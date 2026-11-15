import unittest
from unittest.mock import patch

from bobozan import Fighter, Move
from server import Match


class MatchTests(unittest.TestCase):
    def test_hidden_ai_and_invalid_action_preserve_state(self):
        game = Match()
        before = game.state()
        self.assertNotIn('ai_move', before)
        with self.assertRaises(ValueError):
            game.play('波', game.version)
        self.assertEqual(before, game.state())

    def test_duplicate_request_cannot_advance_round(self):
        game = Match()
        version = game.version
        game.play('攒', version)
        with self.assertRaises(ValueError):
            game.play('攒', version)
        self.assertEqual(game.turn, 2)

    def test_end_and_replay(self):
        game = Match()
        game.player, game.ai = Fighter(1, 1), Fighter(1, 1)
        game.ai_move = Move.WAVE
        game.play('波', game.version)
        self.assertEqual(game.result, '平局')
        with self.assertRaises(ValueError):
            game.play('攒', game.version)
        self.assertEqual(game.scores['平局'], 1)
        game.reset()
        self.assertEqual(game.player, Fighter())
        self.assertEqual(game.turn, 1)
        self.assertIsNone(game.result)
        self.assertEqual(game.scores['平局'], 1)

    def test_round_limit(self):
        with patch('server.choose_ai_move', return_value=Move.CHARGE):
            game = Match()
            for _ in range(30):
                game.play('防', game.version)
        self.assertEqual(game.result, '平局')
        self.assertEqual(game.turn, 30)


if __name__ == '__main__':
    unittest.main()
