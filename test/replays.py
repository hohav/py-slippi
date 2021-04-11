#!/usr/bin/python3

import datetime, glob, os, subprocess, unittest

from slippi import Game, parse
from slippi.id import CSSCharacter, InGameCharacter, Item, Stage
from slippi.log import log
from slippi.metadata import Metadata, Platform, PlayerMetadata, NetplayMetadata
from slippi.event import Buttons, Direction, GameEnd, Frame, Position, Start, Triggers, Velocity, Player, Slippi, \
    SlippiVersion, GameEndMethod, UCF, Physical, Logical, PlayerType, FrameItem
from slippi.parse import ParseEvent

def norm(f):
    return 1 if f > 0.01 else -1 if f < -0.01 else 0


def path(name):
    return os.path.join(os.path.dirname(__file__), 'replays', name + '.slp')


class TestGame(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        self.pkgname: str = "slippi"
        super().__init__(*args, **kwargs)
        my_env = os.environ.copy()
        self.pypath: str = my_env.get("PYTHONPATH", os.getcwd())
        self.mypy_opts: List[str] = ['--ignore-missing-imports']

    def _game(self, name):
        return Game(path(name))

    def _stick_seq(self, game):
        pass

    # not used yet because the recorder currently puts bogus values in triggers.physical
    def _trigger_seq(self, game):
        last_triggers = None
        trigger_seq = []
        for frame in game.frames:
            t = frame.ports[0].leader.pre.triggers
            t = Triggers(norm(t.logical), norm(t.physical.l), norm(t.physical.r))
            if (t.logical or t.physical.l or t.physical.r) and t != last_triggers:
                trigger_seq.append(t)
            last_triggers = t
        return trigger_seq

    def _button_seq(self, game):
        last_buttons = None
        button_seq = []
        for frame in game.frames:
            b = frame.ports[0].leader.pre.buttons
            if (b.logical or b.physical) and b != last_buttons:
                button_seq.append(b)
            last_buttons = b
        return button_seq

    def test_run_mypy_module(self):
        """Run mypy on all module sources"""
        mypy_call: List[str] = ["mypy"] + self.mypy_opts + ["-p", self.pkgname]
        browse_result: int = subprocess.call(mypy_call, env=os.environ, cwd=self.pypath)
        self.assertEqual(browse_result, 0, 'mypy on slippi')

    def test_run_mypy_tests(self):
        """Run mypy on all tests in module under the tests directory"""
        for test_file in glob.iglob(f'{os.getcwd()}/tests/*.py'):
            mypy_call: List[str] = ["mypy"] + self.mypy_opts + [test_file]
            test_result: int = subprocess.call(mypy_call, env=os.environ, cwd=self.pypath)
            self.assertEqual(test_result, 0, f'mypy on test {test_file}')

    def test_slippi_old_version(self):
        game = self._game('v0.1')
        self.assertEqual(game.start.slippi.version, SlippiVersion(0, 1, 0, 0))
        self.assertEqual(game.metadata.duration, None)
        self.assertEqual(game.metadata.players, (None, None, None, None))
        self.assertEqual(game.start.players[0].character, CSSCharacter.FOX)
        self.assertEqual(game.start.players[1].character, CSSCharacter.GANONDORF)

    def test_game(self):
        game = self._game('game')

        self.assertEqual(game.metadata, Metadata._parse({
            'startAt': '2018-06-22T07:52:59Z',
            'lastFrame': 5085,
            'playedOn': 'dolphin',
            'players': {
                '0': {'characters': {InGameCharacter.MARTH: 5209}},
                '1': {'characters': {InGameCharacter.FOX: 5209}}}}))
        self.assertEqual(game.metadata, Metadata(
            date=datetime.datetime(2018, 6, 22, 7, 52, 59, 0, datetime.timezone.utc),
            duration=5209,
            platform=Platform.DOLPHIN,
            players=(
                PlayerMetadata({InGameCharacter.MARTH: 5209}),
                PlayerMetadata({InGameCharacter.FOX: 5209}),
                None, None)))

        self.assertEqual(game.start, Start(
            is_teams=False,
            random_seed=3803194226,
            slippi=Slippi(SlippiVersion(1, 0, 0, 0)),
            stage=Stage.YOSHIS_STORY,
            players=(
                Player(character=CSSCharacter.MARTH, type=PlayerType.HUMAN, stocks=4, costume=3, team=None, ucf=UCF(False, False)),
                Player(character=CSSCharacter.FOX, type=PlayerType.CPU, stocks=4, costume=0, team=None, ucf=UCF(False, False)),
                None, None)))

        self.assertEqual(game.end, GameEnd(GameEndMethod.CONCLUSIVE))

        self.assertEqual(game.metadata.duration, len(game.frames))

    def test_ics(self):
        game = self._game('ics')
        self.assertEqual(game.metadata.players[0].characters, {
            InGameCharacter.NANA: 344,
            InGameCharacter.POPO: 344})
        self.assertEqual(game.start.players[0].character, CSSCharacter.ICE_CLIMBERS)
        self.assertIsNotNone(game.frames[0].ports[0].follower)

    def test_ucf(self):
        self.assertEqual(self._game('shield_drop').start.players[0].ucf, UCF(dash_back=False, shield_drop=True))
        self.assertEqual(self._game('dash_back').start.players[0].ucf, UCF(dash_back=True, shield_drop=False))

    def test_buttons_lrzs(self):
        game = self._game('buttons_lrzs')
        self.assertEqual(self._button_seq(game), [
            Buttons(Logical.TRIGGER_ANALOG, Physical.NONE),
            Buttons(Logical.TRIGGER_ANALOG|Logical.L, Physical.L),
            Buttons(Logical.TRIGGER_ANALOG, Physical.NONE),
            Buttons(Logical.TRIGGER_ANALOG|Logical.R, Physical.R),
            Buttons(Logical.TRIGGER_ANALOG|Logical.A|Logical.Z, Physical.Z),
            Buttons(Logical.START, Physical.START)])

    def test_buttons_abxy(self):
        game = self._game('buttons_abxy')
        self.assertEqual(self._button_seq(game), [
            Buttons(Logical.A, Physical.A),
            Buttons(Logical.B, Physical.B),
            Buttons(Logical.X, Physical.X),
            Buttons(Logical.Y, Physical.Y)])

    def test_dpad_udlr(self):
        game = self._game('dpad_udlr')
        self.assertEqual(self._button_seq(game), [
            Buttons(Logical.DPAD_UP, Physical.DPAD_UP),
            Buttons(Logical.DPAD_DOWN, Physical.DPAD_DOWN),
            Buttons(Logical.DPAD_LEFT, Physical.DPAD_LEFT),
            Buttons(Logical.DPAD_RIGHT, Physical.DPAD_RIGHT)])

    def test_cstick_udlr(self):
        game = self._game('cstick_udlr')
        self.assertEqual(self._button_seq(game), [
            Buttons(Logical.CSTICK_UP, Physical.NONE),
            Buttons(Logical.CSTICK_DOWN, Physical.NONE),
            Buttons(Logical.CSTICK_LEFT, Physical.NONE),
            Buttons(Logical.CSTICK_RIGHT, Physical.NONE)])

    def test_joystick_udlr(self):
        game = self._game('joystick_udlr')
        self.assertEqual(self._button_seq(game), [
            Buttons(Logical.JOYSTICK_UP, Physical.NONE),
            Buttons(Logical.JOYSTICK_DOWN, Physical.NONE),
            Buttons(Logical.JOYSTICK_LEFT, Physical.NONE),
            Buttons(Logical.JOYSTICK_RIGHT, Physical.NONE)])

    def test_nintendont(self):
        game = self._game('nintendont')
        self.assertEqual(game.metadata.platform, Platform.NINTENDONT)

    def test_netplay_name(self):
        game = self._game('netplay')
        players = game.metadata.players
        self.assertEqual(players[0].netplay, NetplayMetadata(code='ABCD#123', name='abcdefghijk'))
        self.assertEqual(players[1].netplay, NetplayMetadata(code='XX#000', name='nobody'))

    def test_console_name(self):
        game = self._game('console_name')
        self.assertEqual(game.metadata.console_name, 'Station 1')

    def test_metadata_json(self):
        game = self._game('game')
        self.assertEqual(game.metadata_raw, {
            'lastFrame': 5085,
            'playedOn': 'dolphin',
            'players': {
                '0': {'characters': {'18': 5209}},
                '1': {'characters': {'1': 5209}}},
            'startAt': '2018-06-22T07:52:59Z'})

    def test_v2(self):
        game = self._game('v2.0')
        self.assertEqual(game.start.slippi.version, SlippiVersion(2, 0, 1))

    def test_unknown_event(self):
        with self.assertLogs(log, 'INFO') as log_context:
            game = self._game('unknown_event')
        self.assertEqual(log_context.output, ['INFO:root:ignoring unknown event type: 0xff'])

    def test_items(self):
        game = self._game('items')
        items = {}
        for f in game.frames:
            for i in f.items:
                if not i.spawn_id in items:
                    items[i.spawn_id] = i
        self.assertEqual(items, {
            0: FrameItem(
                damage=0,
                direction=Direction.RIGHT,
                position=Position(-62.7096061706543, -1.4932749271392822),
                spawn_id=0,
                state=0,
                timer=140.0,
                type=Item.PEACH_TURNIP,
                velocity=Velocity(0.0, 0.0)),
            1: FrameItem(
                damage=0,
                direction=Direction.LEFT,
                position=Position(20.395559310913086, -1.4932749271392822),
                spawn_id=1,
                state=0,
                timer=140.0,
                type=Item.PEACH_TURNIP,
                velocity=Velocity(0.0, 0.0)),
            2: FrameItem(
                damage=0,
                direction=Direction.RIGHT,
                position=Position(-3.982539176940918, -1.4932749271392822),
                spawn_id=2,
                state=0,
                timer=140.0,
                type=Item.PEACH_TURNIP,
                velocity=Velocity(0.0, 0.0))})


class TestParse(unittest.TestCase):
    def test_parse(self):
        metadata = None
        def set_metadata(x):
            nonlocal metadata
            metadata = x
        parse(path('game'), {ParseEvent.METADATA: set_metadata})
        self.assertEqual(metadata.duration, 5209)


if __name__ == '__main__':
    unittest.main()
