from typing import Optional, Sequence, Tuple, Union

from . import id as sid
from .util import *

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
    ITEM = 0x3B
    FRAME_END = 0x3C


class Start(Base):
    """Information used to initialize the game such as the game mode, settings, characters & stage."""

    is_teams: bool
    players: Tuple[Optional["Player"]]
    random_seed: int
    slippi: "Slippi"
    stage: sid.Stage
    is_pal: Optional[bool]
    is_frozen_ps: Optional[bool]

    def __init__(self, is_teams: bool, players: Tuple[Optional["Player"]], random_seed: int, slippi: "Slippi", stage: sid.Stage, is_pal: Optional[bool] = None, is_frozen_ps: Optional[bool] = None):
        self.is_teams = is_teams #: bool: True if this was a teams game
        self.players = players #: tuple(:py:class:`Player` | None): Players in this game by port (port 1 is at index 0; empty ports will contain None)
        self.random_seed = random_seed #: int: Random seed before the game start
        self.slippi = slippi #: :py:class:`Slippi`: Information about the Slippi recorder that generated this replay
        self.stage = stage #: :py:class:`slippi.id.Stage`: Stage on which this game was played
        self.is_pal = is_pal #: bool | None: `added(1.5.0)` True if this was a PAL version of Melee
        self.is_frozen_ps = is_frozen_ps #: bool | None: `added(2.0.0)` True if frozen Pokemon Stadium was enabled

    @classmethod
    def _parse(cls, stream):
        slippi_ = cls.Slippi._parse(stream)

        stream.read(8)
        (is_teams,) = unpack('?', stream)

        stream.read(5)
        (stage,) = unpack('H', stream)
        stage = sid.Stage(stage)

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
                character = sid.CSSCharacter(character)
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
        except EOFError: pass

        try: # v1.3.0
            for i in PORTS:
                tag_bytes = stream.read(16)
                if players[i]:
                    try:
                        null_pos = tag_bytes.index(0)
                        tag_bytes = tag_bytes[:null_pos]
                    except ValueError: pass
                    players[i].tag = tag_bytes.decode('shift-jis').rstrip()
        except EOFError: pass

        # v1.5.0
        try: (is_pal,) = unpack('?', stream)
        except EOFError: is_pal = None

        # v2.0.0
        try: (is_frozen_ps,) = unpack('?', stream)
        except EOFError: is_frozen_ps = None

        return cls(
            is_teams=is_teams,
            players=tuple(players),
            random_seed=random_seed,
            slippi=slippi_,
            stage=stage,
            is_pal=is_pal,
            is_frozen_ps=is_frozen_ps)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.is_teams == other.is_teams and self.players == other.players and self.random_seed == other.random_seed and self.slippi == other.slippi and self.stage is other.stage


    class Slippi(Base):
        """Information about the Slippi recorder that generated this replay."""

        version: "Version"

        def __init__(self, version: "Version"):
            self.version = version #: :py:class:`Version`: Slippi version number

        @classmethod
        def _parse(cls, stream):
            return cls(cls.Version(*unpack('BBBB', stream)))

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.version == other.version


        class Version(Base):

            major: int
            minor: int
            revision: int

            def __init__(self, major: int, minor: int, revision: int, build = None):
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

        character: sid.CSSCharacter
        type: "Type"
        stocks: int
        costume: int
        team: Optional["Team"]
        ucf: "UCF"
        tag: Optional[str]

        def __init__(self, character: sid.CSSCharacter, type: "Type", stocks: int, costume: int, team: Optional["Team"], ucf: "UCF" = None, tag: Optional[str] = None):
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

            dash_back: "DashBack"
            shield_drop: "ShieldDrop"

            def __init__(self, dash_back: "DashBack" = None, shield_drop: "ShieldDrop" = None):
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

    method: "Method"
    lras_initiator: Optional[int]

    def __init__(self, method: "Method", lras_initiator: Optional[int] = None):
        self.method = method #: :py:class:`Method`: `changed(2.0.0)` How the game ended
        self.lras_initiator = lras_initiator #: int | None: `added(2.0.0)` Index of player that LRAS'd, if any

    @classmethod
    def _parse(cls, stream):
        (method,) = unpack('B', stream)
        try: # v2.0.0
            (lras,) = unpack('B', stream)
            lras_initiator = lras if lras < len(PORTS) else None
        except EOFError:
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

    __slots__ = 'index', 'ports', 'items', 'start', 'end'

    index: int
    ports: Sequence[Optional["Port"]]
    items: Sequence["Item"]
    start: Optional["Start"]
    end: Optional["End"]

    def __init__(self, index: int):
        self.index = index
        self.ports = [None, None, None, None] #: tuple(:py:class:`Port` | None): Frame data for each port (port 1 is at index 0; empty ports will contain None)
        self.items = [] #: tuple(:py:class:`Item`): `added(3.0.0)` Active items (includes projectiles)
        self.start = None #: :py:class:`Start` | None: `added(2.2.0)` Start-of-frame data
        self.end = None #: :py:class:`End` | None: `added(2.2.0)` End-of-frame data

    def _finalize(self):
        self.ports = tuple(self.ports)
        self.items = tuple(self.items)


    class Port(Base):
        """Frame data for a given port. Can include two characters' frame data (ICs)."""

        __slots__ = 'leader', 'follower'

        leader: "Data"
        follower: Optional["Data"]

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
                if self._pre and not isinstance(self._pre, self.Pre):
                    self._pre = self.Pre._parse(self._pre)
                return self._pre

            @property
            def post(self):
                """:py:class:`Post`: Post-frame update data"""
                if self._post and not isinstance(self._post, self.Post):
                    self._post = self.Post._parse(self._post)
                return self._post


            class Pre(Base):
                """Pre-frame update data, required to reconstruct a replay. Information is collected right before controller inputs are used to figure out the character's next action."""

                __slots__ = 'state', 'position', 'direction', 'joystick', 'cstick', 'triggers', 'buttons', 'random_seed', 'raw_analog_x', 'damage'

                state: Union[sid.ActionState, int]
                position: "Position"
                direction: "Direction"
                joystick: "Position"
                cstick: "Position"
                triggers: "Triggers"
                buttons: "Buttons"
                random_seed: int
                raw_analog_x: Optional[int]
                damage: Optional[float]
                
                def __init__(self, state: Union[sid.ActionState, int], position: "Position", direction: "Direction", joystick: "Position", cstick: "Position", triggers: "Triggers", buttons: "Buttons", random_seed: int, raw_analog_x: Optional[int] = None, damage: Optional[float] = None):
                    self.state = state #: :py:class:`slippi.id.ActionState` | int: Character's action state
                    self.position = position #: :py:class:`Position`: Character's position
                    self.direction = direction #: :py:class:`Direction`: Direction the character is facing
                    self.joystick = joystick #: :py:class:`Position`: Processed analog joystick position
                    self.cstick = cstick #: :py:class:`Position`: Processed analog c-stick position
                    self.triggers = triggers #: :py:class:`Triggers`: Trigger state
                    self.buttons = buttons #: :py:class:`Buttons`: Button state
                    self.random_seed = random_seed #: int: Random seed at this point
                    self.raw_analog_x = raw_analog_x #: int | None: `added(1.2.0)` Raw x analog controller input (for UCF)
                    self.damage = damage #: float | None: `added(1.4.0)` Current damage percent

                @classmethod
                def _parse(cls, stream):
                    (random_seed, state, position_x, position_y, direction, joystick_x, joystick_y, cstick_x, cstick_y, trigger_logical, buttons_logical, buttons_physical, trigger_physical_l, trigger_physical_r) = unpack('LHffffffffLHff', stream)

                    # v1.2.0
                    try: raw_analog_x = unpack('B', stream)
                    except EOFError: raw_analog_x = None

                    # v1.4.0
                    try: damage = unpack('f', stream)
                    except EOFError: damage = None

                    return cls(
                        state=try_enum(sid.ActionState, state),
                        position=Position(position_x, position_y),
                        direction=Direction(direction),
                        joystick=Position(joystick_x, joystick_y),
                        cstick=Position(cstick_x, cstick_y),
                        triggers=Triggers(trigger_logical, trigger_physical_l, trigger_physical_r),
                        buttons=Buttons(buttons_logical, buttons_physical),
                        random_seed=random_seed,
                        raw_analog_x=raw_analog_x,
                        damage=damage)


            class Post(Base):
                """Post-frame update data, for making decisions about game states (such as computing stats). Information is collected at the end of collision detection, which is the last consideration of the game engine."""

                __slots__ = 'character', 'state', 'position', 'direction', 'damage', 'shield', 'stocks', 'last_attack_landed', 'last_hit_by', 'combo_count', 'state_age', 'flags', 'hit_stun', 'airborne', 'ground', 'jumps', 'l_cancel'

                character: sid.InGameCharacter
                state: Union[sid.ActionState, int]
                position: "Position"
                direction: "Direction"
                damage: float
                shield: float
                stocks: int
                last_attack_landed: Optional[Union["Attack", int]]
                last_hit_by: Optional[int]
                combo_count: int
                state_age: Optional[float]
                flags: Optional["StateFlags"]
                hit_stun: Optional[float]
                airborne: Optional[bool]
                ground: Optional[int]
                jumps: Optional[int]
                l_cancel: Optional["LCancel"]
                
                def __init__(self, character: sid.InGameCharacter, state: Union[sid.ActionState, int], position: "Position", direction: "Direction", damage: float, shield: float, stocks: int, last_attack_landed: Optional[Union["Attack", int]], last_hit_by: Optional[int], combo_count: int, state_age: Optional[float] = None, flags: Optional["StateFlags"] = None, hit_stun: Optional[float] = None, airborne: Optional[bool] = None, ground: Optional[int] = None, jumps: Optional[int] = None, l_cancel: Optional["LCancel"] = None):
                    self.character = character #: :py:class:`slippi.id.InGameCharacter`: In-game character (can only change for Zelda/Sheik). Check on first frame to determine if Zelda started as Sheik
                    self.state = state #: :py:class:`slippi.id.ActionState` | int: Character's action state
                    self.position = position #: :py:class:`Position`: Character's position
                    self.direction = direction #: :py:class:`Direction`: Direction the character is facing
                    self.damage = damage #: float: Current damage percent
                    self.shield = shield #: float: Current size of shield
                    self.stocks = stocks #: int: Number of stocks remaining
                    self.last_attack_landed = last_attack_landed #: :py:class:`Attack` | int | None: Last attack that this character landed
                    self.last_hit_by = last_hit_by #: int | None: Port of character that last hit this character
                    self.combo_count = combo_count #: int: Combo count as defined by the game
                    self.state_age = state_age #: float | None: `added(0.2.0)` Number of frames action state has been active. Can have a fractional component for certain actions
                    self.flags = flags #: :py:class:`StateFlags` | None: `added(2.0.0)` State flags
                    self.hit_stun = hit_stun #: float | None: `added(2.0.0)` Number of hitstun frames remaining
                    self.airborne = airborne #: bool | None: `added(2.0.0)` True if character is airborne
                    self.ground = ground #: int | None: `added(2.0.0)` ID of ground character is standing on, if any
                    self.jumps = jumps #: int | None: `added(2.0.0)` Jumps remaining
                    self.l_cancel = l_cancel #: :py:class:`LCancel` | None: `added(2.0.0)` L-cancel status, if any

                @classmethod
                def _parse(cls, stream):
                    (character, state, position_x, position_y, direction, damage, shield, last_attack_landed, combo_count, last_hit_by, stocks) = unpack('BHfffffBBBB', stream)

                    # v0.2.0
                    try: (state_age,) = unpack('f', stream)
                    except EOFError: state_age = None

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
                    except EOFError:
                        (flags, hit_stun, airborne, ground, jumps, l_cancel) = [None] * 6

                    return cls(
                        character=sid.InGameCharacter(character),
                        state=try_enum(sid.ActionState, state),
                        state_age=state_age,
                        position=Position(position_x, position_y),
                        direction=Direction(direction),
                        damage=damage,
                        shield=shield,
                        stocks=stocks,
                        last_attack_landed=try_enum(Attack, last_attack_landed) if last_attack_landed else None,
                        last_hit_by=last_hit_by if last_hit_by < 4 else None,
                        combo_count=combo_count,
                        flags=flags,
                        hit_stun=hit_stun,
                        airborne=airborne,
                        ground=ground,
                        jumps=jumps,
                        l_cancel=l_cancel)


    class Item(Base):
        """An active item (includes projectiles)."""

        __slots__ = 'type', 'state', 'direction', 'velocity', 'position', 'damage', 'timer', 'spawn_id'

        type: sid.Item
        state: int
        direction: "Direction"
        velocity: "Velocity"
        position: "Position"
        damage: int
        timer: int
        spawn_id: int

        def __init__(self, type: sid.Item, state: int, direction: "Direction", velocity: "Velocity", position: "Position", damage: int, timer: int, spawn_id: int):
            self.type = type #: :py:class:`slippi.id.Item`: Item type
            self.state = state #: int: Item's action state
            self.direction = direction #: :py:class:`Direction`: Direction item is facing
            self.velocity = velocity #: :py:class:`Velocity`: Item's velocity
            self.position = position #: :py:class:`Position`: Item's position
            self.damage = damage #: int: Amount of damage item has taken
            self.timer = timer #: int: Frames remaining until item expires
            self.spawn_id = spawn_id #: int: Unique ID per item spawned (0, 1, 2, ...)

        @classmethod
        def _parse(cls, stream):
            (type, state, direction, x_vel, y_vel, x_pos, y_pos, damage, timer, spawn_id) = unpack('HB5fHfI', stream)
            return cls(
                type=try_enum(sid.Item, type),
                state=state,
                direction=Direction(direction),
                velocity=Velocity(x_vel, y_vel),
                position=Position(x_pos, y_pos),
                damage=damage,
                timer=timer,
                spawn_id=spawn_id)

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.type == other.type and self.state == other.state and self.direction == other.direction and self.velocity == other.velocity and self.position == other.position and self.damage == other.damage and self.timer == other.timer and self.spawn_id == other.spawn_id


    class Start(Base):
        """Start-of-frame data."""

        __slots__ = 'random_seed'

        random_seed: int

        def __init__(self, random_seed: int):
            self.random_seed = random_seed

        @classmethod
        def _parse(cls, stream):
            (random_seed,) = unpack('I', stream)
            random_seed = random_seed #: int: The random seed at the start of the frame
            return cls(random_seed)

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.random_seed == other.random_seed


    class End(Base):
        """End-of-frame data."""

        def __init__(self):
            pass

        @classmethod
        def _parse(cls, stream):
            return cls()

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            return True


    class Event(Base):
        """Temporary wrapper used while parsing frame data."""

        __slots__ = 'id', 'type', 'data'

        def __init__(self, id, type, data):
            self.id = id
            self.type = type
            self.data = data


        class Id(Base):
            __slots__ = 'frame'

            def __init__(self, stream):
                (self.frame,) = unpack('i', stream)


        class PortId(Id):
            __slots__ = 'port', 'is_follower'

            def __init__(self, stream):
                (self.frame, self.port, self.is_follower) = unpack('iB?', stream)


        class Type(Enum):
            START = 'start'
            END = 'end'
            PRE = 'pre'
            POST = 'post'
            ITEM = 'item'


