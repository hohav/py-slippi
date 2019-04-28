from slippi.util import *
from slippi.id import *


unknown_enum_values_seen = {}

def try_enum(enum, val):
    try:
        return enum(val)
    except ValueError:
        name = enum.__name__
        if not name in unknown_enum_values_seen:
            unknown_enum_values_seen[name] = {}
        if not val in unknown_enum_values_seen[name]:
            unknown_enum_values_seen[name][val] = 1
            warn('unknown %s: %s' % (name, val))
        return val


class EventType(IntEnum):
    EVENT_PAYLOADS = 0x35
    GAME_START = 0x36
    FRAME_PRE = 0x37
    FRAME_POST = 0x38
    GAME_END = 0x39


class Start(Base):
    """Information used to initialize the game such as the game mode, settings, characters & stage."""

    def __init__(self, is_teams, players, random_seed, slippi, stage, is_pal):
        self.is_teams = is_teams #: :py:class:`bool`: True if this was a teams game
        self.players = players #: tuple(optional(:py:class:`Player`)): Players in this game by port (port 1 is at index 0; empty ports will contain None)
        self.random_seed = random_seed #: :py:class:`int`: Random seed before the game start
        self.slippi = slippi #: :py:class:`Slippi`: Information about the Slippi recorder that generated this replay
        self.stage = stage #: :py:class:`slippi.id.Stage`: Stage on which this game was played
        self.is_pal = is_pal #: :py:class:`bool`: True if this was a PAL version of Melee

    @classmethod
    def _parse(cls, stream):
        slippi = cls.Slippi._parse(stream)

        stream.read(8)
        (is_teams,) = unpack('?', stream)

        stream.read(5)
        (stage,) = unpack('H', stream)
        stage = Stage(stage)

        stream.read(80)
        players = []
        for i in PORTS:
            (character, type, stocks, costume) = unpack('BBBB', stream)
            character = CSSCharacter(character)

            stream.read(5)
            (team,) = unpack('B', stream)
            team = cls.Player.Team(team) if is_teams else None

            stream.read(26)
            try:
                player = cls.Player(character=character, type=cls.Player.Type(type), stocks=stocks, costume=costume, team=team)
            except ValueError: player = None

            players.append(player)

        stream.read(72)
        (random_seed,) = unpack('L', stream)

        is_pal = False
        try:
            # added: 1.0.0
            for i in PORTS:
                (dash_back, shield_drop) = unpack('LL', stream)
                dash_back = cls.Player.UCF.DashBack(dash_back)
                shield_drop = cls.Player.UCF.ShieldDrop(shield_drop)
                if players[i]:
                    players[i].ucf = cls.Player.UCF(dash_back, shield_drop)

            # added: 1.3.0
            for i in PORTS:
                tag_bytes = stream.read(16)
                if players[i]:
                    try:
                        null_pos = tag_bytes.index(0)
                        tag_bytes = tag_bytes[:null_pos]
                    except ValueError: pass
                    players[i].tag = tag_bytes.decode('shift-jis').rstrip()

            # added: 1.5.0
            (is_pal,) = unpack('?', stream)
        except EofException: pass

        return cls(is_teams=is_teams, players=tuple(players), random_seed=random_seed, slippi=slippi, stage=stage, is_pal=is_pal)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.is_teams == other.is_teams and self.players == other.players and self.random_seed == other.random_seed and self.slippi == other.slippi and self.stage is other.stage


    class Slippi(Base):
        """Information about the Slippi recorder that generated this replay."""

        def __init__(self, version):
            self.version = version #: :py:class:`Version`: Slippi version number

        @classmethod
        def _parse(cls, stream):
            return cls(cls.Version(*unpack('BBBB', stream)))

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.version == other.version


        class Version(Base):
            def __init__(self, major, minor, revision, build):
                self.major = major #: :py:class:`int`:
                self.minor = minor #: :py:class:`int`:
                self.revision = revision #: :py:class:`int`:
                self.build = build #: :py:class:`int`:

            def __repr__(self):
                return '%d.%d.%d.%d' % (self.major, self.minor, self.revision, self.build)

            def __eq__(self, other):
                if not isinstance(other, self.__class__):
                    return NotImplemented
                return self.major == other.major and self.minor == other.minor and self.revision == other.revision and self.build == other.build


    class Player(Base):
        def __init__(self, character, type, stocks, costume, team, ucf = None, tag = ""):
            self.character = character #: :py:class:`slippi.id.CSSCharacter`: Character selected
            self.type = type #: :py:class:`Type`: Player type (human/cpu)
            self.stocks = stocks #: :py:class:`int`: Starting stock count
            self.costume = costume #: :py:class:`int`: Costume ID
            self.team = team #: optional(:py:class:`Team`): Team, if this was a teams game
            self.ucf = ucf or self.UCF() #: :py:class:`UCF`: UCF feature toggles
            self.tag = tag #: :py:class:`str`: Name tag

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.character is other.character and self.type is other.type and self.stocks == other.stocks and self.costume == other.costume and self.team is other.team and self.ucf == other.ucf


        class Type(IntEnum):
            HUMAN = 0
            CPU = 1


        class Team(IntEnum):
            RED = 0
            BLUE = 1
            GREEN = 2


        class UCF(Base):
            def __init__(self, dash_back = None, shield_drop = None):
                self.dash_back = dash_back or self.DashBack.OFF #: :py:class:`DashBack`: UCF dashback state
                self.shield_drop = shield_drop or self.ShieldDrop.OFF #: :py:class:`ShieldDrop`: UCF shield drop state

            def __eq__(self, other):
                if not isinstance(other, self.__class__):
                    return NotImplemented
                return self.dash_back == other.dash_back and self.shield_drop == other.shield_drop


            class DashBack(IntEnum):
                OFF = 0
                UCF = 1
                ARDUINO = 2

            class ShieldDrop(IntEnum):
                OFF = 0
                UCF = 1
                ARDUINO = 2


