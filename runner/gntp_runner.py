'''
Custom event listener to send growl events

Example Config Options:
# Assume using something like saltpad
gntp.url: 'http://salt/job_result/{jid}'
'''

# Import Python libs
import fnmatch
import logging
import os
import pprint
import socket

# Import Salt libs
import salt.utils.event

import gntp.config


logger = logging.getLogger(__name__)

__opts__ = {
    'node': 'master',
    'sock_dir': '/var/run/salt/master',
    'growl_templates': os.path.join(os.path.dirname(__file__), 'templates'),
}

SALT_ICON = 'http://github.com/saltstack.png'


class _EventReader(object):
    class SaltGrowler(gntp.config.GrowlNotifier):
        def add_origin_info(self, packet):
            packet.add_header('Sent-By', socket.getfqdn())

    def __init__(self):
        self.config = {
            'applicationName': 'Salt',
            'notifications': ['Other'],
            'applicationIcon': SALT_ICON,
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

        self.templates = {}
        for fn in os.listdir(__opts__['growl_templates']):
            with open(os.path.join(__opts__['growl_templates'], fn)) as fp:
                logger.info('Reading template %s', fp.name)
                self.templates[fn] = fp.read().strip()

    def register(event, notification):
        def wrap(func):
            setattr(func, 'event', event)
            setattr(func, 'notification', notification)
            return func
        return wrap

    def render(self, template, data):
        if template in self.templates:
            template = self.templates[template]
        else:
            template = self.templates['default.tmpl']
        logger.debug('Rendering template: %s', template)
        return template.format(**data)

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
        if 'gntp.url' in __opts__:
            kwargs['callback'] = __opts__['gntp.url'].format(**ret['data']) 
        self.growl.notify(
            'Results',
            ret['tag'],
            self.render(ret['data'].get('out', 'default') + '.tmpl', ret['data']),
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

