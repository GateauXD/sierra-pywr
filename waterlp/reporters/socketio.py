from os import environ
from datetime import datetime

from flask_socketio import SocketIO


class SocketIOReporter(object):

    def __init__(self, args, publish_key=None, post_reporter=None, run_id=None, broker_url=None):
        self.args = args
        self.post_reporter = post_reporter
        self.updater = None
        self.last_update = {
            'step': datetime(1678, 1, 1),
            'save': datetime(1678, 1, 1)
        }

        subscribe_key = environ.get('OPENAGUA_SUBSCRIBE_KEY')

        run_key = environ.get('RUN_KEY')
        model_key = environ.get('MODEL_KEY')
        queue_name = 'model-{}'.format(model_key)
        if run_key:
            queue_name += '-{}'.format(run_key)

        socketio_url = 'pyamqp://{username}:{password}@{hostname}:5672/socketio'.format(
            username=model_key,
            password=environ.get('RABBITMQ_PASSWORD', 'password'),
            hostname=environ.get('RABBITMQ_HOST', 'localhost'),
        )

        # socketio_url = 'pyamqp://{username}:{password}@{hostname}//'.format(
        #     username=environ['RABBITMQ_USERNAME'],
        #     password=environ.get('RABBITMQ_PASSWORD', 'password'),
        #     hostname=environ.get('RABBITMQ_HOST', 'localhost'),
        # )

        if publish_key and subscribe_key or True:

            self.socketio = SocketIO(message_queue=socketio_url)
            # self.channel = 'openagua-{source_id}-{network_id}-{model_key}-{run_id}'.format(
            #     source_id=args.source_id,
            #     network_id=args.network_id,
            #     model_key=environ['MODEL_KEY'],
            #     run_id=run_id,
            # )
            self.room = 'source-{}-network-{}'.format(args.source_id, args.network_id)
            # if environ.get('RUN_KEY'):
            #     self.channel += '-{}'.format(environ['RUN_KEY'])
            print(' [*] SocketIO will publish to {}'.format(self.socketio))

            # class Listener(socketio.AsyncClientNamespace):
            #     def on_connect(self):
            #         pass
            #
            #     def on_disconnect(self):
            #         pass
            #
            #     async def on_stop_model(self, data):
            #
            #         await self.emit('my_response', data)
            #
            # self.socketio.register_namespace(Listener('/chat'))

        else:
            self.socketio = None
            print(' [-] SocketIO failed to initialize.')

    # publish updates
    def report(self, action, force=False, **payload):
        if self.updater:
            payload = self.updater(action=action, **payload)
        if action in ['step', 'save']:
            now = datetime.now()
            last_update_time = (now - self.last_update[action]).seconds
            if self.socketio and (last_update_time >= 2 or force):
                # self.pubnub.publish().channel(self.channel).message(payload).pn_async(on_publish)
                # self.socketio.emit(action, payload, channel=self.channel)
                self.socketio.emit('update-network-progress', payload, room=self.room)
                self.last_update[action] = now
            # elif self.post_reporter:
            #     self.post_reporter.report(**payload)
        else:
            if self.post_reporter:
                self.post_reporter.report(**payload)
            return

        if action in ['done', 'error']:
            return
