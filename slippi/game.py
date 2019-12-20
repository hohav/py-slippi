from slippi.event import ParseEvent
from slippi.parse import parse
from slippi.util import *


class Game(Base):
    """Replay data from a game of Super Smash Brothers Melee."""

    def __init__(self, input):
        """Parses Slippi replay data from `input` (stream or path)."""

        self.metadata = None
        """:py:class:`Metadata`: Miscellaneous data relevant to the game but not directly provided by Melee"""

        self.start = None
        """:py:class:`slippi.event.Start`: Information about the start of the game"""

        self.frames = []
        """list(:py:class:`slippi.event.Frame`): Every frame of the game, indexed by frame number (omits frames that occur before the timer starts)"""

        self.end = None
        """:py:class:`slippi.event.End`: Information about the end of the game"""

        handlers = {
            ParseEvent.METADATA: lambda x: setattr(self, 'metadata', x),
            ParseEvent.START: lambda x: setattr(self, 'start', x),
            ParseEvent.FRAME: lambda x: self.frames.append(x),
            ParseEvent.END: lambda x: setattr(self, 'end', x)}

        parse(input, handlers)

    def __repr__(self):
        return '%s(metadata=%s, start=%s, end=%s, frames=[...])' % \
            (self.__class__.__name__, self.metadata, self.start, self.end)
