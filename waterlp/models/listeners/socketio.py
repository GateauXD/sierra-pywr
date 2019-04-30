import socketio

sio = socketio.AsyncClient()


def init_socketio_listener(room_name=''):
    class Listen(socketio.AsyncClientNamespace):
        def on_connect(self):
            pass

        def on_disconnect(self):
            pass

        async def on_stop_model(self, data):
            print('TESTTESTTEST')
            await self.emit('model_stopped', data)

    sio.register_namespace(Listen('/{}'.format(room_name)))
