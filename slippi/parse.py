import io, ubjson

from slippi.event import EventType, Start, End, Frame
from slippi.metadata import Metadata
from slippi.util import *


class ParseEvent(Enum):
    """Parser events, used as keys for event handlers. Docstrings indicate the type of object that will be passed to each handler."""

    METADATA = 'metadata' #: :py:class:`slippi.metadata.Metadata`:
    METADATA_RAW = 'metadata_raw' #: dict:
    START = 'start' #: :py:class:`Start`:
    FRAME = 'frame' #: :py:class:`Frame`:
    END = 'end' #: :py:class:`End`:


class ParseError(IOError):
    def __init__(self, message, name = None, pos = None):
        super().__init__(message)
        self.name = name
        self.pos = pos

    def __str__(self):
        return 'Parse error (%s %s): %s' % (
            self.name or '?',
            '@0x%x' % self.pos if self.pos else '?',
            super().__str__())


def _parse_event_payloads(stream):
    (code, payload_size) = unpack('BB', stream)

    event_type = EventType(code)
    if event_type is not EventType.EVENT_PAYLOADS:
        raise Exception('expected event payloads, but got: %s' % event_type)

    payload_size -= 1 # includes size byte for some reason
    command_count = payload_size // 3
    if command_count * 3 != payload_size:
        raise Exception('payload size not divisible by 3: %d' % payload_size)

    payload_sizes = {}
    for i in range(command_count):
        (code, size) = unpack('BH', stream)
        payload_sizes[code] = size

    return payload_sizes


def _parse_event(event_stream, payload_sizes):
    (code,) = unpack('B', event_stream)

    # remember starting pos for better error reporting
    try: base_pos = event_stream.tell() if event_stream.seekable() else None
    except AttributeError: base_pos = None

    try: size = payload_sizes[code]
    except KeyError: raise ValueError('unknown event type: 0x%x' % code)

    stream = io.BytesIO(event_stream.read(size))

    try:
        try: event_type = EventType(code)
        except ValueError: event_type = None

        if event_type is EventType.GAME_START:
            event = Start._parse(stream)
        elif event_type is EventType.FRAME_PRE:
            event = Frame.Event(Frame.Event.Id(stream),
                                Frame.Event.Type.PRE,
                                stream)
        elif event_type is EventType.FRAME_POST:
            event = Frame.Event(Frame.Event.Id(stream),
                                Frame.Event.Type.POST,
                                stream)
        elif event_type is EventType.GAME_END:
            event = End._parse(stream)
        else:
            warn('unknown event code: 0x%02x' % code)
            event = None

        return event
    except Exception as e:
        # Calculate the stream position of the exception as best we can.
        # This won't be perfect: for an invalid enum, the calculated position
        # will be *after* the value at minimum, and may be farther than that
        # due to `unpack`ing multiple values at once. But it's better than
        # leaving it up to the `catch` clause in `parse`, because that will
        # always report a position that's at the end of an event (due to
        # `event_stream.read` above).
        raise ParseError(str(e), pos = base_pos + stream.tell() if base_pos else None)


def _parse_events(stream, payload_sizes, handlers):
    current_frame = None
    done = False

    while not done:
        event = _parse_event(stream, payload_sizes)
        if isinstance(event, Start):
            handler = handlers.get(ParseEvent.START)
            if handler:
                handler(event)
        elif isinstance(event, End):
            handler = handlers.get(ParseEvent.END)
            if handler:
                handler(event)
            done = True
        elif isinstance(event, Frame.Event):
            # Accumulate all events for a single frame into a single `Frame` object.

            # We can't use Frame Bookend events to detect end-of-frame,
            # as they don't exist before Slippi 3.0.0.
            if current_frame and current_frame.index != event.id.frame:
                if current_frame.index > event.id.frame:
                    warn(f'out-of-order-frame: {current_frame.index} -> {event.id.frame}')

                current_frame._finalize()
                handler = handlers.get(ParseEvent.FRAME)
                if handler:
                    handler(current_frame)
                current_frame = None

            if not current_frame:
                current_frame = Frame(event.id.frame)

            port = current_frame.ports[event.id.port]
            if not port:
                port = Frame.Port()
                current_frame.ports[event.id.port] = port

            if event.id.is_follower:
                if port.follower is None:
                    port.follower = Frame.Port.Data()
                data = port.follower
            else:
                data = port.leader

            if event.type is Frame.Event.Type.PRE:
                data._pre = event.data
            elif event.type is Frame.Event.Type.POST:
                data._post = event.data
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
    (length,) = unpack('l', stream) # currently unused

    payload_sizes = _parse_event_payloads(stream)
    _parse_events(stream, payload_sizes, handlers)

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


def parse(input, handlers):
    """Parses Slippi replay data from `input` (stream or path).

    `handlers` should be a dict of :py:class:`slippi.event.ParseEvent` keys to handler functions. Each event will be passed to the corresponding handler as it occurs."""

    (f, needs_close) = (open(input, 'rb'), True) if isinstance(input, str) else (input, False)

    try:
        _parse(f, handlers)
    except Exception as e:
        e = e if isinstance(e, ParseError) else ParseError(str(e))

        try: e.name = f.name
        except AttributeError: pass

        try:
            # prefer provided position info, as it will be more accurate
            if not e.pos and f.seekable():
                e.pos = f.tell()
        # not all stream-like objects support `seekable` (e.g. HTTP requests)
        except AttributeError: pass

        raise e
    finally:
        if needs_close:
            f.close()