class Position(Base):
    __slots__ = 'x', 'y'

    x: float
    y: float

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return '(%.2f, %.2f)' % (self.x, self.y)


class Velocity(Base):
    __slots__ = 'x', 'y'

    x: float
    y: float

    def __init__(self, x: float, y: float):
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
    NON_STALING = 1
    JAB_1 = 2
    JAB_2 = 3
    JAB_3 = 4
    RAPID_JABS = 5
    DASH_ATTACK = 6
    SIDE_TILT = 7
    UP_TILT = 8
    DOWN_TILT = 9
    SIDE_SMASH = 10
    UP_SMASH = 11
    DOWN_SMASH = 12
    NAIR = 13
    FAIR = 14
    BAIR = 15
    UAIR = 16
    DAIR = 17
    NEUTRAL_SPECIAL = 18
    SIDE_SPECIAL = 19
    UP_SPECIAL = 20
    DOWN_SPECIAL = 21
    KIRBY_HAT_MARIO_NEUTRAL_SPECIAL = 22
    KIRBY_HAT_FOX_NEUTRAL_SPECIAL = 23
    KIRBY_HAT_CFALCON_NEUTRAL_SPECIAL = 24
    KIRBY_HAT_DKNEUTRAL_SPECIAL = 25
    KIRBY_HAT_BOWSER_NEUTRAL_SPECIAL = 26
    KIRBY_HAT_LINK_NEUTRAL_SPECIAL = 27
    KIRBY_HAT_SHEIK_NEUTRAL_SPECIAL = 28
    KIRBY_HAT_NESS_NEUTRAL_SPECIAL = 29
    KIRBY_HAT_PEACH_NEUTRAL_SPECIAL = 30
    KIRBY_HAT_ICE_CLIMBER_NEUTRAL_SPECIAL = 31
    KIRBY_HAT_PIKACHU_NEUTRAL_SPECIAL = 32
    KIRBY_HAT_SAMUS_NEUTRAL_SPECIAL = 33
    KIRBY_HAT_YOSHI_NEUTRAL_SPECIAL = 34
    KIRBY_HAT_JIGGLYPUFF_NEUTRAL_SPECIAL = 35
    KIRBY_HAT_MEWTWO_NEUTRAL_SPECIAL = 36
    KIRBY_HAT_LUIGI_NEUTRAL_SPECIAL = 37
    KIRBY_HAT_MARTH_NEUTRAL_SPECIAL = 38
    KIRBY_HAT_ZELDA_NEUTRAL_SPECIAL = 39
    KIRBY_HAT_YOUNG_LINK_NEUTRAL_SPECIAL = 40
    KIRBY_HAT_DOC_NEUTRAL_SPECIAL = 41
    KIRBY_HAT_FALCO_NEUTRAL_SPECIAL = 42
    KIRBY_HAT_PICHU_NEUTRAL_SPECIAL = 43
    KIRBY_HAT_GAME_AND_WATCH_NEUTRAL_SPECIAL = 44
    KIRBY_HAT_GANON_NEUTRAL_SPECIAL = 45
    KIRBY_HAT_ROY_NEUTRAL_SPECIAL = 46
    GET_UP_ATTACK_FROM_BACK = 50
    GET_UP_ATTACK_FROM_FRONT = 51
    PUMMEL = 52
    FORWARD_THROW = 53
    BACK_THROW = 54
    UP_THROW = 55
    DOWN_THROW = 56
    CARGO_FORWARD_THROW = 57
    CARGO_BACK_THROW = 58
    CARGO_UP_THROW = 59
    CARGO_DOWN_THROW = 60
    LEDGE_GET_UP_ATTACK_100 = 61
    LEDGE_GET_UP_ATTACK = 62
    BEAM_SWORD_JAB = 63
    BEAM_SWORD_TILT_SWING = 64
    BEAM_SWORD_SMASH_SWING = 65
    BEAM_SWORD_DASH_SWING = 66
    HOME_RUN_BAT_JAB = 67
    HOME_RUN_BAT_TILT_SWING = 68
    HOME_RUN_BAT_SMASH_SWING = 69
    HOME_RUN_BAT_DASH_SWING = 70
    PARASOL_JAB = 71
    PARASOL_TILT_SWING = 72
    PARASOL_SMASH_SWING = 73
    PARASOL_DASH_SWING = 74
    FAN_JAB = 75
    FAN_TILT_SWING = 76
    FAN_SMASH_SWING = 77
    FAN_DASH_SWING = 78
    STAR_ROD_JAB = 79
    STAR_ROD_TILT_SWING = 80
    STAR_ROD_SMASH_SWING = 81
    STAR_ROD_DASH_SWING = 82
    LIPS_STICK_JAB = 83
    LIPS_STICK_TILT_SWING = 84
    LIPS_STICK_SMASH_SWING = 85
    LIPS_STICK_DASH_SWING = 86
    OPEN_PARASOL = 87
    RAY_GUN_SHOOT = 88
    FIRE_FLOWER_SHOOT = 89
    SCREW_ATTACK = 90
    SUPER_SCOPE_RAPID = 91
    SUPER_SCOPE_CHARGED = 92
    HAMMER = 93


class Triggers(Base):
    __slots__ = 'logical', 'physical'

    logical: float
    physical: "Physical"

    def __init__(self, logical: float, physical_x: float, physical_y: float):
        self.logical = logical #: float: Processed analog trigger position
        self.physical = self.Physical(physical_x, physical_y) #: :py:class:`Physical`: physical analog trigger positions (useful for APM)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return other.logical == self.logical and other.physical == self.physical


    class Physical(Base):
        __slots__ = 'l', 'r'

        l: float
        r: float

        def __init__(self, l: float, r: float):
            self.l = l
            self.r = r

        def __eq__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented
            # Should we add an epsilon to these comparisons? When are people going to be comparing trigger states for equality, other than in our tests?
            return other.l == self.l and other.r == self.r


class Buttons(Base):
    __slots__ = 'logical', 'physical'

    logical: "Logical"
    physical: "Physical"

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
