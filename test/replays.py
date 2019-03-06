#!/usr/bin/python3

import datetime, os, unittest

from slippi import Game
from slippi.id import InGameCharacter, CSSCharacter, Stage
from slippi.event import Start, End, Frame, Buttons, Triggers, Position


BPhys = Buttons.Physical
BLog = Buttons.Logical


def norm(f):
    return 1 if f > 0.01 else -1 if f < -0.01 else 0


class TestGame(unittest.TestCase):
    def _game(self, name):
        return Game(os.path.join(os.path.dirname(__file__), 'replays', name+'.slp'))

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

    def test_slippi_old_version(self):
        game = self._game('v0.1')
        self.assertEqual(game.start.slippi.version, Start.Slippi.Version(0,1,0,0))
        self.assertEqual(game.metadata.duration, None)
        self.assertEqual(game.metadata.players, (None, None, None, None))
        self.assertEqual(game.start.players[0].character, CSSCharacter.FOX)
        self.assertEqual(game.start.players[1].character, CSSCharacter.GANONDORF)

    def test_game(self):
        game = self._game('game')

        self.assertEqual(game.metadata, Game.Metadata._parse({
            'startAt': '2018-06-22T07:52:59Z',
            'lastFrame': 5085,
            'playedOn': 'dolphin',
            'players': {
                '0': {'characters': {InGameCharacter.MARTH: 5209}},
                '1': {'characters': {InGameCharacter.FOX: 5209}}}}))
        self.assertEqual(game.metadata, Game.Metadata(
            date=datetime.datetime(2018, 6, 22, 7, 52, 59, 0, datetime.timezone.utc),
            duration=5209,
            platform=Game.Metadata.Platform.DOLPHIN,
            players=(
                Game.Metadata.Player({InGameCharacter.MARTH: 5209}),
                Game.Metadata.Player({InGameCharacter.FOX: 5209}),
                None, None)))

        self.assertEqual(game.start, Start(
            is_teams=False,
            random_seed=3803194226,
            slippi=Start.Slippi(Start.Slippi.Version(1,0,0,0)),
            stage=Stage.YOSHIS_STORY,
            players=(
                Start.Player(character=CSSCharacter.MARTH, type=Start.Player.Type.HUMAN, stocks=4, costume=3, team=None, ucf=Start.Player.UCF(False, False)),
                Start.Player(character=CSSCharacter.FOX, type=Start.Player.Type.CPU, stocks=4, costume=0, team=None, ucf=Start.Player.UCF(False, False)),
                None, None),
            is_pal=False))

        self.assertEqual(game.end, End(End.Method.CONCLUSIVE))

        self.assertEqual(game.metadata.duration, len(game.frames))

    def test_ics(self):
        game = self._game('ics')
        self.assertEqual(game.metadata.players[0].characters, {
            InGameCharacter.NANA: 344,
            InGameCharacter.POPO: 344})
        self.assertEqual(game.start.players[0].character, CSSCharacter.ICE_CLIMBERS)
        self.assertIsNotNone(game.frames[0].ports[0].follower)

    def test_ucf(self):
        self.assertEqual(self._game('shield_drop').start.players[0].ucf, Start.Player.UCF(dash_back=False, shield_drop=True))
        self.assertEqual(self._game('dash_back').start.players[0].ucf, Start.Player.UCF(dash_back=True, shield_drop=False))

    def test_buttons_lrzs(self):
        game = self._game('buttons-lrzs')
        self.assertEqual(self._button_seq(game), [
            Buttons(BLog.TRIGGER_ANALOG, BPhys.NONE),
            Buttons(BLog.TRIGGER_ANALOG|BLog.L, BPhys.L),
            Buttons(BLog.TRIGGER_ANALOG, BPhys.NONE),
            Buttons(BLog.TRIGGER_ANALOG|BLog.R, BPhys.R),
            Buttons(BLog.TRIGGER_ANALOG|BLog.A|BLog.Z, BPhys.Z),
            Buttons(BLog.START, BPhys.START)])

    def test_buttons_abxy(self):
        game = self._game('buttons-abxy')
        self.assertEqual(self._button_seq(game), [
            Buttons(BLog.A, BPhys.A),
            Buttons(BLog.B, BPhys.B),
            Buttons(BLog.X, BPhys.X),
            Buttons(BLog.Y, BPhys.Y)])

    def test_dpad_udlr(self):
        game = self._game('dpad-udlr')
        self.assertEqual(self._button_seq(game), [
            Buttons(BLog.DPAD_UP, BPhys.DPAD_UP),
            Buttons(BLog.DPAD_DOWN, BPhys.DPAD_DOWN),
            Buttons(BLog.DPAD_LEFT, BPhys.DPAD_LEFT),
            Buttons(BLog.DPAD_RIGHT, BPhys.DPAD_RIGHT)])

    def test_cstick_udlr(self):
        game = self._game('cstick-udlr')
        self.assertEqual(self._button_seq(game), [
            Buttons(BLog.CSTICK_UP, BPhys.NONE),
            Buttons(BLog.CSTICK_DOWN, BPhys.NONE),
            Buttons(BLog.CSTICK_LEFT, BPhys.NONE),
            Buttons(BLog.CSTICK_RIGHT, BPhys.NONE)])

    def test_joystick_udlr(self):
        game = self._game('joystick-udlr')
        self.assertEqual(self._button_seq(game), [
            Buttons(BLog.JOYSTICK_UP, BPhys.NONE),
            Buttons(BLog.JOYSTICK_DOWN, BPhys.NONE),
            Buttons(BLog.JOYSTICK_LEFT, BPhys.NONE),
            Buttons(BLog.JOYSTICK_RIGHT, BPhys.NONE)])


if __name__ == '__main__':
    unittest.main()
