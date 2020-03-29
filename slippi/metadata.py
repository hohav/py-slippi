import re
from datetime import datetime, timedelta, timezone

import slippi.event as evt
import slippi.id as id
from slippi.util import *


class Metadata(Base):
    """Miscellaneous data relevant to the game but not directly provided by Melee."""
    def __init__(self, date, duration, platform, players, console_name, _json):
        self.date = date #: :py:class:`datetime`: Game start date & time
        self.duration = duration #: :py:class:`int`: Duration of game, in frames
        self.platform = platform #: :py:class:`Platform`: Platform the game was played on (console/dolphin)
        self.players = players #: tuple(optional(:py:class:`Player`)): Player metadata by port (port 1 is at index 0; empty ports will contain None)
        self.console_name = console_name #: optional(:py:class:`str`): Name of the console the game was played on, None if not present
        self._json = _json #: :py:class:`dict`: Copy of json metadata for forwards compatibility with replays

    @classmethod
    def _parse(cls, json):
        d = json['startAt'].rstrip('\x00') # workaround for Nintendont/Slippi<1.5 bug
        # timezone & fractional seconds aren't always provided, so parse the date manually (strptime lacks support for optional components)
        m = [int(g or '0') for g in re.search(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(?:Z|\+(\d{2})(\d{2}))?$', d).groups()]
        date = datetime(*m[:7], timezone(timedelta(hours=m[7], minutes=m[8])))
        try: duration = 1 + json['lastFrame'] - evt.FIRST_FRAME_INDEX
        except KeyError: duration = None
        platform = cls.Platform(json['playedOn'])
        try: console_name = json['consoleNick']
        except KeyError: console_name = None
        players = [None, None, None, None]
        for i in PORTS:
            try: players[i] = cls.Player._parse(json['players'][str(i)])
            except KeyError: pass
        return cls(date=date, duration=duration, platform=platform, players=tuple(players), console_name=console_name, _json=json)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.date == other.date and self.duration == other.duration and self.platform == other.platform and self.players == other.players and self.console_name == other.console_name


    class Player(Base):
        def __init__(self, characters, netplay_name):
            self.characters = characters #: dict(:py:class:`slippi.id.InGameCharacter`, :py:class:`int`): Character(s) used, with usage duration in frames (for Zelda/Sheik)
            self.netplay_name = netplay_name #: optional(:py:class:`str`): Netplay name of player if played on dolphin, None if not present

        @classmethod
        def _parse(cls, json):
            characters = {}
            for char_id, duration in json['characters'].items():
                characters[id.InGameCharacter(int(char_id))] = duration
            try: netplay_name = json['names']['netplay']
            except KeyError: netplay_name = None
            return cls(characters, netplay_name)

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.characters == other.characters and self.netplay_name == other.netplay_name


    class Platform(Enum):
        CONSOLE = 'console'
        DOLPHIN = 'dolphin'
        NETWORK = 'network'
        NINTENDONT = 'nintendont'