class End(Base):
    """Information about the end of the game."""

    def __init__(self, method):
        self.method = method #: :py:class:`Method`: How the game ended

    @classmethod
    def _parse(cls, stream):
        (method,) = unpack('B', stream)
        return cls(cls.Method(method))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.method is other.method


    class Method(IntEnum):
        INCONCLUSIVE = 0
        CONCLUSIVE = 3


class Frame(Base):
    """A single frame of the game. Includes data for all characters."""

    __slots__ = 'index', 'ports'

    def __init__(self, index):
        self.index = index
        self.ports = [None, None, None, None]
        """tuple(optional(:py:class:`Port`)): Frame data for each port (port 1 is at index 0; empty ports will contain None)."""

    def _finalize(self):
        self.ports = tuple(self.ports)


    class Port(Base):
        """Frame data for a given port. Can include two characters' frame data (ICs)."""

        __slots__ = 'leader', 'follower'

        def __init__(self):
            self.leader = self.Data() #: :py:class:`Data`: Frame data for the controlled character
            self.follower = None #: optional(:py:class:`Data`): Frame data for the follower (Nana), if any


        class Data(Base):
            """Frame data for a given character. Includes both pre-frame and post-frame data."""

            __slots__ = 'pre', 'post'

            def __init__(self):
                self.pre = None #: :py:class:`Pre`: Pre-frame update data
                self.post = None #: :py:class:`Post`: Post-frame update data


            class Pre(Base):
                """Pre-frame update data, required to reconstruct a replay. Information is collected right before controller inputs are used to figure out the character's next action."""

                __slots__ = 'state', 'position', 'direction', 'joystick', 'cstick', 'triggers', 'buttons', 'random_seed', 'raw_analog_x', 'damage'

                def __init__(self, stream):
                    (random_seed, state, position_x, position_y, direction, joystick_x, joystick_y, cstick_x, cstick_y, trigger_logical, buttons_logical, buttons_physical, trigger_physical_l, trigger_physical_r) = unpack('LHffffffffLHff', stream)
                    self.state = try_enum(ActionState, state) #: :py:class:`slippi.id.ActionState` | int: Character's action state (useful for stats)
                    self.position = Position(position_x, position_y) #: :py:class:`Position`: Character's position
                    self.direction = Direction(direction) #: :py:class:`Direction`: Direction the character is facing
                    self.joystick = Position(joystick_x, joystick_y) #: :py:class:`Position`: Processed analog joystick position
                    self.cstick = Position(cstick_x, cstick_y) #: :py:class:`Position`: Processed analog c-stick position
                    self.triggers = Triggers(trigger_logical, trigger_physical_l, trigger_physical_r) #: :py:class:`Triggers`: Trigger state
                    self.buttons = Buttons(buttons_logical, buttons_physical) #: :py:class:`Buttons`: Button state
                    self.random_seed = random_seed #: :py:class:`int`: Random seed at this point

                    try:
                        # added: 1.2.0
                        self.raw_analog_x = unpack('B', stream) #: :py:class:`int`: Raw x analog controller input (for UCF)
                        # added: 1.4.0
                        self.damage = unpack('f', stream) #: :py:class:`float`: Current damage percent
                    except EofException: pass

            class Post(Base):
                """Post-frame update data, for making decisions about game states (such as computing stats). Information is collected at the end of collision detection, which is the last consideration of the game engine."""

                __slots__ = 'character', 'state', 'state_age', 'position', 'direction', 'damage', 'shield', 'stocks', 'last_attack_landed', 'last_hit_by', 'combo_count'

                def __init__(self, stream):
                    (character, state, position_x, position_y, direction, damage, shield, last_attack_landed, combo_count, last_hit_by, stocks) = unpack('BHfffffBBBB', stream)
                    state_age = None
                    try:
                        # added: 0.2.0
                        (state_age,) = unpack('f', stream)
                    except EofException: pass
                    self.character = InGameCharacter(character) #: :py:class:`slippi.id.InGameCharacter`: In-game character (can only change for Zelda/Sheik). Check on first frame to determine if Zelda started as Sheik
                    self.state = try_enum(ActionState, state) #: :py:class:`slippi.id.ActionState` | int: Character's action state (useful for stats)
                    self.state_age = state_age #: :py:class:`float`: Number of frames action state has been active. Can have a fractional component for certain actions
                    self.position = Position(position_x, position_y) #: :py:class:`Position`: Character's position
                    self.direction = Direction(direction) #: :py:class:`Direction`: Direction the character is facing
                    self.damage = damage #: :py:class:`float`: Current damage percent
                    self.shield = shield #: :py:class:`float`: Current size of shield
                    self.stocks = stocks #: :py:class:`int`: Number of stocks remaining
                    self.last_attack_landed = try_enum(Attack, last_attack_landed) if last_attack_landed else None #: optional(:py:class:`Attack` | int): Last attack that this character landed
                    self.last_hit_by = last_hit_by if last_hit_by < 4 else None #: optional(:py:class:`int`): Port of character that last hit this character
                    self.combo_count = combo_count #: :py:class:`int`: Combo count as defined by the game


    # This class is only used temporarily while parsing frame data.
    class Event(Base):
        def __init__(self, id, data):
            self.id = id
            self.data = data


        class Id(Base):
            def __init__(self, stream):
                (self.frame, self.port, self.is_follower) = unpack('iB?', stream)


