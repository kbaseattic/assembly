"""
Consumes a job from the queue
"""

import pika
import sys
import json
import requests
import os

import config
import assembly as asm

# Set up environment
ARASTURL = config.ARASTURL #Shock
ARASTUSER = config.ARASTUSER
ARASTPASSWORD = config.ARASTPASSWORD

def compute(body):
    print "Computing..."
    params = json.loads(body)

    # Download data
    url = "http://%s" % (ARASTURL)
    url += "/node/%s" % (params['id'])
    url += "?download" 
    r = get(url)
    filename = 'data/'
    filename += params['id']
    datapath = filename
    filename += "/raw/"
    os.makedirs(filename)
    filename += params['filename'][0]
    with open(filename, "wb") as code:
        code.write(r.content)

    # Run assemblies
    print params['assemblers']
    for a in params['assemblers']:
        asm.run(a, datapath)

def get(url):     
    global ARASTUSER, ARASTPASSWORD
    r = None
    if ARASTUSER and ARASTPASSWORD:  
        r = requests.get(url, auth=(ARASTUSER, ARASTPASSWORD))       
    else:
        r = requests.get(url)
        #res = json.loads(r.text)
    return r

def fetch_job(queue):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = config.RABBITMQ_HOST))
    channel = connection.channel()

    result = channel.queue_declare(queue=queue,
                                   exclusive=False,
                                   auto_delete=False,
                                   durable=True)
            
    print ' [*] Fetching job...'

    channel.basic_consume(callback,
                          queue=queue,
                          no_ack=True) #change?

    channel.start_consuming()

def callback(ch, method, properties, body):
    print " [*] %r:%r" % (method.routing_key, body)
    compute(body)


# For now, use this instead of daemon
def main():
    print "consuming"
    fetch_job(config.JOB_MEDIUM)

main()
