import platform
import salt

try:
    import gntp.notifier
except ImportError:
    HAS_GNTP = False
else:
    HAS_GNTP = True

__virtualname__ = 'gntp'

def __virtual__():
    if HAS_GNTP:
        return __virtualname__
    return False


GROWL_MAPPING = {
    'applicationName': ('gntp.applicationname', 'Salt'),
    'hostname': ('gntp.hostname', 'localhost'),
    'password': ('gntp.password', None),
}


class _Notifier(gntp.notifier.GrowlNotifier):
    def add_origin_info(self, packet):
        """Add optional Origin headers to message"""
        packet.add_header('Origin-Machine-Name', platform.node())
        packet.add_header('Origin-Software-Name', 'salt')
        packet.add_header('Origin-Software-Version', salt.__version__)
        packet.add_header('Origin-Platform-Name', platform.system())
        packet.add_header('Origin-Platform-Version', platform.platform())

def _instance(**kwargs):
    for key in GROWL_MAPPING:
        if key not in kwargs:
            config, default = GROWL_MAPPING[key]
            kwargs[key] = __salt__['config.get'](config, default)

    kwargs['notifications'] = ['Salt']
    return _Notifier(**kwargs)


def register(application='salt', notifications=[]):
    growl = _instance()
    growl.register()

def notify(message, noteType='Salt', title='Title'):
    growl = _instance()
    growl.notify(noteType=noteType, title=title, description=message)
