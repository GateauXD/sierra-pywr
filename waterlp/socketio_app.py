import os
import socketio
from waterlp.reporters.redis import local_redis
from waterlp.utils.application import ProcessState

model_key = os.environ.get('MODEL_KEY')
queue_name = 'model-{}'.format(model_key)
run_key = os.environ.get('RUN_KEY')
if run_key:
    queue_name += '-{}'.format(run_key)

sio = socketio.Client()


@sio.on('connect')
def on_connect():
    # sio.emit('join-model', {'queue_name': queue_name})
    print(' [*] Connected!')


@sio.on('stop-model', namespace='/{}'.format(queue_name))
def stop_model(message):
    sid = message.get('sid')
    print(" [*] Message received.")
    if local_redis and sid:
        print(" [*] Stopping {}".format(sid))
        if local_redis.get(sid):
            local_redis.set(sid, ProcessState.CANCELED)


@sio.on('disconnect')
def on_disconnect():
    print(' [*] Disconnected!')


if __name__ == '__main__':
    sio_url = os.environ.get('SOCKETIO_URL', 'ws://localhost:5000')
    sio.connect(sio_url, namespaces=['/{}'.format(queue_name)])
