"""
Arast Daemon

The Arast daemon runs on compute nodes/instances.
Functionality:
 - Monitors job queue for job

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
