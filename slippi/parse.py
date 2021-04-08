from __future__ import annotations

import io, os, pathlib
from typing import BinaryIO, Callable, Dict, Union

import ubjson

from .event import GameEnd, EventType, Frame, Start, FrameEvent, FrameEventPortId, FrameEventType, FrameEventPort, \
    FrameStart, FrameEnd, Data
from .log import log
from .metadata import Metadata
from .util import *


class ParseEvent(Enum):
    """Parser events, used as keys for event handlers. Docstrings indicate the type of object that will be passed to each handler."""

    METADATA = 'metadata' #: :py:class:`slippi.metadata.Metadata`:
    METADATA_RAW = 'metadata_raw' #: dict:
    START = 'start' #: :py:class:`slippi.event.Start`:
    FRAME = 'frame' #: :py:class:`slippi.event.Frame`:
    END = 'end' #: :py:class:`slippi.event.End`:
    FRAME_START = 'frame_start' #: :py:class:`slippi.event.Frame.Start`:
    ITEM = 'item' #: :py:class:`slippi.event.Frame.Item`:
    FRAME_END = 'frame_end' #: :py:class:`slippi.event.Frame.End`:


class ParseError(IOError):
    def __init__(self, message, filename = None, pos = None):
        super().__init__(message)
        self.filename = filename
        self.pos = pos

    def __str__(self):
        return 'Parse error (%s %s): %s' % (
            self.filename or '?',
            '@0x%x' % self.pos if self.pos else '?',
            super().__str__())


def _parse_event_payloads(stream):
    (code, this_size) = unpack('BB', stream)

    event_type = EventType(code)
    if event_type is not EventType.EVENT_PAYLOADS:
        raise Exception(f'expected event payloads, but got {event_type}')

    this_size -= 1 # includes size byte for some reason
    command_count = this_size // 3
    if command_count * 3 != this_size:
        raise Exception(f'payload size not divisible by 3: {this_size}')

    sizes = {}
    for i in range(command_count):
        (code, size) = unpack('BH', stream)
        sizes[code] = size
        try: EventType(code)
        except ValueError: log.info('ignoring unknown event type: 0x%02x' % code)

    log.debug(f'event payload sizes: {sizes}')
    return (2 + this_size, sizes)


def _parse_event(event_stream, payload_sizes):
    (code,) = unpack('B', event_stream)
    log.debug(f'Event: 0x{code:x}')

    # remember starting pos for better error reporting
    try: base_pos = event_stream.tell() if event_stream.seekable() else None
    except AttributeError: base_pos = None

    try: size = payload_sizes[code]
    except KeyError: raise ValueError('unexpected event type: 0x%02x' % code)

    stream = io.BytesIO(event_stream.read(size))

    try:
        try: event_type = EventType(code)
        except ValueError: event_type = None

        if event_type is EventType.GAME_START:
            event = Start._parse(stream)
        elif event_type is EventType.FRAME_PRE:
            event = FrameEvent(FrameEventPortId(stream),
                                FrameEventType.PRE,
                                stream)
        elif event_type is EventType.FRAME_POST:
            event = FrameEvent(FrameEventPortId(stream),
                                FrameEventType.POST,
                                stream)
        elif event_type is EventType.FRAME_START:
            event = FrameEvent(FrameEventPortId(stream),
                                FrameEventType.START,
                                stream)
        elif event_type is EventType.ITEM:
            event = FrameEvent(FrameEventPortId(stream),
                                FrameEventType.ITEM,
                                stream)
        elif event_type is EventType.FRAME_END:
            event = FrameEvent(FrameEventPortId(stream),
                                FrameEventType.END,
                                stream)
        elif event_type is EventType.GAME_END:
            event = GameEnd._parse(stream)
        else:
            event = None
        return (1 + size, event)
    except Exception as e:
        # Calculate the stream position of the exception as best we can.
        # This won't be perfect: for an invalid enum, the calculated position
        # will be *after* the value at minimum, and may be farther than that
        # due to `unpack`ing multiple values at once. But it's better than
        # leaving it up to the `catch` clause in `parse`, because that will
        # always report a position that's at the end of an event (due to
        # `event_stream.read` above).
        raise ParseError(str(e), pos = base_pos + stream.tell() if base_pos else None)


