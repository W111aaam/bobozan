import unittest

from floor import FloorDungeon
from test_floor import go
import test_mechanics


class WaveRelicTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_mechanics.ExpeditionMechanicsTests()
        self.game = self.fixture.arena()

    def test_blink_requires_pierce_to_roll(self):
        game = FloorDungeon(0)
        game.upgrades = [key for key in game.upgrade_catalog if key not in ('blink','pierce')]
        game.make_choices(3)
        self.assertNotIn('blink', [c['id'] for c in game.choices])
        game.upgrades.append('pierce')
        game.make_choices(3)
        self.assertIn('blink', [c['id'] for c in game.choices])
        go(game, 'choose', choice='blink')
        self.assertIn('blink', game.upgrades)

    def test_double_passes_defeated_enemy_and_parallel_hits_side_lane(self):
        game = self.game
        game.upgrades = ['double', 'parallel', 'burn']
        self.fixture.enemy(game, 4, 5, hp=1)
        second = self.fixture.enemy(game, 6, 5, hp=3)
        side = self.fixture.enemy(game, 5, 6, hp=3)
        go(game, 'wave', 'right')
        self.assertEqual(game.player['energy'], 2)
        self.assertEqual((second['hp'], side['hp']), (2, 2))
        self.assertNotIn('burning', second)
        self.assertNotIn('burning', side)

    def test_impact_pushes_enemy_into_fragile_floor(self):
        game = self.game
        game.upgrades = ['impact']
        game.terrain = [dict(x=6, y=5, kind='fragile', stage=1)]
        enemy = self.fixture.enemy(game, 5, 5, hp=4)
        preview = game.preview_details('wave', 'right')
        self.assertIn('ram被推入深渊', preview['events'])
        go(game, 'wave', 'right')
        self.assertNotIn(enemy, game.enemies)
        self.assertEqual(game.tile_at([6, 5])['stage'], 2)

    def test_burn_ticks_for_two_later_actions(self):
        game = self.game
        game.upgrades = ['burn']
        enemy = self.fixture.enemy(game, 6, 5, hp=5)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['burning']), (4, 2))
        go(game, 'guard')
        self.assertEqual((enemy['hp'], enemy['burning']), (3, 1))
        go(game, 'guard')
        self.assertEqual((enemy['hp'], enemy['burning']), (2, 0))

    def test_shallow_water_extinguishes_existing_and_new_burns(self):
        game = self.game
        game.upgrades = ['burn', 'impact']
        enemy = self.fixture.enemy(game, 5, 5, hp=5)
        game.terrain = [dict(x=6, y=5, kind='water')]
        go(game, 'wave', 'right')
        self.assertEqual((enemy['x'], enemy['hp']), (6, 4))
        self.assertFalse(enemy.get('burning'))

        enemy['burning'] = 2
        enemy['intent'] = dict(action='wait', cells=[], label='休整')
        go(game, 'guard')
        self.assertEqual(enemy['hp'], 4)
        self.assertFalse(enemy.get('burning'))

    def test_freeze_cancels_one_movement_after_two_hits(self):
        game = self.game
        game.upgrades = ['freeze']
        enemy = self.fixture.enemy(game, 6, 5, hp=5, last_seen=[3, 5])
        go(game, 'wave', 'right')
        self.assertEqual(enemy['frost_stacks'], 1)
        go(game, 'wave', 'right')
        self.assertEqual(enemy['frost_stacks'], 0)
        self.assertEqual(enemy['intent']['action'], 'wait')
        before = (enemy['x'], enemy['y'])
        go(game, 'guard')
        self.assertEqual((enemy['x'], enemy['y']), before)
        self.assertEqual(enemy['intent']['action'], 'move')

    def test_preview_reports_visible_damage_and_reflection_without_leaking_hidden_sources(self):
        game = self.game
        self.fixture.enemy(game, 5, 5, intent=dict(action='wave', cells=[[4, 5], [3, 5]]))
        self.fixture.enemy(game, 12, 5, intent=dict(action='area', cells=[[3, 5]], damage=2))
        before = game.dump()
        wave = game.preview_details('wave', 'right')
        self.assertEqual(wave['received'], [dict(damage=1, name='ram')])
        self.assertEqual(wave['reflected'], 0)
        defense = game.preview_details('reflect', 'right')
        self.assertEqual(defense['received'], [])
        self.assertEqual(defense['reflected'], 1)
        self.assertEqual(game.dump(), before)

    def test_blink_lands_past_enemy_and_resolves_attack_at_destination(self):
        game = self.game
        game.upgrades = ['pierce', 'blink']
        self.fixture.enemy(game, 5, 5, hp=3, intent=dict(action='area', cells=[[7, 5]], damage=2))
        before = game.dump()
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['landing'], [7, 5])
        self.assertEqual(preview['received'], [dict(damage=2, name='ram')])
        self.assertEqual(game.dump(), before)
        go(game, 'wave', 'right')
        self.assertEqual((game.player['x'], game.player['y'], game.player['hp']), (7, 5, 3))
