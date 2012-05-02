import pika

import router
import config


def on_request(ch, method, props, body):
    router.route_job(body)

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=config.RABBITMQ_HOST))

channel = connection.channel()
channel.queue_declare(queue=config.RPC_QUEUE)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue=config.RPC_QUEUE)
print " [x] Awaiting RPC requests"
channel.start_consuming()
