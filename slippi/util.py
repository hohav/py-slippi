import enum, re, struct, sys, termcolor, warnings


PORTS = range(4)


warnings.formatwarning = lambda msg, *args, **kwargs: '%s %s\n' % (termcolor.colored('WARNING', 'yellow'), msg)
warn = warnings.warn


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
    else:
        return '%s' % (obj,)


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
        return self.__class__.__name__+'.'+self._name_


class IntEnum(enum.IntEnum):
    def __repr__(self):
        return self.__class__.__name__+'.'+self._name_


class IntFlag(enum.IntFlag):
    pass


class EofException(Exception):
    pass
