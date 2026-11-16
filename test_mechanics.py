import json
import unittest
from random import Random

from floor import FloorDungeon
from test_floor import go, route, place, feature, position
from dungeon import DIRS


class ExpeditionMechanicsTests(unittest.TestCase):
    def test_route_sanity_forecast_counts_known_light_without_hiding_earlier_corrosion(self):
        game = self.arena()
        game.sanity = 1
        game.features.append(dict(id='visible-light', kind='light_wisp', x=7, y=5, used=False))
        game.update_visibility()
        before = game.dump()
        route = game.path_details([7, 5], forecast=True)
        self.assertEqual(route['sanityForecast'], dict(start=1, end=89, recovered=90, lowAt=1, corrosionAt=2))
        self.assertEqual(game.dump(), before)
        for direction in route['path']:
            go(game, 'move', direction)
        self.assertEqual((game.sanity, game.player['hp']), (89, 19))

    def test_route_sanity_forecast_ignores_light_on_a_mapped_unseen_tile(self):
        game = self.arena()
        game.sanity = 101
        game.features.append(dict(id='fog-light', kind='light_radiant', x=10, y=5, used=False))
        game.mapped.append([10, 5])
        forecast = game.path_details([10, 5], forecast=True)['sanityForecast']
        self.assertEqual(forecast, dict(start=101, end=98, recovered=0, lowAt=4, corrosionAt=None))

    def test_known_unalerted_enemy_does_not_shorten_safe_routes(self):
        game = self.arena()
        game.smoke = 3
        self.enemy(game, 3, 8)
        game.plan()
        self.assertFalse(game.state()['pursuing'])
        self.assertEqual(game.path_to([6, 5]), ['right', 'right', 'right'])
        game.smoke = 0
        game.plan()
        self.assertTrue(game.state()['pursuing'])
        self.assertEqual(game.path_to([6, 5]), ['right'])

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

    def test_kills_only_restore_sanity_when_player_collects_dropped_light(self):
        game = self.arena()
        game.sanity = 100
        game.weapon = 'fan'
        first = self.enemy(game, 4, 5, hp=1, regular_loot=True)
        self.enemy(game, 5, 4, hp=1)
        self.enemy(game, 5, 6, kind='broodling', hp=1, summoner=12, regular_loot=True)
        first['id'] = next(ident for ident in range(3, 200)
                           if 20 <= Random(game.seed + game.depth * 71993 + ident * 1103).randrange(100) < 30)
        go(game, 'wave', 'right')
        self.assertFalse(game.enemies)
        self.assertEqual(game.sanity, 100)
        self.assertFalse(any(fx['kind'] == 'sanity_gain' for fx in game.effects))
        self.assertEqual([feature['kind'] for feature in game.features], ['light_wisp'])
        go(game, 'move', 'right')
        self.assertEqual(game.sanity, 189)

    def test_wisp_boosts_damage_and_soul_boosts_charge_independently(self):
        game = self.arena()
        game.sanity = 450
        game.player['energy'] = 0
        game.upgrades = ['echo']
        game.echo_charges = 2
        game.features.append(dict(id='test-light', kind='light_wisp', x=3, y=5, used=False))
        go(game, 'guard')
        self.assertEqual((game.sanity, game.light_blessings), (450, {'light_wisp': 65}))
        go(game, 'charge')
        self.assertEqual(game.player['energy'], 2)
        game.light_blessings['light_wisp'] = 2
        game.features.append(dict(id='test-soul', kind='light_soul', x=3, y=5, used=False))
        go(game, 'guard')
        self.assertEqual(game.light_blessings, {'light_wisp': 1, 'light_soul': 105})
        enemy = self.enemy(game, 4, 5, hp=8)
        self.assertEqual(game.preview_details('wave', 'right')['hits'][0]['damage'], 7)
        self.assertEqual(game.light_blessings['light_wisp'], 1)
        go(game, 'wave', 'right')
        self.assertEqual(enemy['hp'], 1)
        self.assertEqual(game.light_blessings, {'light_soul': 104})
        self.assertEqual(game.state()['waveStats']['damage'], 6)
        game.enemies.clear()
        go(game, 'charge')
        self.assertEqual(game.player['energy'], 3)

    def test_light_step_progress_survives_reload_and_refresh(self):
        game = self.arena()
        game.player['hp'] = 3
        game.light_blessings = {'light_radiant': 80}
        for _ in range(24):
            go(game, 'move', 'right')
            go(game, 'move', 'left')
        game.features.append(dict(id='test-light', kind='light_soul', x=3, y=5, used=False))
        go(game, 'guard')
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.light_blessings, {'light_radiant': 31, 'light_soul': 105})
        self.assertEqual((game.light_steps, game.player['hp']), (48, 3))
        go(game, 'move', 'right')
        self.assertEqual((game.light_steps, game.player['hp']), (49, 3))
        go(game, 'move', 'left')
        self.assertEqual((game.light_steps, game.player['hp']), (0, 6))

    def test_radiant_only_counts_steps_for_its_own_duration(self):
        game = self.arena()
        game.light_blessings = {'light_wisp': 10}
        game.features.append(dict(id='test-radiant', kind='light_radiant', x=3, y=5, used=False))
        go(game, 'guard')
        self.assertEqual(game.light_blessings, {'light_wisp': 9, 'light_radiant': 155})
        game.light_blessings['light_radiant'] = 1
        go(game, 'move', 'right')
        self.assertEqual((game.light_blessings, game.light_steps), ({'light_wisp': 8}, 0))
        go(game, 'move', 'left')
        self.assertEqual(game.light_steps, 0)

    def test_fan_hits_multiple_and_power_shortens_range(self):
        game = self.arena()
        near = self.enemy(game, 4, 5, hp=13)
        flank = self.enemy(game, 5, 4, hp=13)
        go(game, 'equip', choice='fan')
        for enemy in game.enemies:
            enemy['intent'] = dict(action='wait', cells=[])
        go(game, 'wave', 'right')
        self.assertEqual((near['hp'], flank['hp']), (8, 8))
        game.mode = 'power'
        game.player['energy'] = 2
        for enemy in game.enemies:
            enemy['intent'] = dict(action='wait', cells=[])
        go(game, 'wave', 'right')
        self.assertEqual((near['hp'], flank['hp']), (0, 8))

    def test_combat_statuses_use_actual_health_changes_and_hide_unseen_targets(self):
        game = self.arena()
        game.player['hp'] = 19
        game.upgrades = ['heart']
        self.enemy(game, 4, 5, intent=dict(action='melee', cells=[[3, 5]], damage=5))
        go(game, 'guard')
        statuses = [(fx['kind'], fx['amount'], fx.get('source'))
                    for fx in game.state()['effects'] if fx.get('target') == '你']
        self.assertEqual(statuses, [('healed', 1, '护心'), ('blocked', 4, None), ('damage', 1, None)])
        self.assertEqual(game.player['hp'], 19)

        remote = self.enemy(game, 14, 5, name='远处敌人')
        game.record_status('damage', remote, 1)
        effect = game.state()['effects'][-1]
        self.assertEqual(effect['cells'], [])
        self.assertNotIn('target', effect)
        self.assertNotIn('targetId', effect)

    def test_return_uses_original_path_after_move_and_reload(self):
        game = self.arena()
        game.weapon = 'return'
        target = self.enemy(game, 5, 5, hp=12)
        go(game, 'wave', 'right')
        self.assertEqual(target['hp'], 7)
        self.assertEqual(game.returning[0]['cells'], [[5, 5], [4, 5]])
        game = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        game.enemies[0]['intent'] = dict(action='wait', cells=[])
        go(game, 'move', 'up')
        self.assertEqual(game.enemies[0]['hp'], 2)
        self.assertFalse(game.returning)

    def test_reflection_spends_energy_and_redirects_wave(self):
        game = self.arena()
        game.upgrades.append('reflect')
        shooter = self.enemy(game, 5, 5, energy=1)
        shooter['intent'] = dict(action='wave', cells=[[4, 5], [3, 5]], direction='left')
        before = game.dump()
        self.assertEqual(game.preview('reflect', 'right'), [{'name': 'ram', 'damage': 1}])
        self.assertEqual(game.dump(), before)
        go(game, 'reflect', 'right')
        self.assertEqual((game.player['energy'], game.player['hp'], shooter['hp']), (2, 20, 2))
        game.player['energy'] = 0
        with self.assertRaises(ValueError):
            go(game, 'reflect', 'right')

    def test_mirror_turns_projectile_then_rotates_and_persists(self):
        game = self.arena(14, 6)
        target = self.enemy(game, 16, 4, hp=8)
        self.assertEqual(game.trace([14, 6], 'right'), [[15, 6], [16, 6], [16, 5], [16, 4]])
        go(game, 'wave', 'right')
        self.assertEqual(target['hp'], 2)
        game = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        self.assertEqual(game.tile_at([16, 6])['slash'], chr(92))
        self.assertEqual(game.trace([14, 6], 'right')[-1], [16, 8])

    def test_floor_opens_on_first_entry_and_reentering_drops_either_actor(self):
        game = self.arena(5, 17)
        go(game, 'move', 'right')
        self.assertEqual(game.tile_at([6, 17])['stage'], 2)
        self.assertEqual((game.depth, game.player['hp']), (1, 20))
        game = FloorDungeon.restore(game.dump())
        pit = next(tile for tile in game.state()['terrain'] if position(tile) == (6, 17))
        self.assertEqual(pit['stage'], 2)
        go(game, 'guard')
        self.assertEqual(game.player['hp'], 20)
        go(game, 'move', 'left')
        enemy = self.enemy(game, 7, 17)
        enemy['intent'] = dict(action='move', target=[6, 17], cells=[])
        go(game, 'guard')
        self.assertFalse(game.enemies)
        self.assertEqual(game.state()['falls'][0]['cell'], [6, 17])
        go(game, 'move', 'right')
        self.assertIsNone(game.result)
        self.assertEqual((game.depth, game.player['hp']), (2, 12))
        self.assertEqual(game.state()['fallTransition']['fromCell'], [6, 17])

    def test_lance_and_guardian_intercept(self):
        game = self.arena()
        game.weapon = 'lance'
        ally = self.enemy(game, 4, 5, name='同伴')
        second = self.enemy(game, 5, 5, hp=12)
        escort = self.enemy(game, 4, 4, kind='escort', name='护卫', hp=12)
        game.counter = True
        self.assertEqual(game.state()['enemies'][0]['guardedBy'], '护卫')
        before = game.dump()
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['interceptions'], [
            dict(guard='护卫', target='同伴', cells=[[4, 5], [4, 4]], damage=7),
        ])
        self.assertEqual(game.dump(), before)
        go(game, 'wave', 'right')
        self.assertEqual((ally['hp'], second['hp'], escort['hp']), (3, 3, 5))

    def test_guardian_intercept_preview_hides_escort_outside_view(self):
        game = self.arena()
        game.talents = ['reach']
        game.weapon_levels['straight'] = 2
        ally = self.enemy(game, 9, 5, name='边缘目标')
        escort = self.enemy(game, 9, 6, kind='escort', name='暗处护卫', hp=10)
        self.assertNotIn('guardedBy', game.state()['enemies'][0])
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['interceptions'], [])
        self.assertNotIn('暗处护卫', str(preview))
        go(game, 'wave', 'right')
        self.assertEqual((ally['hp'], escort['hp']), (3, 3))

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
        self.assertEqual(boss['intent']['damage'], 7)
        self.assertIn(list(position(game.player)), game.state()['dangerCells'])

        restored = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        hp = restored.player['hp']
        go(restored, 'guard')
        self.assertEqual(restored.player['hp'], hp - 3)

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
        self.assertEqual((boss['intent']['weapon'], boss['intent']['damage'], boss['intent']['cost']), ('fan', 14, 3))

    def test_seeded_rare_room_rewards_once(self):
        game = FloorDungeon(3)
        self.assertTrue(game.rare_room)
        target = position(feature(game, 'wonder'))
        path = route(game, game.rooms_data[3]['anchor'])
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
        self.assertEqual((game.player['hp'], game.player['energy']), (11, game.cap))
        game.finish_action()
        self.assertEqual(game.player['hp'], 11)
