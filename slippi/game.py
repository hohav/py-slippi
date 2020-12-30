import io
from logging import debug
from typing import List, Optional, Union

from .event import FIRST_FRAME_INDEX, End, Frame, Start
from .metadata import Metadata
from .parse import ParseEvent, parse
from .util import *


class Game(Base):
    """Replay data from a game of Super Smash Brothers Melee."""

    start: Optional[Start]
    frames: List[Frame]
    end: Optional[End]
    metadata: Optional[Metadata]
    metadata_raw: Optional[dict]

    def __init__(self, input: Union[io.BytesIO, str]):
        """Parses Slippi replay data from `input` (stream or path)."""

        self.start = None
        """:py:class:`slippi.event.Start`: Information about the start of the game"""

        self.frames = []
        """list(:py:class:`slippi.event.Frame`): Every frame of the game, indexed by frame number"""

        self.end = None
        """:py:class:`slippi.event.End`: Information about the end of the game"""

        self.metadata = None
        """:py:class:`slippi.metadata.Metadata`: Miscellaneous data not directly provided by Melee"""

        self.metadata_raw = None
        """dict: Raw JSON metadata, for debugging and forward-compatibility"""

        handlers = {
            ParseEvent.START: lambda x: setattr(self, 'start', x),
            ParseEvent.FRAME: self._add_frame,
            ParseEvent.END: lambda x: setattr(self, 'end', x),
            ParseEvent.METADATA: lambda x: setattr(self, 'metadata', x),
            ParseEvent.METADATA_RAW: lambda x: setattr(self, 'metadata_raw', x)}

        parse(input, handlers)

    def _add_frame(self, f):
        idx = f.index - FIRST_FRAME_INDEX
        count = len(self.frames)
        if idx == count:
            self.frames.append(f)
        elif idx < count: # rollback
            debug(f"rollback: {count-1} -> {idx}")
            self.frames[idx] = f
        else:
            raise Exception(f'missing frames: {count-1} -> {idx}')

    def _attr_repr(self, attr):
        self_attr = getattr(self, attr)
        if isinstance(self_attr, list):
            return '%s=[...](%d)' % (attr, len(self_attr))
        elif attr == 'metadata_raw':
            return None
        else:
            return super()._attr_repr(attr)
