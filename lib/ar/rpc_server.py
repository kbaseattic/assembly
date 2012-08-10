import pika

import config
import router

def on_request(ch, method, props, body):
    print " [.] Incoming request:  %r" % (body)
    #url = router.get_upload_url(body)

    url = str(router.route_job(body))
    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(
            correlation_id=props.correlation_id),
                     body=url)
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=config.RABBITMQ_HOST))

channel = connection.channel()
channel.queue_declare(queue='rpc_queue')
channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue='rpc_queue')
print " [x] Awaiting RPC requests"
channel.start_consuming()
