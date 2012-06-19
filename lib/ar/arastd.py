"""
Arast Daemon

"""

#! /usr/bin/python
import sys
import daemon
import consume
import config


context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

with context:
    print "Starting arastd"
    consume.fetch_job(config.JOB_MEDIUM)
