import unittest

from test_floor import go
from floor import FloorDungeon
import test_mechanics


class GrassTests(unittest.TestCase):
    def test_ground_fire_spreads_with_warning_and_expires_after_two_steps(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['burn']
        game.terrain = [dict(x=4, y=y, kind='high_grass') for y in range(2, 6)]
        game.terrain.append(dict(x=5, y=4, kind='water'))
        game.update_visibility()
        self.assertIn('下一拍仍有地火', game.preview_details('wave', 'right')['events'])
        go(game, 'wave', 'right')
        self.assertEqual(game.state()['fireCells'], [[4, 5]])
        game = FloorDungeon.restore(game.dump())
        with self.assertRaisesRegex(ValueError, '正在燃烧'):
            game.path_to([4, 5])
        go(game, 'move', 'right')
        self.assertEqual(game.player['hp'], 19)
        self.assertEqual(game.state()['fireCells'], [[4, 4]])
        go(game, 'guard')
        self.assertEqual(game.state()['fireCells'], [[4, 3]])
        go(game, 'guard')
        self.assertFalse(game.state()['fireCells'])
        self.assertEqual(game.tile_at([4, 2])['kind'], 'high_grass')
        self.assertEqual(game.tile_at([5, 4])['kind'], 'water')

    def test_frost_smoke_prevents_ground_fire_spreading_into_its_area(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.upgrades = ['burn']
        game.inventory = ['frost_smoke']
        game.terrain = [dict(x=4, y=y, kind='high_grass') for y in (4, 5)]
        go(game, 'wave', 'right')
        go(game, 'item', [4, 4], 'frost_smoke')
        self.assertFalse(game.state()['fireCells'])
        self.assertEqual(game.tile_at([4, 4])['kind'], 'high_grass')

    def test_enemy_takes_ground_fire_when_held_in_place(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['burn']
        game.terrain = [dict(x=4, y=5, kind='high_grass')]
        go(game, 'wave', 'right')
        enemy = fixture.enemy(game, 4, 5, hp=3)
        go(game, 'guard')
        self.assertEqual(enemy['hp'], 2)
        self.assertFalse(game.state()['fireCells'])

    def test_cover_is_passable_and_player_wave_clears_it(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        grass = dict(x=4, y=5, kind='high_grass')
        game.terrain = [grass]
        enemy = fixture.enemy(game, 5, 5, hp=8)
        self.assertTrue(game.walkable([4, 5]))
        self.assertFalse(game.has_sight([3, 5], [5, 5]))
        self.assertFalse(game.state()['enemies'])
        before = game.dump()
        self.assertIn('高草被压倒或打碎', game.preview_details('wave', 'right')['events'])
        self.assertEqual(game.dump(), before)
        go(game, 'wave', 'right')
        self.assertEqual(grass['kind'], 'grass')
        self.assertEqual(enemy['hp'], 2)
        self.assertTrue(game.has_sight([3, 5], [5, 5]))

    def test_enemy_attack_clears_grass_but_not_behind_closed_door(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        first = dict(x=6, y=5, kind='high_grass')
        behind_door = dict(x=4, y=5, kind='high_grass')
        game.terrain = [first, behind_door]
        game.doors = [[5, 5]]
        game._door_cells = {(5, 5)}
        fixture.enemy(game, 7, 5, energy=1,
                      intent=dict(action='wave', cells=[[6,5],[5,5],[4,5],[3,5]]))
        go(game, 'guard')
        self.assertEqual(first['kind'], 'grass')
        self.assertEqual(behind_door['kind'], 'high_grass')

    def test_both_actors_trample_and_grass_cannot_drop_twice(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.terrain = [dict(x=4, y=5, kind='high_grass'), dict(x=6, y=5, kind='high_grass')]
        fixture.enemy(game, 7, 5, intent=dict(action='move', target=[6,5], cells=[]))
        go(game, 'move', 'right')
        self.assertEqual([tile['kind'] for tile in game.terrain], ['grass', 'grass'])
        features = game.features[:]
        game.flatten_grass([4, 5])
        game.flatten_grass([6, 5])
        self.assertEqual(game.features, features)