def _parse_events(stream, payload_sizes, total_size, handlers):
    current_frame = None
    bytes_read = 0
    event = None

    # `total_size` will be zero for in-progress replays
    while (total_size == 0 or bytes_read < total_size) and event != ParseEvent.END:
        (b, event) = _parse_event(stream, payload_sizes)
        bytes_read += b
        if isinstance(event, Start):
            handler = handlers.get(ParseEvent.START)
            if handler:
                handler(event)
        elif isinstance(event, GameEnd):
            handler = handlers.get(ParseEvent.END)
            if handler:
                handler(event)
        elif isinstance(event, FrameEvent):
            # Accumulate all events for a single frame into a single `Frame` object.

            # We can't use Frame Bookend events to detect end-of-frame,
            # as they don't exist before Slippi 3.0.0.
            if current_frame and current_frame.index != event.id.frame:
                current_frame._finalize()
                handler = handlers.get(ParseEvent.FRAME)
                if handler:
                    handler(current_frame)
                current_frame = None

            if not current_frame:
                current_frame = Frame(event.id.frame)

            if event.type is FrameEventType.PRE or event.type is FrameEventType.POST:
                port = current_frame.ports[event.id.port]
                if not port:
                    port = FrameEventPort()
                    current_frame.ports[event.id.port] = port

                if event.id.is_follower:
                    if port.follower is None:
                        port.follower = Data()
                    data = port.follower
                else:
                    data = port.leader

                if event.type is FrameEventType.PRE:
                    data._pre = event.data
                else:
                    data._post = event.data
            elif event.type is FrameEventType.ITEM:
                current_frame.items.append(Frame.Item._parse(event.data))
            elif event.type is FrameEventType.START:
                current_frame.start = FrameStart._parse(event.data)
            elif event.type is FrameEvent.Type.END:
                current_frame.end = FrameEnd._parse(event.data)
            else:
                raise Exception('unknown frame data type: %s' % event.data)

    if current_frame:
        current_frame._finalize()
        handler = handlers.get(ParseEvent.FRAME)
        if handler:
            handler(current_frame)


def _parse(stream, handlers):
    # For efficiency, don't send the whole file through ubjson.
    # Instead, assume `raw` is the first element. This is brittle and
    # ugly, but it's what the official parser does so it should be OK.
    expect_bytes(b'{U\x03raw[$U#l', stream)
    (length,) = unpack('l', stream)

    (bytes_read, payload_sizes) = _parse_event_payloads(stream)
    _parse_events(stream, payload_sizes, length - bytes_read, handlers)

    expect_bytes(b'U\x08metadata', stream)

    json = ubjson.load(stream)
    raw_handler = handlers.get(ParseEvent.METADATA_RAW)
    if raw_handler:
        raw_handler(json)

    metadata = Metadata._parse(json)
    handler = handlers.get(ParseEvent.METADATA)
    if handler:
        handler(metadata)

    expect_bytes(b'}', stream)


def _parse_try(input: BinaryIO, handlers):
    """Wrap parsing exceptions with additional information."""

    try:
        _parse(input, handlers)
    except Exception as e:
        e = e if isinstance(e, ParseError) else ParseError(str(e))

        try: e.filename = input.name # type: ignore
        except AttributeError: pass

        try:
            # prefer provided position info, as it will be more accurate
            if not e.pos and input.seekable(): # type: ignore
                e.pos = input.tell() # type: ignore
        # not all stream-like objects support `seekable` (e.g. HTTP requests)
        except AttributeError: pass

        raise e


def _parse_open(input: os.PathLike, handlers) -> None:
    with open(input, 'rb') as f:
        _parse_try(f, handlers)


def parse(input: Union[BinaryIO, str, os.PathLike], handlers: Dict[ParseEvent, Callable[..., None]]) -> None:
    """Parse a Slippi replay.

    :param input: replay file object or path
    :param handlers: dict of parse event keys to handler functions. Each event will be passed to the corresponding handler as it occurs."""

    if isinstance(input, str):
        _parse_open(pathlib.Path(input), handlers)
    elif isinstance(input, os.PathLike):
        _parse_open(input, handlers)
    else:
        _parse_try(input, handlers)
