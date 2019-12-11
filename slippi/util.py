import enum, inspect, struct, sys, termcolor, warnings


PORTS = range(4)


warnings.formatwarning = lambda msg, *args, **kwargs: '%s %s\n' % (termcolor.colored('WARNING', 'yellow'), msg)
warn = warnings.warn


def _attrs(obj):
    attrs = ((attr, obj.__getattribute__(attr)) for attr in dir(obj)
             if not attr.startswith('_'))
    return (a for a in attrs if not inspect.isclass(a[1]))


def _format(obj):
    return '%.02f' % obj if isinstance(obj, float) else obj


def try_enum(enum, val):
    try:
        return enum(val)
    except ValueError:
        warn('unknown %s: %s' % (enum.__name__, val))
        return val


def unpack(fmt, stream):
    fmt = '>' + fmt
    size = struct.calcsize(fmt)
    bytes = stream.read(size)
    if not bytes:
        raise EofException()
    return struct.unpack(fmt, bytes)


def expect_bytes(expected_bytes, stream):
    read_bytes = stream.read(len(expected_bytes))
    if read_bytes != expected_bytes:
        raise Exception(f'expected {expected_bytes}, but got: {read_bytes}')


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
