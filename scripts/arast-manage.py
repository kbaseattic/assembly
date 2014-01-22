#! /usr/bin/env python

import argparse
import requests

p = argparse.ArgumentParser(prog='arast-manage.py', 
                  epilog='Use "arast command -h" for more information about a command.')

sub_p = p.add_subparsers(dest='command', title='The commands are')
p.add_argument('-s', dest='host', help='arast server url', default='localhost')
p_node_list = sub_p.add_parser('node-list', help='list compute nodes')
p_node_shutdown = sub_p.add_parser('node-shutdown')
p_node_shutdown.add_argument('node')

args = p.parse_args()

if args.command == 'node-list':
    print requests.get('http://{}:8000/admin/system/node'.format(args.host)).text
if args.command == 'node-shutdown':
    if args.node:
        print requests.get('http://{}:8000/admin/system/node/{}/close'.format(args.host, args.node)).text
    else:
        p.print_usage()
    
