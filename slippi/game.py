import io, re, sys, ubjson
from datetime import datetime, timedelta, timezone

import slippi.event as evt
from slippi.id import InGameCharacter
from slippi.util import *


# The first frame of the game is indexed -123, counting up to zero (which is when the word "GO" appears). But since players actually get control before frame zero (!!!), we need to record these frames.
FIRST_FRAME_INDEX = -123


class Game(Base):
    """Replay data from a game of Super Smash Brothers Melee."""

    def __init__(self, path):
        """Reads data from the Slippi (.slp) replay file at `path`."""

        self.metadata = None
        """:py:class:`Metadata`: Miscellaneous data relevant to the game but not directly provided by Melee"""

        self.start = None
        """:py:class:`slippi.event.Start`: Information about the start of the game"""

        self.frames = []
        """list(:py:class:`slippi.event.Frame`): Every frame of the game, indexed by frame number (omits frames that occur before the timer starts)"""

        self.end = None
        """:py:class:`slippi.event.End`: Information about the end of the game"""

        self._out_of_order = False
        self._warnings = []

        self._parse_file(path)

    def _parse_event_payloads(self, stream):
        (code, payload_size) = unpack('BB', stream)
        event_type = evt.EventType(code)
        if event_type is not evt.EventType.EVENT_PAYLOADS:
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

    def _parse_event(self, event_stream, payload_sizes):
        (code,) = unpack('B', event_stream)
        try:
            event_type = evt.EventType(code)
        except ValueError:
            if not code in self._warnings:
                warn('skipping unknown event code: %d' % code)
                self._warnings.append(code)
            event_stream.read(payload_sizes[code])
            return None

        payload = event_stream.read(payload_sizes[code])
        stream = io.BytesIO(payload)
        if event_type is evt.EventType.GAME_START:
            return evt.Start._parse(stream)
        elif event_type is evt.EventType.FRAME_PRE:
            return evt.Frame.Event(evt.Frame.Event.Id(stream),
                                   evt.Frame.Port.Data.Pre(stream))
        elif event_type is evt.EventType.FRAME_POST:
            return evt.Frame.Event(evt.Frame.Event.Id(stream),
                                   evt.Frame.Port.Data.Post(stream))
        elif event_type is evt.EventType.GAME_END:
            return evt.End._parse(stream)
        else:
            raise Exception('unexpected event: %s' % event_type)

    def _parse_file(self, path):
        """Parses the .slp file at `path`. Called automatically by our constructor."""

        with open(path, 'rb') as f:
            json = ubjson.load(f)

        self.metadata = self.Metadata._parse(json['metadata'])

        stream = io.BytesIO(json['raw'])
        payload_sizes = self._parse_event_payloads(stream)

        try:
            while True:
                event = self._parse_event(stream, payload_sizes)
                if isinstance(event, evt.Frame.Event):
                    frame_index = event.id.frame - FIRST_FRAME_INDEX

                    if not self._out_of_order and len(self.frames) != frame_index and len(self.frames) != frame_index + 1:
                        self._out_of_order = True
                        warn('out-of-order frame: %d' % event.id.frame)

                    while (len(self.frames) <= frame_index):
                        if self.frames:
                            self.frames[-1]._finalize()
                        self.frames.append(evt.Frame(event.id.frame))

                    port = self.frames[frame_index].ports[event.id.port]
                    if not port:
                        port = evt.Frame.Port()
                        self.frames[frame_index].ports[event.id.port] = port

                    if event.id.is_follower:
                        if port.follower is None:
                            port.follower = evt.Frame.Port.Data()
                        data = port.follower
                    else:
                        data = port.leader

                    if isinstance(event.data, evt.Frame.Port.Data.Pre):
                        data.pre = event.data
                    elif isinstance(event.data, evt.Frame.Port.Data.Post):
                        data.post = event.data
                    else:
                        raise Exception('unknown frame data type: %s' % event.data)
                elif isinstance(event, evt.Start):
                    self.start = event
                elif isinstance(event, evt.End):
                    self.end = event
                else:
                    pass
        except EofException:
            pass

    def __repr__(self):
        return '%s(metadata=%s, start=%s, end=%s, frames=[...])' % \
            (self.__class__.__name__, self.metadata, self.start, self.end)


    class Metadata(Base):
        """Miscellaneous data relevant to the game but not directly provided by Melee."""
        def __init__(self, date, duration, platform, players):
            self.date = date #: :py:class:`datetime`: Game start date & time
            self.duration = duration #: :py:class:`int`: Duration of game, in frames
            self.platform = platform #: :py:class:`Platform`: Platform the game was played on (console/dolphin)
            self.players = players #: tuple(optional(:py:class:`Player`)): Player metadata by port (port 1 is at index 0; empty ports will contain None)

        @classmethod
        def _parse(cls, json):
            d = json['startAt'].rstrip('\x00') # workaround for Nintendont/Slippi<1.5 bug
            # timezone & fractional seconds aren't always provided, so parse the date manually (strptime lacks support for optional components)
            m = [int(g or '0') for g in re.search(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(?:Z|\+(\d{2})(\d{2}))?$', d).groups()]
            date = datetime(*m[:7], timezone(timedelta(hours=m[7], minutes=m[8])))
            try:
                duration = 1 + json['lastFrame'] - FIRST_FRAME_INDEX
            except KeyError: duration = None
            platform = cls.Platform(json['playedOn'])
            players = [None, None, None, None]
            for i in PORTS:
                try:
                    players[i] = cls.Player._parse(json['players'][str(i)]['characters'])
                except KeyError: pass
            return cls(date=date, duration=duration, platform=platform, players=tuple(players))

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.date == other.date and self.duration == other.duration and self.platform == other.platform and self.players == other.players


        class Player(Base):
            def __init__(self, characters):
                self.characters = characters #: dict(:py:class:`slippi.id.InGameCharacter`, :py:class:`int`): Character(s) used, with usage duration in frames (for Zelda/Sheik)

            @classmethod
            def _parse(cls, json):
                characters = {}
                for char_id, duration in json.items():
                    characters[InGameCharacter(int(char_id))] = duration
                return cls(characters)

            def __eq__(self, other):
                if not isinstance(other, self.__class__):
                    return NotImplemented
                return self.characters == other.characters


        class Platform(Enum):
            CONSOLE = 'console'
            DOLPHIN = 'dolphin'
            NETWORK = 'network'
            NINTENDONT = 'nintendont'
