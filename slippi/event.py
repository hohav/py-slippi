from slippi.util import *
from slippi.id import *


# The first frame of the game is indexed -123, counting up to zero (which is when the word "GO" appears). But since players actually get control before frame zero (!!!), we need to record these frames.
FIRST_FRAME_INDEX = -123


class EventType(IntEnum):
    """Slippi events that can appear in a game's `raw` data."""

    EVENT_PAYLOADS = 0x35
    GAME_START = 0x36
    FRAME_PRE = 0x37
    FRAME_POST = 0x38
    GAME_END = 0x39
    FRAME_START = 0x3A
    ITEM_UPDATE = 0x3B
    FRAME_BOOKEND = 0x3C


class ParseEvent(Enum):
    """Parser events, used as keys for event handlers. Docstrings indicate the type of object that will be passed to each handler."""

    METADATA = 'metadata' #: :py:class:`slippi.metadata.Metadata`:
    METADATA_RAW = 'metadata_raw' #: dict:
    START = 'start' #: :py:class:`Start`:
    FRAME = 'frame' #: :py:class:`Frame`:
    END = 'end' #: :py:class:`End`:
    FRAME_START = 'frame_start' #: :py:class:`FrameStart`:
    ITEM_UPDATE = 'item_update' #: :py:class:`ItemUpdate`:
    FRAME_BOOKEND = 'frame_bookend' #: :py:class:`FrameBookend`:


class Start(Base):
    """Information used to initialize the game such as the game mode, settings, characters & stage."""

    def __init__(self, is_teams, players, random_seed, slippi, stage, is_pal = None, is_frozen_ps = None):
        self.is_teams = is_teams #: bool: True if this was a teams game
        self.players = players #: tuple(:py:class:`Player` | None): Players in this game by port (port 1 is at index 0; empty ports will contain None)
        self.random_seed = random_seed #: int: Random seed before the game start
        self.slippi = slippi #: :py:class:`Slippi`: Information about the Slippi recorder that generated this replay
        self.stage = stage #: :py:class:`slippi.id.Stage`: Stage on which this game was played
        self.is_pal = is_pal #: bool | None: `added(1.5.0)` True if this was a PAL version of Melee
        self.is_frozen_ps = is_frozen_ps #: bool | None: `added(2.0.0)` True if frozen Pokemon Stadium was enabled

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

            stream.read(5)
            (team,) = unpack('B', stream)
            stream.read(26)

            try: type = cls.Player.Type(type)
            except ValueError: type = None

            if type is not None:
                character = CSSCharacter(character)
                team = cls.Player.Team(team) if is_teams else None
                player = cls.Player(character=character, type=type, stocks=stocks, costume=costume, team=team)
            else:
                player = None

            players.append(player)

        stream.read(72)
        (random_seed,) = unpack('L', stream)

        try: # v1.0.0
            for i in PORTS:
                (dash_back, shield_drop) = unpack('LL', stream)
                dash_back = cls.Player.UCF.DashBack(dash_back)
                shield_drop = cls.Player.UCF.ShieldDrop(shield_drop)
                if players[i]:
                    players[i].ucf = cls.Player.UCF(dash_back, shield_drop)
        except EofException: pass

        try: # v1.3.0
            for i in PORTS:
                tag_bytes = stream.read(16)
                if players[i]:
                    try:
                        null_pos = tag_bytes.index(0)
                        tag_bytes = tag_bytes[:null_pos]
                    except ValueError: pass
                    players[i].tag = tag_bytes.decode('shift-jis').rstrip()
        except EofException: pass

        # v1.5.0
        try: (is_pal,) = unpack('?', stream)
        except EofException: is_pal = None

        # v2.0.0
        try: (is_frozen_ps,) = unpack('?', stream)
        except EofException: is_frozen_ps = None

        return cls(is_teams=is_teams, players=tuple(players), random_seed=random_seed, slippi=slippi, stage=stage, is_pal=is_pal, is_frozen_ps=is_frozen_ps)

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
            def __init__(self, major, minor, revision, build = None):
                self.major = major #: int:
                self.minor = minor #: int:
                self.revision = revision #: int:
                # build was obsoleted in 2.0.0, and never held a nonzero value

            def __repr__(self):
                return '%d.%d.%d' % (self.major, self.minor, self.revision)

            def __eq__(self, other):
                if not isinstance(other, self.__class__):
                    return NotImplemented
                return self.major == other.major and self.minor == other.minor and self.revision == other.revision


    class Player(Base):
        def __init__(self, character, type, stocks, costume, team, ucf = None, tag = None):
            self.character = character #: :py:class:`slippi.id.CSSCharacter`: Character selected
            self.type = type #: :py:class:`Type`: Player type (human/cpu)
            self.stocks = stocks #: int: Starting stock count
            self.costume = costume #: int: Costume ID
            self.team = team #: :py:class:`Team` | None: Team, if this was a teams game
            self.ucf = ucf or self.UCF() #: :py:class:`UCF`: UCF feature toggles
            self.tag = tag #: str | None: Name tag

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

    def __init__(self, method, lras_initiator = None):
        self.method = method #: :py:class:`Method`: `changed(2.0.0)` How the game ended
        self.lras_initiator = lras_initiator #: int | None: `added(2.0.0)` Index of player that LRAS'd, if any

    @classmethod
    def _parse(cls, stream):
        (method,) = unpack('B', stream)
        try: # v2.0.0
            (lras,) = unpack('B', stream)
            lras_initiator = lras if lras < len(PORTS) else None
        except EofException:
            lras_initiator = None
        return cls(cls.Method(method), lras_initiator)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.method is other.method


    class Method(IntEnum):
        INCONCLUSIVE = 0 # `obsoleted(2.0.0)`
        TIME = 1 # `added(2.0.0)`
        GAME = 2 # `added(2.0.0)`
        CONCLUSIVE = 3 # `obsoleted(2.0.0)`
        NO_CONTEST = 7 # `added(2.0.0)`


