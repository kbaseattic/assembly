"""
Arast Daemon

"""

#! /usr/bin/python

import daemon
import consume

context = daemon.DaemonContext()

print "Starting daemon"
with context:
    print "Starting arastd"