class Position(Base):
    __slots__ = 'x', 'y'

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return '(%.2f, %.2f)' % (self.x, self.y)


class Direction(IntEnum):
    LEFT = -1
    RIGHT = 1


class Attack(IntEnum):
    OTHER = 1
    JAB = 2
    JAB_2 = 3
    JAB_3 = 4
    JAB_LOOP = 5
    DASH_ATTACK = 6
    FTILT = 7
    UTILT = 8
    DTILT = 9
    FSMASH = 10
    USMASH = 11
    DSMASH = 12
    NAIR = 13
    FAIR = 14
    BAIR = 15
    UAIR = 16
    DAIR = 17
    NEUTRAL_B = 18
    SIDE_B = 19
    UP_B = 20
    DOWN_B = 21
    GETUP_ATTACK = 50
    GETUP_ATTACK_SLOW = 51
    GRAB_RELEASE = 52
    FTHROW = 53
    BTHROW = 54
    UTHROW = 55
    DTHROW = 56
    LEDGE_ATTACK_SLOW = 61
    LEDGE_ATTACK = 62


class Triggers(Base):
    __slots__ = 'logical', 'physical'

    def __init__(self, logical, physical_x, physical_y):
        self.logical = logical #: :py:class:`float`: Processed analog trigger position
        self.physical = self.Physical(physical_x, physical_y) #: :py:class:`Physical`: physical analog trigger positions (useful for APM)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return other.logical == self.logical and other.physical == self.physical


    class Physical(Base):
        __slots__ = 'l', 'r'

        def __init__(self, l, r):
            self.l = l
            self.r = r

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            # Should we add an epsilon to these comparisons? When are people going to be comparing trigger states for equality, other than in our tests?
            return other.l == self.l and other.r == self.r


class Buttons(Base):
    __slots__ = 'logical', 'physical'

    def __init__(self, logical, physical):
        self.logical = self.Logical(logical) #: :py:class:`Logical`: Processed button-state bitmask
        self.physical = self.Physical(physical) #: :py:class:`Physical`: Physical button-state bitmask

    def __eq__(self, other):
        if not isinstance(other, Buttons):
            return NotImplemented
        return other.logical is self.logical and other.physical is self.physical


    class Logical(IntFlag):
        TRIGGER_ANALOG = 2**31
        CSTICK_RIGHT = 2**23
        CSTICK_LEFT = 2**22
        CSTICK_DOWN = 2**21
        CSTICK_UP = 2**20
        JOYSTICK_RIGHT = 2**19
        JOYSTICK_LEFT = 2**18
        JOYSTICK_DOWN = 2**17
        JOYSTICK_UP = 2**16
        START = 2**12
        Y = 2**11
        X = 2**10
        B = 2**9
        A = 2**8
        L = 2**6
        R = 2**5
        Z = 2**4
        DPAD_UP = 2**3
        DPAD_DOWN = 2**2
        DPAD_RIGHT = 2**1
        DPAD_LEFT = 2**0
        NONE = 0


    class Physical(IntFlag):
        START = 2**12
        Y = 2**11
        X = 2**10
        B = 2**9
        A = 2**8
        L = 2**6
        R = 2**5
        Z = 2**4
        DPAD_UP = 2**3
        DPAD_DOWN = 2**2
        DPAD_RIGHT = 2**1
        DPAD_LEFT = 2**0
        NONE = 0

        def pressed(self):
            """Returns a list of all buttons being pressed."""
            pressed = []
            for b in self.__class__:
                if self & b:
                    pressed.append(b)
            return pressed
