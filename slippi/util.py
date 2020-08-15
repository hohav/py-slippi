import enum, os, re, struct, sys

from .log import log


PORTS = range(4)


def _indent(s):
    return re.sub(r'^', '    ', s, flags=re.MULTILINE)


def _format_collection(coll, delim_open, delim_close):
    elements = [_format(x) for x in coll]
    if '\n' in elements[0]:
        return delim_open + '\n' + ',\n'.join(_indent(e) for e in elements) + delim_close
    else:
        return delim_open + ', '.join(elements) + delim_close


def _format(obj):
    if isinstance(obj, float):
        return '%.02f' % obj
    elif isinstance(obj, tuple):
        return _format_collection(obj, '(', ')')
    elif isinstance(obj, list):
        return _format_collection(obj, '[', ']')
    elif isinstance(obj, enum.Enum):
        return repr(obj)
    else:
        return str(obj)


def try_enum(enum, val):
    try:
        return enum(val)
    except ValueError:
        log.info('unknown %s: %s' % (enum.__name__, val))
        return val


def unpack(fmt, stream):
    fmt = '>' + fmt
    size = struct.calcsize(fmt)
    bytes = stream.read(size)
    if not bytes:
        raise EOFError()
    return struct.unpack(fmt, bytes)


def expect_bytes(expected_bytes, stream):
    read_bytes = stream.read(len(expected_bytes))
    if read_bytes != expected_bytes:
        raise Exception(f'expected {expected_bytes}, but got: {read_bytes}')


class Base:
    __slots__ = []

    def _attr_repr(self, attr):
        return attr + '=' + _format(getattr(self, attr))

    def __repr__(self):
        attrs = []
        for attr in dir(self):
            # uppercase names are nested classes
            if not (attr.startswith('_') or attr[0].isupper()):
                s = self._attr_repr(attr)
                if s:
                    attrs.append(_indent(s))

        return '%s(\n%s)' % (self.__class__.__name__, ',\n'.join(attrs))


class Enum(enum.Enum):
    def __repr__(self):
        return '%r:%s' % (self._value_, self._name_)


class IntEnum(enum.IntEnum):
    def __repr__(self):
        return '%d:%s' % (self._value_, self._name_)

    @classmethod
    def _missing_(cls, value):
        raise ValueError("0x%x is not a valid %s" % (value, cls.__name__)) from None


class IntFlag(enum.IntFlag):
    def __repr__(self):
        members, _ = enum._decompose(self.__class__, self._value_)
        return '%s:%s' % (bin(self._value_), '|'.join([str(m._name_ or m._value_) for m in members]))


class EOFError(IOError):
    def __init__(self):
        super().__init__('unexpected end of file')
