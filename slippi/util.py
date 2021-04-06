import enum, os, re, struct, sys
from typing import Tuple, Any, List, Union, BinaryIO

from .log import log


PORTS = range(4)


def _indent(s: str) -> str:
    return re.sub(r'^', '    ', s, flags=re.MULTILINE)


def _format_collection(coll: Union[List[Any], Tuple[Any, ...]], delim_open: str, delim_close: str) -> str:
    elements = [_format(x) for x in coll]
    if elements and '\n' in elements[0]:
        return delim_open + '\n' + ',\n'.join(_indent(e) for e in elements) + delim_close
    else:
        return delim_open + ', '.join(elements) + delim_close


def _format(obj: Any) -> str:
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


def try_enum(enum: Any, val: Any) -> Any:
    try:
        return enum(val)
    except ValueError:
        log.info('unknown %s: %s' % (enum.__name__, val))
        return val


def unpack(fmt: str, stream: BinaryIO) -> Tuple[Any, ...]:
    fmt = '>' + fmt
    size = struct.calcsize(fmt)
    bytes = stream.read(size)
    if not bytes:
        raise EOFError()
    return struct.unpack(fmt, bytes)


def expect_bytes(expected_bytes: bytes, stream: BinaryIO) -> None:
    read_bytes = stream.read(len(expected_bytes))
    if read_bytes != expected_bytes:
        raise Exception(f'expected {expected_bytes.decode()}, but got: {read_bytes.decode()}')


class Base:
    __slots__: Tuple[Any, ...] = ()

    def _attr_repr(self, attr: str) -> str:
        return attr + '=' + _format(getattr(self, attr))

    def __repr__(self) -> str:
        attrs: List[str] = []
        for attr in dir(self):
            # uppercase names are nested classes
            if not (attr.startswith('_') or attr[0].isupper()):
                s = self._attr_repr(attr)
                if s:
                    attrs.append(_indent(s))

        return '%s(\n%s)' % (self.__class__.__name__, ',\n'.join(attrs))


class Enum(enum.Enum):
    def __repr__(self) -> str:
        return '%r:%s' % (self._value_, self._name_)


class IntEnum(enum.IntEnum):
    def __repr__(self) -> str:
        return '%d:%s' % (self._value_, self._name_)

    @classmethod
    def _missing_(cls, value: Any) -> None:
        val_desc = f'0x{value:x}' if isinstance(value, int) else f'{value}'
        raise ValueError(f'{val_desc} is not a valid {cls.__name__}') from None


class IntFlag(enum.IntFlag):
    def __repr__(self) -> str:
        members, _ = enum._decompose(self.__class__, self._value_)  # type: ignore[attr-defined]
        return '%s:%s' % (bin(self._value_), '|'.join([str(m._name_ or m._value_) for m in members]))


class EOFError(IOError):
    def __init__(self) -> None:
        super().__init__('unexpected end of file')
