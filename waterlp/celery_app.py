import getpass
from os import path, environ, makedirs
from shutil import rmtree
from celery import Celery

from pathlib import Path
home = str(Path.home())

run_key = environ.get('RUN_KEY')
model_key = environ.get('MODEL_KEY')
queue_name = 'model-{}'.format(model_key)
if run_key:
    queue_name += '-{}'.format(run_key)

# librabbitmq does not handle pickle content; pyamqp makes sure that librabbitmq isn't used if installed
broker_url = 'pyamqp://{username}:{password}@{hostname}:5672/model-run'.format(
    username=model_key,
    password=environ.get('RABBITMQ_PASSWORD', 'password'),
    hostname=environ.get('RABBITMQ_HOST', 'localhost'),
)

app = Celery('openagua', broker=broker_url, include=['waterlp.tasks'])

app.conf.update(
    task_default_queue=queue_name,
    task_default_exchange='model.tasks',
    broker_heartbeat=10,
    accept_content=['json', 'pickle'],
    result_expires=3600,
    worker_prefetch_multiplier=1,
)


def start_listening(concurrency=4):
    from waterlp.utils.application import PNSubscribeCallback

    # app.config_from_object('waterlp.celeryconfig')
    app_dir = '{}/.waterlp'.format(home)
    logs_dir = '{}/logs'.format(app_dir)
    if path.exists(app_dir):
        rmtree(app_dir)
    makedirs(logs_dir)

    pubnub_subscribe_key = environ.get('PUBNUB_SUBSCRIBE_KEY')
    openagua_subscribe_key = environ.get('OPENAGUA_SUBSCRIBE_KEY')

    # if pubnub_subscribe_key:
    #     from pubnub.pnconfiguration import PNConfiguration
    #     from pubnub.pubnub import PubNub
    #
    #     pnconfig = PNConfiguration()
    #     pnconfig.subscribe_key = pubnub_subscribe_key
    #     pnconfig.ssl = False
    #     pubnub = PubNub(pnconfig)
    #     pubnub.add_listener(PNSubscribeCallback())
    #
    #     pubnub.subscribe().channels(queue_name).execute()
    #     print(" [*] Subscribed to PubNub at {}".format(queue_name))
    #
    # elif openagua_subscribe_key:
    #     from waterlp.models.listeners.socketio import init_socketio_listener
    #     init_socketio_listener(room_name=queue_name)

    app.start(['celery', 'worker', '-c', str(concurrency), '-l', 'INFO'])


if __name__ == '__main__':
    start_listening()
