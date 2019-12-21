import io, ubjson

from slippi.event import EventType, ParseEvent, Start, End, Frame
from slippi.metadata import Metadata
from slippi.util import *


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
    stream = io.BytesIO(event_stream.read(payload_sizes[code]))

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
            if current_frame and current_frame.index != event.id.frame:
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
    expect_bytes(b'{U\x03raw[$U#l', stream)
    (length,) = unpack('l', stream) # currently unused

    payload_sizes = _parse_event_payloads(stream)
    _parse_events(stream, payload_sizes, handlers)

    # Parse metadata first because it may useful while parsing frames
    expect_bytes(b'U\x08metadata', stream)
    metadata = Metadata._parse(ubjson.load(stream))
    handler = handlers.get(ParseEvent.METADATA)
    if handler:
        handler(metadata)
    expect_bytes(b'}', stream)


def parse(input, handlers):
    """Parses Slippi replay data from `input` (stream or path).

    `handlers` should be a dict of :py:class:`slippi.event.ParseEvent` keys to handler functions. Each event will be passed to the corresponding handler as it occurs."""

    if isinstance(input, str):
        with open(input, 'rb') as f:
            _parse(f, handlers)
    else:
        _parse(input, handlers)
