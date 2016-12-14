#!/usr/bin/env python
#
# This is a simple helper script to pre-create the job queue
#

import pika
from time import sleep
import sys

retries = 6
tsleep = 5

while (retries>0):
  try:
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='jobs.regular', durable=True)
    sys.exit(0)
  except pika.exceptions.AMQPConnectionError:
    print "Retrying..."
    retries -= 1
    sleep(tsleep)

print "Failed to connect"
sys.exit(1)
