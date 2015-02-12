# Import Python libs
import pprint
import logging
import socket
from fnmatch import fnmatch

# Import Salt libs
import salt.utils.event

import gntp.config


logger = logging.getLogger(__name__)

__opts__ = {
    'node': 'master',
    'sock_dir': '/var/run/salt/master',
}

GROWL_SETTINGS = {
    'applicationName': 'Salt',
    'notifications': ['Auth', 'Start', 'Job', 'Results', 'Other'],
}

TEMPLATE_RETURN = '''
Function: {fun}
Arguments: {fun_args}
ID: {id}
JID: {jid}
Return: {return}
'''.strip()


class SaltGrowler(gntp.config.GrowlNotifier):
    def add_origin_info(self, packet):
        packet.add_header('Sent-By', socket.getfqdn())


class EventReader(object):
    def __init__(self):
        self.event = salt.utils.event.SaltEvent(
            __opts__['node'],
            __opts__['sock_dir']
        )
        logger.info('Listening on %s', self.event.puburi)

        self.growl = SaltGrowler(**GROWL_SETTINGS)
        self.growl.register()

        self.events = {}
        for obj in EventReader.__dict__.itervalues():
            if hasattr(obj, 'event'):
                self.events[obj.event] = obj

    def register(event):
        def wrap(func):
            setattr(func, 'event', event)
            return func
        return wrap

    def dispatcher(self):
        while True:
            ret = self.event.get_event(full=True)
            if ret is None:
                continue
            # salt/auth is surprisingly noisy so for now we will
            # skip over it
            if ret['tag'] == 'salt/auth':
                continue
            for event, func in self.events.iteritems():
                if fnmatch(ret['tag'], event):
                    func(self, ret, identifier=ret['tag'])
                    break
            else:
                logger.info('Unhandled tag: %s', ret['tag'])
                logger.debug(pprint.pformat(ret))

    @register('salt/minion/*/start')
    def minion_start(self, ret, **kwargs):
        self.growl.notify(
            'Start',
            ret['tag'],
            ret['data'],
            **kwargs
        )

    @register('salt/job/*/new')
    def job_new(self, ret, **kwargs):
        self.growl.notify(
            'Job',
            ret['tag'],
            pprint.pformat(ret['data']),
            **kwargs
        )

    @register('salt/job/*/ret/*')
    def job_return(self, ret, **kwargs):
        kwargs['sticky'] = True
        self.growl.notify(
            'Results',
            ret['tag'],
            TEMPLATE_RETURN.format(**ret['data']),
            **kwargs
        )

    @register('salt/auth')
    def salt_auth(self, ret, **kwargs):
        self.growl.notify(
            'Auth',
            ret['tag'],
            pprint.pformat(ret['data']),
            **kwargs
        )

def watch():
    logging.getLogger('gntp').setLevel(logging.INFO)
    EventReader().dispatcher()