class Frame(Base):
    """A single frame of the game. Includes data for all characters."""

    __slots__ = 'index', 'ports'

    def __init__(self, index):
        self.index = index
        self.ports = [None, None, None, None]
        """tuple(:py:class:`Port` | None): Frame data for each port (port 1 is at index 0; empty ports will contain None)."""

    def _finalize(self):
        self.ports = tuple(self.ports)


    class Port(Base):
        """Frame data for a given port. Can include two characters' frame data (ICs)."""

        __slots__ = 'leader', 'follower'

        def __init__(self):
            self.leader = self.Data() #: :py:class:`Data`: Frame data for the controlled character
            self.follower = None #: :py:class:`Data` | None: Frame data for the follower (Nana), if any


        class Data(Base):
            """Frame data for a given character. Includes both pre-frame and post-frame data."""

            __slots__ = '_pre', '_post'

            def __init__(self):
                self._pre = None
                self._post = None

            @property
            def pre(self):
                """:py:class:`Pre`: Pre-frame update data"""
                if not isinstance(self._pre, self.Pre):
                    self._pre = self.Pre(self._pre)
                return self._pre

            @property
            def post(self):
                """:py:class:`Post`: Pre-frame update data"""
                if not isinstance(self._post, self.Post):
                    self._post = self.Post(self._post)
                return self._post


            class Pre(Base):
                """Pre-frame update data, required to reconstruct a replay. Information is collected right before controller inputs are used to figure out the character's next action."""

                __slots__ = 'state', 'position', 'direction', 'joystick', 'cstick', 'triggers', 'buttons', 'random_seed', 'raw_analog_x', 'damage'

                def __init__(self, stream):
                    (random_seed, state, position_x, position_y, direction, joystick_x, joystick_y, cstick_x, cstick_y, trigger_logical, buttons_logical, buttons_physical, trigger_physical_l, trigger_physical_r) = unpack('LHffffffffLHff', stream)

                    # v1.2.0
                    try: raw_analog_x = unpack('B', stream)
                    except EofException: raw_analog_x = None

                    # v1.4.0
                    try: damage = unpack('f', stream)
                    except EofException: damage = None

                    self.state = try_enum(ActionState, state) #: :py:class:`slippi.id.ActionState` | int: Character's action state
                    self.position = Position(position_x, position_y) #: :py:class:`Position`: Character's position
                    self.direction = Direction(direction) #: :py:class:`Direction`: Direction the character is facing
                    self.joystick = Position(joystick_x, joystick_y) #: :py:class:`Position`: Processed analog joystick position
                    self.cstick = Position(cstick_x, cstick_y) #: :py:class:`Position`: Processed analog c-stick position
                    self.triggers = Triggers(trigger_logical, trigger_physical_l, trigger_physical_r) #: :py:class:`Triggers`: Trigger state
                    self.buttons = Buttons(buttons_logical, buttons_physical) #: :py:class:`Buttons`: Button state
                    self.random_seed = random_seed #: int: Random seed at this point
                    self.raw_analog_x = raw_analog_x #: int | None: `added(1.2.0)` Raw x analog controller input (for UCF)
                    self.damage = damage #: float | None: `added(1.4.0)` Current damage percent


            class Post(Base):
                """Post-frame update data, for making decisions about game states (such as computing stats). Information is collected at the end of collision detection, which is the last consideration of the game engine."""

                __slots__ = 'character', 'state', 'state_age', 'position', 'direction', 'damage', 'shield', 'stocks', 'last_attack_landed', 'last_hit_by', 'combo_count', 'flags', 'hit_stun', 'airborne', 'ground', 'jumps', 'l_cancel'

                def __init__(self, stream):
                    (character, state, position_x, position_y, direction, damage, shield, last_attack_landed, combo_count, last_hit_by, stocks) = unpack('BHfffffBBBB', stream)

                    # v0.2.0
                    try: (state_age,) = unpack('f', stream)
                    except EofException: state_age = None

                    try: # v2.0.0
                        flags = unpack('5B', stream)
                        (misc_as, airborne, maybe_ground, jumps, l_cancel) = unpack('f?HBB', stream)
                        flags = StateFlags(flags[0] +
                                           flags[1] * 2**8 +
                                           flags[2] * 2**16 +
                                           flags[3] * 2**24 +
                                           flags[4] * 2**32)
                        ground = maybe_ground if not airborne else None
                        hit_stun = misc_as if flags.HIT_STUN else None
                        l_cancel = LCancel(l_cancel) if l_cancel else None
                    except EofException:
                        (flags, hit_stun, airborne, ground, jumps, l_cancel) = [None] * 6

                    self.character = InGameCharacter(character) #: :py:class:`slippi.id.InGameCharacter`: In-game character (can only change for Zelda/Sheik). Check on first frame to determine if Zelda started as Sheik
                    self.state = try_enum(ActionState, state) #: :py:class:`slippi.id.ActionState` | int: Character's action state
                    self.state_age = state_age #: float | None: Number of frames action state has been active. Can have a fractional component for certain actions
                    self.position = Position(position_x, position_y) #: :py:class:`Position`: Character's position
                    self.direction = Direction(direction) #: :py:class:`Direction`: Direction the character is facing
                    self.damage = damage #: float: Current damage percent
                    self.shield = shield #: float: Current size of shield
                    self.stocks = stocks #: int: Number of stocks remaining
                    self.last_attack_landed = try_enum(Attack, last_attack_landed) if last_attack_landed else None #: :py:class:`Attack` | int | None: Last attack that this character landed
                    self.last_hit_by = last_hit_by if last_hit_by < 4 else None #: int | None: Port of character that last hit this character
                    self.combo_count = combo_count #: int: Combo count as defined by the game
                    self.flags = flags #: :py:class:`StateFlags` | None: `added(2.0.0)` State flags
                    self.hit_stun = hit_stun #: float | None: `added(2.0.0)` Number of hitstun frames remaining
                    self.airborne = airborne #: bool | None: `added(2.0.0)` True if character is airborne
                    self.ground = ground #: int | None: `added(2.0.0)` ID of ground character is standing on, if any
                    self.jumps = jumps #: int | None: `added(2.0.0)` Jumps remaining
                    self.l_cancel = l_cancel #: :py:class:`LCancel` | None: `added(2.0.0)` L-cancel status, if any


    # This class is only used temporarily while parsing frame data.
    class Event(Base):
        __slots__ = 'id', 'type', 'data'

        def __init__(self, id, type, data):
            self.id = id
            self.type = type
            self.data = data


        class Id(Base):
            __slots__ = 'frame', 'port', 'is_follower'

            def __init__(self, stream):
                (self.frame, self.port, self.is_follower) = unpack('iB?', stream)


        class Type(Enum):
            PRE = 'pre'
            POST = 'post'


