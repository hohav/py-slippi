from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from . import event as evt
from . import id as sid
from .util import *


class Metadata(Base):
    """Miscellaneous data not directly provided by Melee."""

    date: datetime #: Game start date & time
    duration: int #: Duration of game, in frames
    platform: Metadata.Platform #: Platform the game was played on (console/dolphin)
    players: Tuple[Optional[Metadata.Player]] #: Player metadata by port (port 1 is at index 0; empty ports will contain None)
    console_name: Optional[str] #: Name of the console the game was played on, if any

    def __init__(self, date: datetime, duration: int, platform: Metadata.Platform, players: Tuple[Optional[Metadata.Player]], console_name: Optional[str] = None):
        self.date = date
        self.duration = duration
        self.platform = platform
        self.players = players
        self.console_name = console_name

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
        return cls(date=date, duration=duration, platform=platform, players=tuple(players), console_name=console_name)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.date == other.date and self.duration == other.duration and self.platform == other.platform and self.players == other.players and self.console_name == other.console_name


    class Player(Base):
        characters: Dict[sid.InGameCharacter, int] #: Character(s) used, with usage duration in frames (for Zelda/Sheik)
        netplay: Optional[Metadata.Player.Netplay] #: Netplay info (Dolphin-only)

        def __init__(self, characters: Dict[sid.InGameCharacter, int], netplay: Optional[Metadata.Player.Netplay] = None):
            self.characters = characters
            self.netplay = netplay

        @classmethod
        def _parse(cls, json):
            characters = {}
            for char_id, duration in json['characters'].items():
                characters[sid.InGameCharacter(int(char_id))] = duration
            try:
                netplay = cls.Netplay(code=json['names']['code'], name=json['names']['netplay'])
            except KeyError: netplay = None
            return cls(characters, netplay)

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.characters == other.characters and self.netplay == other.netplay


        class Netplay(Base):
            code: str #: Netplay code (e.g. "ABCD#123")
            name: str #: Netplay nickname

            def __init__(self, code: str, name: str):
                self.code = code
                self.name = name

            def __eq__(self, other):
                if not isinstance(other, self.__class__):
                    return NotImplemented
                return self.code == other.code and self.name == other.name


    class Platform(Enum):
        CONSOLE = 'console'
        DOLPHIN = 'dolphin'
        NETWORK = 'network'
        NINTENDONT = 'nintendont'
