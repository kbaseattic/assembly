"""
Consumes a job from the queue
"""

import pika
import sys

import config

def fetch_job(queue):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = config.RABBITMQ_HOST))
    channel = connection.channel()

    result = channel.queue_declare(queue=queue,
                                   exclusive=False,
                                   auto_delete=False,
                                   durable=True)
            
    print ' [*] Fetching job.'

    channel.basic_consume(callback,
                          queue=queue,
                          no_ack=True) #change?

    channel.start_consuming()

def callback(ch, method, properties, body):
    print " [*] %r:%r" % (method.routing_key, body)


