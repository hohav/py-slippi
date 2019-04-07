import enum, inspect, struct, sys, termcolor


PORTS = range(4)


def _attrs(obj):
    attrs = ((attr, obj.__getattribute__(attr)) for attr in dir(obj)
             if not attr.startswith('_'))
    return (a for a in attrs if not inspect.isclass(a[1]))


def _format(obj):
    return '%.02f' % obj if isinstance(obj, float) else obj


def unpack(fmt, stream):
    fmt = '>' + fmt
    size = struct.calcsize(fmt)
    bytes = stream.read(size)
    if not bytes:
        raise EofException()
    return struct.unpack(fmt, bytes)


def warn(msg):
    print(termcolor.colored('WARNING', 'yellow') + ' ' + msg, file=sys.stderr)


class Base:
    __slots__ = []

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
          ', '.join('%s=%s' % (k, _format(v)) for k,v in _attrs(self)))


class Enum(enum.Enum):
    def __repr__(self):
        return self.__class__.__name__+'.'+self._name_


class IntEnum(enum.IntEnum):
    def __repr__(self):
        return self.__class__.__name__+'.'+self._name_


class IntFlag(enum.IntFlag):
    pass


class EofException(Exception):
    pass
