"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""

import pika
import sys

import config

def send_message(size, params, msg):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = config.RABBITMQ_HOST))
    channel = connection.channel()

    routingKey = determine_routing_key (size, params)

    channel.basic_publish(exchange = '',
                          routing_key=routingKey,
                          body=msg,
                          properties=pika.BasicProperties(
                          delivery_mode=2)) #persistant message

    print " [x] Sent %r %r" % (routingKey, msg)
    connection.close()

def get_data_size(files):
    return 2

def transfer_data(files):
    """
    Return file path on NFS server
    """
    return 2

def determine_routing_key(size, params):
    return config.DEFAULT_ROUTING_KEY


def main():
    send_message(1,[],sys.argv[1])

# Receiving


main()
