import json
from random import Random
import unittest

from enemy_design import ENEMY_DESIGNS
from floor import FloorDungeon
from layout import generate_layout
from test_floor import go


class RegionalEnemyTests(unittest.TestCase):
    def arena(self, x=3, y=5):
        g = FloorDungeon(0)
        g.player.update(x=x, y=y, energy=2)
        g.enemies = []
        g.doors, g.walls, g.terrain, g.features = [], [], [], []
        g._door_cells, g._wall_cells = set(), set()
        g.rooms_data = [dict(id=0, bounds=[0, 0, 10, 10], kind='entry', name='试验场', cleared=True)]
        g.locked = False
        g.update_visibility()
        return g

    def enemy(self, g, kind, x, y, **fields):
        name, _, hp, _ = ENEMY_DESIGNS[kind]
        e = dict(id=len(g.enemies), kind=kind, name=name, home=0, hp=hp, maxHp=hp,
                 x=x, y=y, energy=0, phase=0, last_seen=[g.player['x'], g.player['y']])
        e.update(fields)
        g.enemies.append(e)
        g.plan()
        return e

    def test_regional_rotation_covers_new_enemies_and_keeps_pairs(self):
        seen = set()
        for seed in range(8):
            for depth in range(1, 26):
                layout = generate_layout(seed, depth)
                spawns = layout['spawn']
                seen.update(kind for _, kind, _, _ in spawns)
                self.assertEqual(len({(x, y) for _, _, x, y in spawns}), len(spawns))
                if depth in (14, 19):
                    self.assertEqual([(home, kind) for home, kind, _, _ in spawns if kind == 'twin'],
                                     [(4, 'twin'), (4, 'twin')])
        self.assertTrue((ENEMY_DESIGNS.keys() - {'bonepuppet', 'broodling'}) <= seen)

    def test_population_is_distributed_and_scales_with_floor(self):
        for seed in range(12):
            for depth in (1, 4, 8, 14, 19, 24):
                layout = generate_layout(seed, depth)
                count = len(layout['spawn'])
                self.assertGreaterEqual(count, 4 if depth == 1 else 6)
                self.assertLessEqual(count, 9)
                reinforcements = [entry for entry in layout['spawn'] if
                                  layout['rooms_data'][entry[0]]['kind'] == 'standard']
                self.assertTrue(reinforcements)
                for _, _, x, y in reinforcements:
                    self.assertTrue(all(abs(x-a) + abs(y-b) > 1 for a, b in layout['doors']))

    def test_loot_limits_persist_and_summoned_or_fallen_enemies_do_not_drop(self):
        g = self.arena()
        g.depth = 11
        winners = [ident for ident in range(200)
                   if Random(g.seed + g.depth * 71993 + ident * 1103).randrange(100) < 15]
        first, second, third, fourth, fifth = winners[:5]

        def enemy(ident, kind, eligible=True):
            return dict(id=ident, kind=kind, x=5, y=5, regular_loot=eligible)

        g.finish_side_enemies({}, [enemy(first, 'drainbat'), enemy(second, 'drainbat')])
        self.assertEqual([drop['kind'] for drop in g.features], ['kit'])
        g = FloorDungeon.restore(g.dump())
        g.falls = [dict(id=third)]
        g.finish_side_enemies({}, [enemy(third, 'rushcrab'), enemy(fourth, 'rushcrab', False)])
        self.assertEqual(len(g.features), 1)
        g.falls = []
        g.finish_side_enemies({}, [enemy(fourth, 'rushcrab'), enemy(fifth, 'rushcrab')])
        self.assertEqual([drop['kind'] for drop in g.features], ['kit', 'dew'])
        self.assertEqual(g.enemy_loot_count, 2)

    def test_second_drop_chance_halves_and_survives_reload(self):
        g = self.arena()
        bat = self.enemy(g, 'drainbat', 4, 5, regular_loot=True)
        self.assertIn('掉落概率 18%', g.state()['enemies'][0]['lootHint'])
        g.enemy_loot_count = 1
        g = FloorDungeon.restore(json.loads(json.dumps(g.dump())))
        bat = g.enemies[0]
        self.assertIn('掉落概率 9%', g.state()['enemies'][0]['lootHint'])
        bat['id'] = next(ident for ident in range(200)
                         if 9 <= Random(g.seed + g.depth * 71993 + ident * 1103).randrange(100) < 18)
        self.assertIsNone(g.roll_enemy_loot(bat))
        g.enemy_loot_count = 2
        self.assertIn('已达掉落上限', g.state()['enemies'][0]['lootHint'])

    def test_patrol_stays_in_room_and_yields_to_alert(self):
        g = FloorDungeon(0)
        self.assertFalse(any(e.get('patrol') for e in g.enemies))
        g.depth = 2
        g.enter_room()
        patrol, = (e for e in g.enemies if e.get('patrol'))
        positions = set()
        for _ in range(15):
            cell = (patrol['x'], patrol['y'])
            positions.add(cell)
            self.assertEqual(g.room_at(cell), patrol['home'])
            self.assertFalse(g.has_threat())
            self.assertTrue(all(abs(cell[0] - x) + abs(cell[1] - y) > 1 for x, y in g.doors))
            go(g, 'guard')
        self.assertGreater(len(positions), 1)
        restored = FloorDungeon.restore(json.loads(json.dumps(g.dump())))
        self.assertEqual(restored.enemies, g.enemies)
        patrol = next(e for e in restored.enemies if e.get('patrol'))
        x, y = patrol['x'], patrol['y']
        restored.player.update(x=x + 1, y=y)
        restored.plan()
        self.assertEqual(patrol['intent']['action'], 'notice')
        self.assertTrue(restored.has_threat())

    def test_chasing_enemy_detours_around_known_hazards(self):
        for hazard in (
            dict(kind='fragile', stage=1),
            dict(kind='trap', armed=True, mechanism='dart'),
            None,
        ):
            with self.subTest(hazard=hazard):
                g = self.arena()
                enemy = self.enemy(g, 'drainbat', 5, 5)
                if hazard:
                    g.terrain = [dict(x=4, y=5, **hazard)]
                else:
                    g.ground_fire = [dict(x=4, y=5, spread=0)]
                g.plan()
                self.assertEqual(enemy['intent']['target'], [5, 4])
                if hazard and hazard['kind'] == 'trap':
                    g.terrain[0]['hidden'] = True
                    g.plan()
                    self.assertEqual(enemy['intent']['target'], [4, 5])

    def test_enemy_can_approach_player_on_hazard_without_stepping_onto_it(self):
        g = self.arena()
        g.ground_fire = [dict(x=3, y=5, spread=0)]
        enemy = self.enemy(g, 'drainbat', 5, 5)
        self.assertEqual(enemy['intent']['target'], [4, 5])

    def test_fire_delays_pursuit_until_passage_is_safe(self):
        g = self.arena()
        g.width, g.height = 7, 11
        g._wall_cells = {(x, y) for x in range(g.width) for y in range(g.height) if y != 5}
        g.ground_fire = [dict(x=4, y=5, spread=0)]
        enemy = self.enemy(g, 'drainbat', 5, 5)
        self.assertEqual(enemy['intent']['action'], 'wait')
        go(g, 'guard')
        self.assertEqual(enemy['intent']['target'], [4, 5])

    def test_snake_preview_uses_actual_side_step(self):
        g = self.arena()
        snake = self.enemy(g, 'slipsnake', 5, 5)
        self.assertEqual(snake['intent']['label'], '滑鳞侧闪')
        self.assertEqual(g.preview('wave', 'right'), [])
        go(g, 'wave', 'right')
        self.assertEqual(snake['hp'], 2)
        self.assertNotEqual(snake['y'], 5)

    def test_death_burst_is_delayed_visible_and_survives_reload(self):
        g = self.arena()
        self.enemy(g, 'boneburst', 4, 5, hp=1)
        # Give the lethal shot the opening created by a previous dodge.
        g.enemies[0]['intent'] = dict(action='wait', label='空档', cells=[])
        go(g, 'wave', 'right')
        self.assertEqual(g.player['hp'], 5)
        self.assertIn([3, 5], g.state()['dangerCells'])
        loaded = FloorDungeon.restore(json.loads(json.dumps(g.dump())))
        self.assertEqual(loaded.state()['dangerCells'], g.state()['dangerCells'])
        go(loaded, 'guard')
        self.assertTrue(loaded.counter)
        self.assertEqual(loaded.player['hp'], 5)
        self.assertFalse(loaded.state()['dangerCells'])
        go(g, 'move', 'up')
        self.assertEqual(g.player['hp'], 5)

    def test_split_conserves_remaining_health_and_is_once_only(self):
        g = self.arena()
        parent = self.enemy(g, 'splitcloud', 4, 5)
        go(g, 'wave', 'right')
        child = next(e for e in g.enemies if e is not parent)
        self.assertEqual((parent['hp'], child['hp']), (2, 1))
        self.assertNotEqual(parent['id'], child['id'])
        go(g, 'wave', 'right')
        self.assertEqual(len(g.enemies), 2)

    def test_blocking_bite_prevents_healing(self):
        g = self.arena()
        bat = self.enemy(g, 'drainbat', 4, 5, hp=1)
        go(g, 'guard')
        self.assertEqual((g.player['hp'], bat['hp']), (5, 1))
        go(g, 'charge')
        self.assertEqual((g.player['hp'], bat['hp']), (4, 2))

    def test_drain_requires_unblocked_damage(self):
        for action, direction, hp, energy in (('guard', None, 5, 2), ('reflect', 'right', 5, 1),
                                                ('charge', None, 4, 2)):
            with self.subTest(action=action):
                g = self.arena()
                self.enemy(g, 'nullmage', 5, 5, energy=1)
                go(g, action, direction)
                self.assertEqual((g.player['hp'], g.player['energy']), (hp, energy))

    def test_eye_preserves_original_aim_and_then_recovers(self):
        g = self.arena()
        eye = self.enemy(g, 'siegeeye', 6, 5)
        line = eye['intent']['warning']
        self.assertIn([3, 5], line)
        go(g, 'move', 'up')
        self.assertEqual(eye['intent']['cells'], line)
        go(g, 'guard')
        self.assertEqual(eye['intent']['action'], 'wait')
        self.assertEqual(g.player['hp'], 5)

    def test_leap_uses_shared_collision_and_freeze(self):
        g = self.arena()
        ripper = self.enemy(g, 'leapripper', 6, 5)
        self.assertEqual(ripper['intent']['target'], [4, 5])
        self.assertTrue(ripper['intent']['mob_jump'])
        go(g, 'move', 'right')
        self.assertEqual((g.player['x'], ripper['x']), (3, 6))
        ripper.update(phase=0, frozen=True)
        g.plan()
        self.assertEqual(ripper['intent']['action'], 'wait')
        go(g, 'guard')
        self.assertEqual(ripper['x'], 6)
        ripper['phase'] = 0
        g.plan()
        go(g, 'guard')
        self.assertEqual(ripper['x'], 4)
        self.assertIn([3, 5], ripper['intent']['cells'])
        go(g, 'move', 'up')
        self.assertEqual(g.player['hp'], 5)

    def test_closed_door_blocks_special_movement_and_long_beam(self):
        for kind in ('blinkgolem', 'siegeeye', 'rushcrab'):
            with self.subTest(kind=kind):
                g = self.arena()
                g.doors, g._door_cells = [[5, 5]], {(5, 5)}
                enemy = self.enemy(g, kind, 7, 5)
                self.assertFalse(enemy['intent'].get('mob_jump'))
                self.assertNotIn('warning', enemy['intent'])
                self.assertIn(enemy['intent']['action'], ('move', 'wait'))
                if enemy['intent']['action'] == 'move':
                    self.assertEqual(enemy['intent']['target'], [6, 5])