class FrameStart(Base):
    """Frame and random seed information."""

    __slots__ = 'frame_number', 'random_seed'

    def __init__(self, frame_number, random_seed):
        self.frame_number = frame_number #: int `added(2.2.0)` The number of the frame
        self.random_seed = random_seed #: int: `added(2.2.0)` The random seed at the start of the frame

    @classmethod
    def _parse(cls, stream):
        (frame_number, random_seed) = unpack('iI', stream)
        return cls(frame_number, random_seed)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.frame_number == other.frame_number) and (self.random_seed == other.random_seed)


class ItemUpdate(Base):
    """Information about 15 or fewer specific items"""

    __slots__ = 'frame_number', 'type_id', 'state', 'direction', 'velocity', 'position', 'damage', 'timer', 'spawn_id'

    def __init__(self, frame_number, type_id, state, direction, x_vel, y_vel, x_pos, y_pos, damage, timer, spawn_id):
        self.frame_number = frame_number #: int: `added(3.0.0)` The number of the frame
        self.type_id = try_enum(Item, type_id) #: :py:class:`slippi.id.Item` | int: `added(3.0.0)` Type of item
        self.state = state #: int: `added(3.0.0)` The item's state
        self.direction = Direction(direction) #: :py:class:`Direction`: `added(3.0.0)` Direction the character is facing
        self.velocity = Velocity(x_vel, y_vel) #: :py:class:`Velocity`: `added(3.0.0)` Character's velocity
        self.position = Position(x_pos, y_pos) #: :py:class:`Position`: `added(3.0.0)` Character's position
        self.damage = damage #: int: `added(3.0.0)` Amount of damage item has taken
        self.timer = timer #: int: `added(3.0.0)` Number of frames before item expires
        self.spawn_id = spawn_id #: int int: `added(3.0.0)` Number representing item

    @classmethod
    def _parse(cls, stream):
        (frame_number, type_id, state, direction, x_vel, y_vel, x_pos, y_pos, damage, timer, spawn_id) = unpack('iHB5fHfI', stream)
        return cls(frame_number, type_id, state, direction, x_vel, y_vel, x_pos, y_pos, damage, timer, spawn_id)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return ((self.frame_number == other.frame_number)
            and (self.type_id == other.type_id)
            and (self.state == other.state)
            and (self.direction == other.direction)
            and (self.velocity == other.velocity)
            and (self.position == other.position)
            and (self.damage == other.damage)
            and (self.timer == other.timer)
            and (self.spawn_id == other.spawn_id))


class FrameBookend(Base):
    """Marks the end of a frame."""

    __slots__ = 'frame_number'

    def __init__(self, frame_number):
        self.frame_number = frame_number #: int | None: `added(3.0.0)` The number of the frame

    @classmethod
    def _parse(cls, stream):
        (frame_number,) = unpack('i', stream)
        return cls(frame_number)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.frame_number == other.frame_number


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


class Velocity(Base):
    __slots__ = 'x_vel', 'y_vel'

    def __init__(self, x_vel, y_vel):
        self.x = x_vel
        self.y = y_vel

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.x_vel == other.x_vel and self.y_vel == other.y_vel

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
        self.logical = logical #: float: Processed analog trigger position
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


class LCancel(IntEnum):
    SUCCESS = 1
    FAILURE = 2


class StateFlags(IntFlag):
    REFLECT = 2**4
    UNTOUCHABLE = 2**10
    FAST_FALL = 2**11
    HIT_LAG = 2**13
    SHIELD = 2**23
    HIT_STUN = 2**25
    SHIELD_TOUCH = 2**26
    POWER_SHIELD = 2**29
    FOLLOWER = 2**35
    SLEEP = 2**36
    DEAD = 2**38
    OFF_SCREEN = 2**39
