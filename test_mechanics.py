import json
import unittest

from floor import FloorDungeon
from test_floor import go, route, place, feature, position
from dungeon import DIRS


class ExpeditionMechanicsTests(unittest.TestCase):
    def arena(self, x=3, y=5):
        game = FloorDungeon(0)
        game.player.update(x=x, y=y, energy=3)
        game.enemies = []
        game.doors = []
        game._door_cells = set()
        game.walls = []
        game._wall_cells = set()
        game.features = []
        game.terrain = [
            dict(x=16, y=6, kind='mirror', slash='/', rotating=True),
            dict(x=6, y=17, kind='fragile', stage=0),
        ]
        for room in game.rooms_data:
            room['cleared'] = True
        game.update_visibility()
        return game

    def enemy(self, game, x, y, kind='ram', hp=3, **fields):
        enemy = dict(id=len(game.enemies), x=x, y=y, kind=kind, name=kind,
                     home=1, energy=0, hp=hp, phase=0, intent=dict(action='wait', cells=[]))
        enemy.update(fields)
        game.enemies.append(enemy)
        game.update_visibility()
        return enemy

    def test_fan_hits_multiple_and_power_shortens_range(self):
        game = self.arena()
        near = self.enemy(game, 4, 5)
        flank = self.enemy(game, 5, 4)
        go(game, 'equip', choice='fan')
        for enemy in game.enemies:
            enemy['intent'] = dict(action='wait', cells=[])
        go(game, 'wave', 'right')
        self.assertEqual((near['hp'], flank['hp']), (2, 2))
        game.mode = 'power'
        game.player['energy'] = 2
        for enemy in game.enemies:
            enemy['intent'] = dict(action='wait', cells=[])
        go(game, 'wave', 'right')
        self.assertEqual((near['hp'], flank['hp']), (0, 2))

    def test_return_uses_original_path_after_move_and_reload(self):
        game = self.arena()
        game.weapon = 'return'
        target = self.enemy(game, 5, 5)
        go(game, 'wave', 'right')
        self.assertEqual(target['hp'], 2)
        self.assertEqual(game.returning[0]['cells'], [[5, 5], [4, 5]])
        game = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        game.enemies[0]['intent'] = dict(action='wait', cells=[])
        go(game, 'move', 'up')
        self.assertEqual(game.enemies[0]['hp'], 1)
        self.assertFalse(game.returning)

    def test_reflection_spends_energy_and_redirects_wave(self):
        game = self.arena()
        shooter = self.enemy(game, 5, 5, energy=1)
        shooter['intent'] = dict(action='wave', cells=[[4, 5], [3, 5]], direction='left')
        before = game.dump()
        self.assertEqual(game.preview('reflect', 'right'), [{'name': 'ram', 'damage': 1}])
        self.assertEqual(game.dump(), before)
        go(game, 'reflect', 'right')
        self.assertEqual((game.player['energy'], game.player['hp'], shooter['hp']), (2, 5, 2))
        game.player['energy'] = 0
        with self.assertRaises(ValueError):
            go(game, 'reflect', 'right')

    def test_mirror_turns_projectile_then_rotates_and_persists(self):
        game = self.arena(14, 6)
        target = self.enemy(game, 16, 4)
        self.assertEqual(game.trace([14, 6], 'right'), [[15, 6], [16, 6], [16, 5], [16, 4]])
        go(game, 'wave', 'right')
        self.assertEqual(target['hp'], 2)
        game = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        self.assertEqual(game.tile_at([16, 6])['slash'], chr(92))
        self.assertEqual(game.trace([14, 6], 'right')[-1], [16, 8])

    def test_floor_collapses_on_second_entry_for_either_actor(self):
        game = self.arena(5, 17)
        go(game, 'move', 'right')
        self.assertEqual(game.tile_at([6, 17])['stage'], 1)
        go(game, 'guard')
        self.assertEqual(game.player['hp'], 5)
        go(game, 'move', 'left')
        enemy = self.enemy(game, 7, 17)
        enemy['intent'] = dict(action='move', target=[6, 17], cells=[])
        go(game, 'guard')
        self.assertFalse(game.enemies)
        self.assertEqual(game.state()['falls'][0]['cell'], [6, 17])
        go(game, 'move', 'right')
        self.assertEqual(game.result, 'defeat')
        self.assertEqual(game.state()['falls'][0]['id'], 'hero')

    def test_lance_and_guardian_intercept(self):
        game = self.arena()
        game.weapon = 'lance'
        ally = self.enemy(game, 4, 5)
        second = self.enemy(game, 5, 5)
        escort = self.enemy(game, 4, 4, kind='escort')
        game.counter = True
        go(game, 'wave', 'right')
        self.assertEqual((ally['hp'], second['hp'], escort['hp']), (3, 1, 2))

    def test_twin_reacts_to_partner_damage(self):
        game = self.arena()
        twin = self.enemy(game, 5, 4, kind='twin', pair='pair')
        self.enemy(game, 4, 5, kind='twin', pair='pair')
        go(game, 'wave', 'right')
        self.assertTrue(twin['resonance'])
        game.player.update(x=5, y=6)
        game.update_visibility()
        game.plan()
        self.assertEqual(twin['intent']['weapon'], 'fan')

    def test_boss_sweep_locks_its_pattern_and_allows_two_step_escape(self):
        game = FloorDungeon(0)
        game.depth = 5
        game.enter_room()
        boss, = game.enemies
        x, y = position(boss)
        place(game, (x, y + 2))
        boss.update(phase=2, hp=boss['maxHp'] // 2, last_seen=list(position(game.player)))
        game.plan()
        warning = boss['intent']['warning']
        self.assertEqual(len(warning), 5)
        self.assertIn([x + 1, y + 2], warning)
        self.assertEqual(game.state()['dangerCells'], [])
        go(game, 'move', 'right')
        self.assertEqual(boss['intent']['cells'], warning)
        self.assertEqual(boss['intent']['damage'], 3)
        self.assertIn(list(position(game.player)), game.state()['dangerCells'])

        restored = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        hp = restored.player['hp']
        go(restored, 'guard')
        self.assertEqual(restored.player['hp'], hp - 2)

        hp = game.player['hp']
        go(game, 'move', 'down')
        self.assertEqual(game.player['hp'], hp)
        self.assertEqual(boss['intent']['action'], 'wait')

    def test_boss_sweep_does_not_reach_through_closed_door(self):
        game = self.arena(x=8, y=5)
        enemy = self.enemy(game, 10, 5, kind='boss', hp=9, maxHp=9, phase=2,
                           last_seen=[8, 5])
        game.doors = [[7, 5]]
        game._door_cells = {(7, 5)}
        game.plan()
        self.assertEqual(enemy['intent']['warning'], [[8, 5], [9, 5]])

    def test_breaker_opens_alcove_and_mirror_boss_copies_loadout(self):
        game = FloorDungeon(0)
        game.depth = 15
        game.enter_room()
        boss = next(e for e in game.enemies if e['kind'] == 'breaker')
        wall = position(next(t for t in game.terrain if t['kind'] == 'rubble'))
        dx = (wall[0] - boss['x']) // 3
        dy = (wall[1] - boss['y']) // 3
        place(game, (boss['x'] + dx, boss['y'] + dy))
        boss['last_seen'] = list(position(game.player))
        game.plan()
        self.assertIn(list(wall), boss['intent']['cells'])
        self.assertFalse(game.walkable(wall))
        evade = next(k for k, v in DIRS.items() if v == (-dy, dx))
        go(game, 'move', evade)
        self.assertTrue(game.walkable(wall))
        self.assertTrue(route(game, position(feature(game, 'siege-cache'))))
        game.depth = 25
        game.enter_room()
        boss = next(e for e in game.enemies if e['kind'] == 'mirrorboss')
        game.weapon, game.mode = 'fan', 'power'
        game.player.update(x=boss['x'] - 1, y=boss['y'])
        boss['energy'] = 3
        boss['last_seen'] = list(position(game.player))
        game.upgrades = ['heavy']
        game.update_visibility()
        game.plan()
        self.assertEqual((boss['intent']['weapon'], boss['intent']['damage'], boss['intent']['cost']), ('fan', 4, 3))

    def test_seeded_rare_room_rewards_once(self):
        game = FloorDungeon(3)
        self.assertTrue(game.rare_room)
        target = position(feature(game, 'wonder'))
        path = route(game, position(feature(game, 'chest')))
        self.assertTrue(path)
        game.locked = False
        game.enemies = []
        for room in game.rooms_data:
            room['cleared'] = True
        game.player['hp'] = 2
        for direction in route(game, target):
            go(game, 'move', direction)
            if game.choices:
                go(game, 'choose', choice=game.choices[0]['id'])
        self.assertEqual((game.player['hp'], game.player['energy']), (5, game.cap))
        game.finish_action()
        self.assertEqual(game.player['hp'], 5)
