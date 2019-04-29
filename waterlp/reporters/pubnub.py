from os import environ
from datetime import datetime

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub


def on_publish(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        print(" [-] ERROR: Failed to report progress. {}".format(status.error_data.information))
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];


class PubNubReporter(object):

    def __init__(self, args, publish_key=None, post_reporter=None, run_id=None):
        self.args = args
        self.post_reporter = post_reporter
        self.updater = None
        self.last_update = {
            'step': datetime(1678, 1, 1),
            'save': datetime(1678, 1, 1)
        }

        subscribe_key = environ.get('PUBNUB_SUBSCRIBE_KEY')

        if publish_key and subscribe_key:
            pnconfig = PNConfiguration()
            pnconfig.subscribe_key = subscribe_key
            pnconfig.publish_key = publish_key
            pnconfig.ssl = False
            self.pubnub = PubNub(pnconfig)
            self.channel = 'openagua-{source_id}-{network_id}-{model_key}-{run_id}'.format(
                source_id=args.source_id,
                network_id=args.network_id,
                model_key=environ['MODEL_KEY'],
                run_id=run_id,
            )
            # if environ.get('RUN_KEY'):
            #     self.channel += '-{}'.format(environ['RUN_KEY'])
            print(' [*] PubNub will publish to {}'.format(self.channel))
        else:
            self.pubnub = None
            self.channel = None
            print(' [-] PubNub failed to initialize.')

    # publish updates
    def report(self, action, force=False, **payload):
        if self.updater:
            payload = self.updater(action=action, **payload)
        if action in ['step', 'save']:
            now = datetime.now()
            last_update_time = (now - self.last_update[action]).seconds
            if self.pubnub and (last_update_time >= 2 or force):
                self.pubnub.publish().channel(self.channel).message(payload).pn_async(on_publish)
                self.last_update[action] = now
            # elif self.post_reporter:
            #     self.post_reporter.report(**payload)
        else:
            if self.post_reporter:
                self.post_reporter.report(**payload)
            return

        if action in ['done', 'error']:
            return
