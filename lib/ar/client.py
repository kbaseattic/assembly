"""
Client to initiate an Assembly RAST job submission.
"""


import pika
import sys
import json
import optparse
import uuid

import client_config

## Parse arguments ##
parser = optparse.OptionParser()
parser.add_option("-f", "--file", action="store", dest="filename",
                  help="specify a sequence file")
parser.add_option("-a", "--assemblers", action="store",
                  dest="assemblers")
parser.add_option("-s", "--size", action="store", dest="size",
                  help="size of data in GB")
parser.add_option("-d", "--directory", action="store",
                  dest="directory",
                  help="specify input directory")

(opt, args) = parser.parse_args()
options = vars(opt)


## Send RPC call ##
class RpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=client_config.ARAST_HOST))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, msg):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                reply_to = self.callback_queue,
                correlation_id = self.corr_id,
                ),
                                   body=msg)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


#rpc_body = json.dumps(str(options), sort_keys=True)
rpc_body = json.dumps(options, sort_keys=True)
arast_rpc = RpcClient()
print " [x] Sending message: %r" % (rpc_body)
response = arast_rpc.call(rpc_body)
print " [.] Response: %r" % (response)
