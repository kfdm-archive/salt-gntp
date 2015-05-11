# Import Python libs
import pprint
import logging
import socket
import fnmatch

# Import Salt libs
import salt.utils.event

import gntp.config


logger = logging.getLogger(__name__)

__opts__ = {
    'node': 'master',
    'sock_dir': '/var/run/salt/master',
}

TEMPLATE_RETURN = '''
Function: {fun}
Arguments: {fun_args}
ID: {id}
JID: {jid}
Return: {return}
'''.strip()


class _EventReader(object):
    class SaltGrowler(gntp.config.GrowlNotifier):
        def add_origin_info(self, packet):
            packet.add_header('Sent-By', socket.getfqdn())

    def __init__(self):
        self.config = {
            'applicationName': 'Salt',
            'notifications': ['Other'],
        }
        self.event = salt.utils.event.SaltEvent(
            __opts__['node'],
            __opts__['sock_dir']
        )
        logger.info('Listening on %s', self.event.puburi)

        self.events = {}
        for obj in _EventReader.__dict__.itervalues():
            if hasattr(obj, 'event'):
                self.events[obj.event] = obj
                self.config['notifications'].append(obj.notification)

        self.growl = self.SaltGrowler(**self.config)
        self.growl.register()

    def register(event, notification):
        def wrap(func):
            setattr(func, 'event', event)
            setattr(func, 'notification', notification)
            return func
        return wrap

    def dispatcher(self):
        while True:
            ret = self.event.get_event(full=True)
            if ret is None:
                continue
            if ret['tag'].isdigit():
                logger.debug('Skipping numeric tag: %s', ret['tag'])
                continue
            for event, func in self.events.iteritems():
                if fnmatch.fnmatch(ret['tag'], event):
                    logger.debug('Tag: %s Notification: %s', ret['tag'], func.notification)
                    func(self, ret, identifier=ret['tag'])
                    break
            else:
                logger.info('Unhandled tag: %s', ret['tag'])
                logger.debug(pprint.pformat(ret))

    @register('salt/minion/*/start', 'Start')
    def minion_start(self, ret, **kwargs):
        self.growl.notify(
            'Start',
            ret['tag'],
            ret['data']['data'],
            **kwargs
        )

    @register('salt/job/*/new', 'Job')
    def job_new(self, ret, **kwargs):
        self.growl.notify(
            'Job',
            ret['tag'],
            pprint.pformat(ret['data']),
            **kwargs
        )

    @register('new_job', 'New Job')
    def new_job(self, ret, **kwargs):
        pass

    @register('salt/job/*/ret/*', 'Results')
    def job_return(self, ret, **kwargs):
        kwargs['sticky'] = True
        self.growl.notify(
            'Results',
            ret['tag'],
            TEMPLATE_RETURN.format(**ret['data']),
            **kwargs
        )

    @register('salt/auth', 'Auth')
    def salt_auth(self, ret, **kwargs):
        # salt/auth is surprisingly noisy so for now we will
        # skip over it for now
        return
        self.growl.notify(
            'Auth',
            ret['tag'],
            pprint.pformat(ret['data']),
            **kwargs
        )

__virtualname__ = 'gntp'
def __virtual__():
    return 'gntp'

def watch():
    '''Watch the salt event system and growl the results'''
    # debug logging in the gntp library would make things too messy
    # so we manually turn it off here
    logging.getLogger('gntp').setLevel(logging.INFO)
    _EventReader().dispatcher()

