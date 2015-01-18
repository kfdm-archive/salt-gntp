import pprint

__virtualname__ = 'gntp'

def __virtual__():
    if 'gntp.register' in __salt__:
        return __virtualname__
    return False

def returner(ret):
    try:
        __salt__['gntp.register']('Salt', ['Salt'])
        __salt__['gntp.notify'](pprint.pformat(ret), title=ret.get('fun'))
    except Exception, e:
        print e
    else:
        print ret

