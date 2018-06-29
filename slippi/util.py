import inspect, struct


def _real_attrs(obj):
    attrs = ((attr, obj.__getattribute__(attr)) for attr in dir(obj)
             if not attr.startswith('_'))
    return (a for a in attrs if not inspect.isclass(a[1]))


def dict_repr(obj):
    return '<%s: %s>' % (obj.__class__.__qualname__,
                         ', '.join('%s: %s' % a for a in _real_attrs(obj)))


def unpack(fmt, stream):
    fmt = '>' + fmt
    size = struct.calcsize(fmt)
    bytes = stream.read(size)
    if not bytes:
        raise EofException()
    return struct.unpack(fmt, bytes)


class EofException(Exception):
    pass
