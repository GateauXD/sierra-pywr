#!/usr/bin/env python
import json
import getpass
from shutil import rmtree
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin
import os
from main import commandline_parser, run_model

from waterlp.logger import RunLogger


# This code is derived from
# https://medium.com/python-pandemonium/building-robust-rabbitmq-consumers-with-python-and-kombu-part-2-e9505f56e12e

class Worker(ConsumerMixin):

    def __init__(self, connection, queues):
        self.connection = connection
        self.queues = queues

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queues,
                         prefetch_count=0,
                         # no_ack=True,
                         callbacks=[self.process_task])]

    def process_task(self, body, message):

        message.ack()

        env = body.get('env', {})
        args = body.get('args')
        kwargs = body.get('kwargs')

        app_dir = '/home/{}/.waterlp'.format(getpass.getuser())
        logs_dir = '{}/logs'.format(app_dir)

        for key, value in env.items():
            os.environ[key] = value
        print(" [x] Running model with %r" % args)

        parser = commandline_parser()
        args, unknown = parser.parse_known_args(args)

        RunLog = RunLogger(name='waterlp', app_name=args.app_name, run_name=args.run_name, logs_dir=logs_dir,
                           username=args.hydra_username)

        try:
            RunLog.log_start()
            run_model(args, logs_dir, **kwargs)
            RunLog.log_finish()
        except Exception as err:
            RunLog.log_error(message=str(err))

        # message.ack()


if __name__ == '__main__':

    hostname = os.environ.get('RABBITMQ_HOST', 'localhost')
    model_key = os.environ.get('MODEL_KEY')
    run_key = os.environ.get('RUN_KEY')
    vhost = os.environ.get('RABBITMQ_VHOST', 'model-run')
    userid = os.environ.get('RABBITMQ_USERNAME', model_key)
    password = os.environ.get('RABBITMQ_PASSWORD', 'password')

    app_dir = '/home/{}/.waterlp'.format(getpass.getuser())
    logs_dir = '{}/logs'.format(app_dir)
    if os.path.exists(app_dir):
        rmtree(app_dir)
    os.makedirs(logs_dir)

    # Note: heartbeat is needed to ensure dead connections are terminated right away.
    # heartbeat only works with py-amqp (so don't install librabbitmq).
    # see https://kombu.readthedocs.io/en/stable/reference/kombu.connection.html#kombu.connection.Connection.heartbeat
    # Hopefully this will not cause too major a performance hit.
    with Connection(
            hostname=hostname,
            virtual_host=vhost,
            userid=userid,
            password=password,
            heartbeat=5,
    ) as conn:
        try:

            # QUEUE
            queue_name = 'model-{}'.format(model_key)
            if run_key:
                queue_name += '-{}'.format(run_key)

            queue = Queue(
                name=queue_name,
                durable=True,
                auto_delete=False,
                message_ttl=3600,
            )

            worker = Worker(conn, [queue])

            print(' [*] Waiting for messages. To exit press CTRL+C')

            worker.run()
        except KeyboardInterrupt:
            conn.release()
            print('bye bye')
