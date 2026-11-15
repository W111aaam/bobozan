import contextlib
import io
import unittest
from random import Random
from unittest.mock import patch

from bobozan import Fighter, Move, choose_ai_move, main, play_game, resolve_round


class CombatTests(unittest.TestCase):
    def test_all_nine_matchups(self):
        # Expected HP loss for player and AI, independently specified per pairing.
        C, W, G = Move.CHARGE, Move.WAVE, Move.GUARD
        damage = {(C, C): (0, 0), (C, W): (1, 0), (C, G): (0, 0),
                  (W, C): (0, 1), (W, W): (1, 1), (W, G): (0, 0),
                  (G, C): (0, 0), (G, W): (0, 0), (G, G): (0, 0)}
        energy = {C: 2, W: 0, G: 1}
        for (a, b), (loss_a, loss_b) in damage.items():
            with self.subTest(player=a, ai=b):
                self.assertEqual(resolve_round(Fighter(3, 1), Fighter(3, 1), a, b),
                                 (Fighter(3 - loss_a, energy[a]), Fighter(3 - loss_b, energy[b])))

    def test_illegal_wave_on_either_side(self):
        for a, b in [(Move.WAVE, Move.CHARGE), (Move.CHARGE, Move.WAVE)]:
            with self.assertRaises(ValueError):
                resolve_round(Fighter(), Fighter(), a, b)

    def test_simultaneous_knockout(self):
        self.assertEqual(resolve_round(Fighter(1, 1), Fighter(1, 1), Move.WAVE, Move.WAVE),
                         (Fighter(0, 0), Fighter(0, 0)))

    def test_ai_never_spends_missing_energy(self):
        rng = Random(42)
        for hp in (1, 2, 3):
            for energy in (0, 1, 10):
                for _ in range(100):
                    self.assertIn(choose_ai_move(Fighter(hp, 0), Fighter(hp, energy), rng),
                                  (Move.CHARGE, Move.GUARD))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def test_help_and_invalid_input_do_not_reroll_ai(self):
        with patch('bobozan.choose_ai_move', return_value=Move.CHARGE) as choose, \
                patch('builtins.input', side_effect=['h', '2', 'bad', 'q']):
            self.assertIsNone(play_game(Random(1)))
        self.assertEqual(choose.call_count, 1)
        self.assertIn('能量不足', self.output.getvalue())

    def test_round_limit(self):
        with patch('bobozan.choose_ai_move', return_value=Move.CHARGE) as choose, \
                patch('builtins.input', return_value='3'):
            self.assertEqual(play_game(Random(1)), '平局')
        self.assertEqual(choose.call_count, 30)

    def test_win_and_loss(self):
        with patch('bobozan.choose_ai_move', return_value=Move.CHARGE), \
                patch('builtins.input', side_effect=['1', '2'] * 3):
            self.assertEqual(play_game(Random(1)), '胜利')
        with patch('bobozan.choose_ai_move', side_effect=[Move.CHARGE, Move.WAVE] * 3), \
                patch('builtins.input', return_value='1'):
            self.assertEqual(play_game(Random(1)), '失败')

    def test_replay_resets_fighters_and_tracks_results(self):
        with patch('bobozan.choose_ai_move', return_value=Move.CHARGE), \
                patch('builtins.input', side_effect=['1', '2'] * 3 + ['y'] + ['1', '2'] * 3 + ['q']):
            main()
        self.assertIn('2 胜 / 0 负 / 0 平', self.output.getvalue())
        self.assertEqual(self.output.getvalue().count('第 1 回合 | 你：3 血 / 0 能量'), 2)

    def test_eof_quits(self):
        with patch('builtins.input', side_effect=EOFError):
            self.assertIsNone(play_game(Random(1)))


if __name__ == '__main__':
    unittest.main()
