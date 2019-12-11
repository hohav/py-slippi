import re
from datetime import datetime, timedelta, timezone

import slippi.event as evt
import slippi.id as id
from slippi.util import *


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
            duration = 1 + json['lastFrame'] - evt.FIRST_FRAME_INDEX
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
                characters[id.InGameCharacter(int(char_id))] = duration
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
