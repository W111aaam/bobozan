import json
import unittest
from unittest.mock import patch

from floor import BOSS_FLOORS, FloorDungeon
from growth import CLASSES, RUNES, WEAPON_DAMAGE
from test_floor import go, place
import test_mechanics


class GrowthTests(unittest.TestCase):
    def test_dodge_rewards_avoiding_locked_attack_and_keeps_cooldown_after_reload(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.hero_class = 'straight'
        game.player['energy'] = 0
        fixture.enemy(game, 5, 5, hp=12, intent=dict(action='wave', cells=[[4, 5], [3, 5]], damage=5))
        preview = game.preview_details('dodge', 'up')
        self.assertIn('闪避 · 回复 1 能量', preview['events'])
        self.assertEqual((game.turn, game.player['energy']), (0, 0))
        go(game, 'dodge', 'up')
        self.assertEqual((game.player['y'], game.player['hp'], game.player['energy']), (4, 20, 1))
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.dodge_cooldown, 30)
        with self.assertRaisesRegex(ValueError, '冷却'):
            go(game, 'dodge', 'down')
        game.enemies = []
        for _ in range(30):
            go(game, 'guard')
        go(game, 'dodge', 'down')
        self.assertEqual((game.player['energy'], game.dodge_cooldown), (1, 30))

    def test_dodge_does_not_reward_staying_in_locked_attack_or_contested_move(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.hero_class = 'straight'
        game.player['energy'] = 0
        fixture.enemy(game, 3, 7, hp=12, intent=dict(action='area', cells=[[3, 5], [3, 4]], damage=5))
        go(game, 'dodge', 'up')
        self.assertEqual((game.player['hp'], game.player['energy']), (15, 0))
        game.dodge_ready_turn = 0
        game.enemies[0]['intent'] = dict(action='move', cells=[], target=[4, 4])
        go(game, 'dodge', 'right')
        self.assertEqual((game.player['x'], game.dodge_cooldown), (3, 0))

    def test_fan_covers_eight_neighbors_and_routes_diagonally_without_corner_cutting(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.hero_class = game.weapon = 'fan'
        game.walls = [[3, 4]]
        game._wall_cells = {(3, 4)}
        game.update_visibility()
        with self.assertRaisesRegex(ValueError, '阻挡'):
            go(game, 'move', 'up-right')
        self.assertEqual(game.path_to([4, 6]), ['down-right'])
        go(game, 'move', 'down-right')
        self.assertEqual((game.player['x'], game.player['y']), (4, 6))
        behind = fixture.enemy(game, 3, 6, hp=16)
        diagonal = fixture.enemy(game, 5, 7, hp=16)
        distant = fixture.enemy(game, 4, 8, hp=16)
        go(game, 'wave', 'up')
        self.assertEqual((behind['hp'], diagonal['hp'], distant['hp']), (11, 11, 16))

    def test_return_orb_stops_at_target_or_enemy_and_tracks_player_next_beat(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.hero_class = game.weapon = 'return'
        target = fixture.enemy(game, 5, 5, hp=18)
        later = fixture.enemy(game, 6, 5, hp=18)
        go(game, 'wave', 'right', choice=[7, 5])
        self.assertEqual((target['hp'], later['hp']), (13, 18))
        self.assertEqual(game.state()['returning'][0]['orbCell'], [5, 5])
        self.assertEqual(game.state()['returning'][0]['sidePaths']['3,4'][-1], [3, 4])
        game = FloorDungeon.restore(game.dump())
        for enemy in game.enemies:
            enemy['intent'] = dict(action='wait', cells=[])
        go(game, 'guard')
        self.assertEqual(game.enemies[0]['hp'], 8)
        self.assertFalse(game.returning)
        game.enemies = []
        go(game, 'wave', 'right', choice=[4, 5])
        self.assertEqual(game.state()['returning'][0]['orbCell'], [4, 5])
        go(game, 'move', 'up')
        self.assertEqual(next(effect['cells'][-1] for effect in game.effects if effect['kind'] == 'tide_return'), [3, 4])

    def test_lance_is_unbounded_and_range_bonuses_stack_additively(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.hero_class = game.weapon = 'lance'
        game.width = 110
        game.talents = ['reach', 'through']
        game.player['energy'] = game.cap
        foes = [fixture.enemy(game, x, 5, hp=25) for x in range(4, 106)]
        wall = [104, 5]
        game.walls = [wall]
        game._wall_cells = {tuple(wall)}
        self.assertEqual(game.wave_damage_before_defense('wave'), 9)
        self.assertEqual(game.wave_damage_before_defense('heavy'), 16)
        self.assertIsNone(game.player_wave_range())
        go(game, 'wave', 'right')
        self.assertTrue(all(enemy['hp'] == 16 for enemy in foes[:100]))
        self.assertTrue(all(enemy['hp'] == 25 for enemy in foes[100:]))

    def test_reflect_is_a_reward_and_heavy_is_available_from_start(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.hero_class = 'straight'
        before = game.dump()
        with self.assertRaisesRegex(ValueError, '反弹遗物'):
            go(game, 'reflect', 'right')
        self.assertEqual(game.dump(), before)
        go(game, 'heavy', 'right')
        self.assertEqual(game.player['energy'], 0)
        game.depth = 5
        game.make_choices(1)
        self.assertIn('reflect', {choice['id'] for choice in game.choices})
        self.assertNotIn('heavy', {choice['id'] for choice in game.choices})
        go(game, 'choose', choice='reflect')
        self.assertTrue(game.state()['canReflect'])
        saved = game.dump()
        saved['upgrades'] = ['heavy']
        restored = FloorDungeon.restore(saved)
        self.assertEqual(restored.upgrades, ['reflect'])

    def test_unbounded_wave_stops_when_mirrors_create_a_loop(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.hero_class = game.weapon = 'lance'
        game.terrain = [dict(x=x, y=y, kind='mirror', slash=slash)
                        for x, y, slash in ((4, 5, chr(92)), (4, 6, '/'), (2, 6, chr(92)), (2, 5, '/'))]
        ray = game.player_wave_paths([3, 5], 'right')[0]
        self.assertEqual(ray, [[4, 5], [4, 6], [3, 6], [2, 6], [2, 5], [3, 5]])

    def test_rune_journal_remembers_seen_unclaimed_drops_across_floors_and_old_saves(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.drop_rune('seen', [5, 5])
        game.drop_rune('in-fog', [12, 5])
        game.update_visibility()
        known = game.state()['runeJournal']
        self.assertEqual(len(known), 1)
        self.assertEqual((known[0]['depth'], known[0]['cell']), (1, [5, 5]))
        game.change_floor(2, 'down')
        game.plan()
        self.assertEqual(game.state()['runeJournal'], known)
        saved = json.loads(json.dumps(game.dump()))
        saved.pop('rune_landmarks')
        game = FloorDungeon.restore(saved)
        self.assertEqual(game.state()['runeJournal'], known)
        game.change_floor(1, 'up')
        game.plan()
        self.assertEqual(game.state()['runeJournal'], known)
        place(game, (5, 5))
        go(game, 'equip_ground_rune', choice='seen')
        self.assertEqual(game.state()['runeJournal'], [])
        game.change_floor(2, 'down')
        game.plan()
        self.assertEqual(FloorDungeon.restore(game.dump()).state()['runeJournal'], [])

    def test_exhausted_rune_pool_keeps_unclaimed_secret_and_vault_rewards(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.dropped_runes = list(RUNES)
        game.features = [
            dict(id='secret-reward', kind='rune_shard', x=4, y=5, used=False),
            dict(id='cache', kind='rune_shard', x=5, y=5, used=False),
            dict(id='already-used', kind='rune_shard', x=6, y=5, used=True),
        ]
        game = FloorDungeon.restore(game.dump())
        self.assertEqual([(f['id'], f['kind'], f['item']) for f in game.features],
                         [('secret-reward', 'dropped_item', 'recall'), ('cache', 'dropped_item', 'frost_smoke')])
        go(game, 'move', 'right')
        go(game, 'move', 'right')
        self.assertEqual(game.inventory, ['recall', 'frost_smoke'])
        game = FloorDungeon.restore(game.dump())
        self.assertTrue(all(f['used'] for f in game.features))
        self.assertEqual(game.dropped_runes, list(RUNES))

    def test_exhausted_rune_pool_gives_boss_and_statue_distinct_light_rewards(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.dropped_runes = list(RUNES)
        fixture.enemy(game, 4, 5, kind='armedidol', hp=1)
        self.assertEqual(game.state()['enemies'][0]['lootHint'], '掉落：微光')
        go(game, 'wave', 'right')
        self.assertEqual(game.features[0]['kind'], 'light_wisp')
        game.depth = 5
        game.enter_room()
        boss, = game.enemies
        game.enemies = []
        game.finish_side_enemies({}, [boss])
        game.finish_action()
        game.finish_action()
        boss_drops = [f for f in game.features if f['id'].startswith('boss-rune-')]
        self.assertEqual([f['kind'] for f in boss_drops], ['light_soul'])
        self.assertEqual([f['kind'] for f in game.features if f['id'].startswith('boss-radiant-')],
                         ['light_radiant'])
        self.assertEqual([f['kind'] for f in game.features if f['id'].startswith('boss-core-')],
                         ['forge_core'])
        self.assertEqual(game.bag_capacity, 10)
        self.assertTrue(game.choices)

    def test_boss_drops_all_rewards_on_death_while_another_enemy_is_alive(self):
        game = FloorDungeon(0)
        game.depth = 20
        game.enter_room()
        boss, guard = game.enemies
        boss.update(hp=1, intent=dict(action='wait', cells=[]))
        place(game, (boss['x'] - 1, boss['y']))
        game.player['energy'] = 3
        panel = next(enemy for enemy in game.state()['enemies'] if enemy['id'] == boss['id'])
        self.assertEqual(panel['lootHint'], '固定掉落：随机刻印、辉光和锻造核心')
        self.assertEqual(panel['lightLoot']['light_radiant'], 100)
        go(game, 'wave', 'right')
        self.assertEqual(game.enemies, [guard])
        self.assertFalse(game.choices)
        saved = FloorDungeon.restore(game.dump())
        saved.finish_side_enemies({}, [boss])
        drops = [f for f in saved.features if f['id'].startswith('boss-')]
        self.assertEqual([f['kind'] for f in drops], ['rune', 'light_radiant', 'forge_core'])
        place(saved, (drops[0]['x'], drops[0]['y']))
        saved.sanity = 100
        go(saved, 'guard')
        self.assertEqual(saved.sanity, 399)
        self.assertEqual(len(saved.ground_runes_here()), 1)
        self.assertEqual(saved.forge_cores, 1)
        saved = FloorDungeon.restore(saved.dump())
        go(saved, 'guard')
        self.assertEqual(saved.forge_cores, 1)
        self.assertFalse(any(feature['kind'] == 'forge_core' for feature in saved.state()['features']))

    def test_supply_comparison_predicts_launcher_with_current_build_without_equipping_it(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.weapon = 'fan'
        game.launcher_upgrades['fan'] = 'barrier_fan'
        game.upgrades = ['heavy']
        game.weapon_levels['fan'] = 1
        game.features = [dict(id='box', kind='supply_choice', x=3, y=5, used=False)]
        go(game, 'open_supply')
        before = game.dump()
        choice = next(c for c in game.state()['choices'] if c['id'] == 'close_fan')
        self.assertEqual(choice['comparison'], [
            dict(label='覆盖', before='2 格 · 格挡后加宽', after='周围八格'),
            dict(label='波伤害', before='8', after='12'),
            dict(label='重波伤害', before='13', after='20'),
        ])
        self.assertEqual(game.dump(), before)
        go(game, 'choose', choice='close_fan')
        stats = game.state()['waveStats']
        self.assertEqual((stats['damage'], stats['heavyDamage']), (12, 20))

    def test_sniper_comparison_shows_only_distances_reached_in_current_mode(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.mode = 'power'
        game.features = [dict(id='box', kind='supply_choice', x=3, y=5, used=False)]
        go(game, 'open_supply')
        choice = next(c for c in game.state()['choices'] if c['id'] == 'sniper_launcher')
        self.assertEqual(next(stat['after'] for stat in choice['comparison'] if stat['label'] == '波伤害'), '1 格 7 伤 · 2 格 9 伤')

    def test_close_fan_hits_all_eight_adjacent_cells_with_rounded_damage(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'fan'
        game.features = [dict(id='box', kind='supply_choice', x=3, y=5, used=False)]
        game.upgrades = ['heavy']
        go(game, 'open_supply')
        go(game, 'choose', choice='close_fan')
        adjacent = {(x, y) for y in range(4, 7) for x in range(2, 5)} - {(3, 5)}
        targets = [fixture.enemy(game, x, y, hp=18) for x, y in sorted(adjacent)]
        remote = fixture.enemy(game, 5, 5, hp=18)
        stats = game.state()['waveStats']
        self.assertEqual((stats['range'], stats['damage'], stats['heavyDamage']), (1, 8, 15))
        for direction in ('left', 'right', 'up', 'down'):
            preview = game.preview_details('wave', direction)
            self.assertEqual(set(map(tuple, preview['cells'])), adjacent)
            self.assertEqual([hit['damage'] for hit in preview['hits']], [8] * 8)
        go(game, 'heavy', 'right')
        self.assertEqual([target['hp'] for target in targets], [3] * 8)
        self.assertEqual(remote['hp'], 18)

    def test_close_fan_cannot_gain_range_or_fire_through_blocked_corners(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'fan'
        game.launcher_upgrades['fan'] = 'close_fan'
        game.weapon_levels['fan'] = 2
        game.talents = ['reach', 'through']
        game.upgrades = ['parallel', 'flank_array', 'pierce', 'blink']
        game.doors.append([4, 5])
        game._door_cells.add((4, 5))
        game.update_visibility()
        preview = game.preview_details('wave', 'right')
        self.assertEqual(game.state()['waveStats']['range'], 1)
        self.assertTrue(all(max(abs(x - 3), abs(y - 5)) == 1 for x, y in preview['cells']))
        self.assertIsNone(preview['landing'])
        go(game, 'wave', 'right')
        cells = {tuple(cell) for effect in game.effects if effect['kind'] == 'wave' for cell in effect['cells']}
        self.assertFalse({(4, 4), (4, 5), (4, 6)} & cells)
        self.assertEqual((game.player['x'], game.player['y']), (3, 5))

    def test_sniper_launcher_uses_distance_for_normal_and_heavy_main_beams(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.launcher_upgrades['straight'] = 'sniper_launcher'
        game.weapon_levels['straight'] = 1
        game.upgrades = ['heavy']
        near = fixture.enemy(game, 2, 5, hp=20)
        mid = fixture.enemy(game, 3, 7, hp=20)
        far = fixture.enemy(game, 6, 5, hp=20)
        self.assertEqual([game.preview('wave', direction)[0]['damage']
                          for direction in ('left', 'down', 'right')], [7, 9, 12])
        self.assertEqual(game.preview('heavy', 'right')[0]['damage'], 17)
        go(game, 'heavy', 'right')
        self.assertEqual((near['hp'], mid['hp'], far['hp']), (20, 20, 3))

    def test_straight_launchers_are_claimed_once_and_can_be_swapped_after_reload(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.features = [dict(id='first', kind='supply_choice', x=3, y=5, used=False)]
        game.weapon_levels['straight'] = 2
        game.inscriptions['straight'] = 'frost'
        go(game, 'open_supply')
        go(game, 'choose', choice='stride_launcher')
        game.features.append(dict(id='second', kind='supply_choice', x=3, y=5, used=False))
        go(game, 'open_supply')
        go(game, 'choose', choice='sniper_launcher')
        game = FloorDungeon.restore(game.dump())
        self.assertEqual((game.launcher, game.weapon_level, game.rune), ('sniper_launcher', 2, 'frost'))
        self.assertEqual({option['id'] for option in game.supply_options()}, {'smoke', 'lure'})
        go(game, 'equip_launcher', choice='stride_launcher')
        self.assertEqual((game.launcher, game.weapon_level, game.rune, game.turn), ('stride_launcher', 2, 'frost', 0))
        go(game, 'equip_launcher', choice='standard')
        self.assertIsNone(game.launcher)
        with self.assertRaises(ValueError):
            go(game, 'equip_launcher', choice='barrier_fan')

    def test_tide_launcher_steers_after_movement_and_survives_reload(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'return'
        game.features = [dict(id='box', kind='supply_choice', x=3, y=5, used=False)]
        go(game, 'open_supply')
        go(game, 'choose', choice='tide_launcher')
        self.assertIn('潮折器 · 下一拍回波飞向行动后的位置', game.preview_details('wave', 'right')['events'])
        go(game, 'wave', 'right')
        game = FloorDungeon.restore(game.dump())
        target = fixture.enemy(game, 4, 4, hp=6)
        preview = game.state()['returning'][0]
        self.assertIn([4, 4], preview['sidePaths']['3,4'])
        self.assertNotIn([4, 4], preview['cells'])
        go(game, 'move', 'up')
        self.assertEqual(target['hp'], 1)
        self.assertFalse(game.returning)
        self.assertEqual(next(effect['cells'][0] for effect in game.effects
                              if effect['kind'] == 'tide_return'), [7, 5])

    def test_tide_return_uses_the_door_state_after_moving(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'return'
        game.launcher_upgrades['return'] = 'tide_launcher'
        go(game, 'wave', 'right')
        game.doors.append([4, 5])
        game._door_cells.add((4, 5))
        game.update_visibility()
        self.assertEqual(game.tide_return_path([7, 5], [3, 5]), [[7, 5], [6, 5], [5, 5]])
        self.assertEqual(game.state()['returning'][0]['sidePaths']['4,5'][-1], [4, 5])
        go(game, 'move', 'right')
        self.assertEqual(next(effect['cells'][-1] for effect in game.effects
                              if effect['kind'] == 'tide_return'), [4, 5])

    def test_barrier_fan_adds_two_edge_cells_after_successful_guard(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'fan'
        game.features = [dict(id='box', kind='supply_choice', x=3, y=5, used=False)]
        go(game, 'open_supply')
        go(game, 'choose', choice='barrier_fan')
        self.assertEqual(game.state()['growth']['emitterName'], '屏障扇')
        self.assertNotIn('barrier_fan', {option['id'] for option in game.supply_options()})
        normal = set(map(tuple, game.state()['aimPaths']['right']))
        go(game, 'guard')
        self.assertFalse(game.barrier_wide)
        fixture.enemy(game, 2, 5, hp=6, intent=dict(action='melee', cells=[[3, 5]], damage=1))
        go(game, 'guard')
        game = FloorDungeon.restore(game.dump())
        self.assertTrue(game.barrier_wide)
        self.assertEqual(set(map(tuple, game.state()['aimPaths']['right'])) - normal, {(5, 3), (5, 7)})
        upper = fixture.enemy(game, 5, 3, hp=12)
        lower = fixture.enemy(game, 5, 7, hp=12)
        preview = game.preview_details('wave', 'right')
        self.assertIn('屏障扇 · 两侧各扩大一格', preview['events'])
        self.assertTrue(game.barrier_wide)
        go(game, 'wave', 'right')
        self.assertEqual((upper['hp'], lower['hp']), (4, 4))
        self.assertFalse(game.barrier_wide)
        self.assertEqual(set(map(tuple, game.state()['aimPaths']['right'])), normal)

    def test_barrier_fan_keeps_ready_when_charging_and_respects_walls(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'fan'
        game.launcher_upgrades['fan'] = 'barrier_fan'
        game.barrier_ready = True
        game.upgrades = ['heavy']
        game.mode = 'power'
        game.player['energy'] = 2
        game.walls.append([4, 4])
        game._wall_cells.add((4, 4))
        target = fixture.enemy(game, 4, 6, hp=16)
        go(game, 'charge')
        preview = game.preview_details('heavy', 'right')
        self.assertNotIn([4, 4], preview['cells'])
        self.assertIn([4, 6], preview['cells'])
        go(game, 'heavy', 'right')
        self.assertEqual(target['hp'], 3)
        self.assertFalse(game.barrier_wide)

    def test_restore_stride_launcher_from_previous_save_format(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        saved = game.dump()
        saved.pop('launcher_upgrades')
        saved.update(stride_launcher=True, stride_ready=True)
        game = FloorDungeon.restore(saved)
        self.assertEqual((game.launcher, game.stride_range), ('stride_launcher', 1))

    def test_barrier_fan_uses_the_successful_reflection_trigger(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades.append('reflect')
        game.weapon = 'fan'
        game.launcher_upgrades['fan'] = 'barrier_fan'
        go(game, 'reflect', 'right')
        self.assertFalse(game.barrier_wide)
        fixture.enemy(game, 5, 5, hp=6, energy=1,
                      intent=dict(action='wave', cells=[[4, 5], [3, 5]], direction='left'))
        go(game, 'reflect', 'right')
        self.assertTrue(game.barrier_wide)

    def test_stride_launcher_shares_supply_claim_and_preserves_straight_progression(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.features = [dict(id='box', kind='supply_choice', x=3, y=5, used=False)]
        game.inventory = ['ankh'] * game.bag_capacity
        game.weapon_levels['straight'] = 2
        game.inscriptions['straight'] = 'frost'
        go(game, 'open_supply')
        go(game, 'choose', choice='stride_launcher')
        self.assertEqual((game.weapon, game.weapon_level, game.rune), ('straight', 2, 'frost'))
        self.assertEqual(len(game.inventory), game.bag_capacity)
        self.assertEqual(game.state()['growth']['emitterName'], '踏步枪')
        with self.assertRaises(ValueError):
            go(game, 'open_supply')
        self.assertNotIn('stride_launcher', {item['id'] for item in game.supply_options()})

    def test_stride_launcher_extends_next_wave_once_even_in_power_mode(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.launcher_upgrades['straight'] = 'stride_launcher'
        game.mode = 'power'
        game.upgrades = ['heavy']
        ram = fixture.enemy(game, 4, 4, hp=6, intent=dict(action='move', cells=[], target=[4, 5]))
        go(game, 'move', 'right')
        self.assertFalse(game.stride_ready)
        game.enemies.remove(ram)
        go(game, 'move', 'right')
        go(game, 'move', 'right')
        go(game, 'guard')
        game = FloorDungeon.restore(game.dump())
        target = fixture.enemy(game, 8, 5, hp=17)
        self.assertEqual(game.state()['waveStats']['range'], 3)
        self.assertIn([8, 5], game.state()['aimPaths']['right'])
        preview = game.preview_details('heavy', 'right')
        self.assertIn('踏步枪 · 本次射程 +1', preview['events'])
        self.assertIn([8, 5], preview['cells'])
        self.assertTrue(game.stride_ready)
        go(game, 'heavy', 'right')
        self.assertEqual(target['hp'], 3)
        self.assertEqual(game.state()['waveStats']['range'], 2)
        self.assertFalse(game.stride_ready)

    def test_rune_pool_is_randomized_and_never_repeats_across_floors_or_reloads(self):
        orders = []
        for seed in (21, 22):
            game = FloorDungeon(seed, 'straight')
            for index in range(len(RUNES) + 2):
                if index == 2:
                    game.change_floor(2, 'down')
                    game = FloorDungeon.restore(game.dump())
                    game.change_floor(1, 'up')
                game.drop_rune(f'test-rune-{index}', [game.player['x'], game.player['y']])
            self.assertEqual(len(game.dropped_runes), len(RUNES) - len(BOSS_FLOORS))
            for depth in BOSS_FLOORS:
                game.change_floor(depth, 'down')
                boss, *guards = game.enemies
                game.enemies = guards
                game.finish_side_enemies({}, [boss])
                drops = [f['kind'] for f in game.features if f['id'].startswith('boss-')]
                self.assertEqual(drops, ['rune', 'light_radiant', 'forge_core'])
                game = FloorDungeon.restore(game.dump())
            self.assertEqual(len(game.dropped_runes), len(RUNES))
            self.assertEqual(set(game.dropped_runes), set(RUNES))
            self.assertLessEqual(len([f for f in game.features if f['kind'] == 'rune']), len(RUNES))
            self.assertEqual(FloorDungeon.restore(game.dump()).dropped_runes, game.dropped_runes)
            orders.append(game.dropped_runes)
        self.assertNotEqual(*orders)

    def test_rune_is_equipped_from_its_ground_tile_once(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.drop_rune('first', [3, 5])
        game.drop_rune('second', [4, 5])
        first, second = game.features[-2:]
        with self.assertRaisesRegex(ValueError, '所在的地格'):
            go(game, 'equip_ground_rune', choice=second['id'])
        with self.assertRaisesRegex(ValueError, '未知动作'):
            go(game, 'etch', choice=first['rune'])
        self.assertNotIn('runes', game.state()['growth'])
        go(game, 'equip_ground_rune', choice=first['id'])
        self.assertEqual((game.rune, game.turn), (first['rune'], 0))
        self.assertTrue(first['used'])
        self.assertFalse(game.state()['groundRunes'])
        go(game, 'move', 'right')
        self.assertEqual(game.rune, first['rune'])
        self.assertEqual(game.state()['groundRunes'][0]['name'], RUNES[second['rune']][0])
        go(game, 'equip_ground_rune', choice=second['id'])
        self.assertEqual(game.rune, second['rune'])
        self.assertIn(first['rune'], game.dropped_runes)
        with self.assertRaisesRegex(ValueError, '所在的地格'):
            go(game, 'equip_ground_rune', choice=second['id'])

    def test_missing_drop_history_is_rebuilt_from_equipped_and_all_visited_floors(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.drop_rune('unseen', [12, 5])
        game.drop_rune('previously_replaced', [3, 5])
        game.features[-1]['used'] = True
        game.change_floor(2, 'down')
        game.drop_rune('current', [game.player['x'], game.player['y']])
        game.inscriptions[game.weapon] = next(rune for rune in RUNES if rune not in game.dropped_runes)
        prior_runes = set(game.dropped_runes) | {game.rune}
        existing = json.loads(json.dumps(game.dump()))
        existing.pop('dropped_runes')

        restored = FloorDungeon.restore(existing)
        self.assertEqual(set(restored.dropped_runes), prior_runes)
        self.assertEqual(restored.rune, game.rune)
        for index in range(len(RUNES) - len(prior_runes) - len(BOSS_FLOORS)):
            self.assertEqual(restored.drop_rune(f'new-{index}', [3, 5]), 'rune')
            self.assertNotIn(restored.features[-1]['rune'], prior_runes)
        self.assertIsNone(restored.drop_rune('exhausted', [3, 5]))
        self.assertEqual(len(restored.dropped_runes), max(len(prior_runes), len(RUNES) - len(BOSS_FLOORS)))

    def test_conduction_deals_equal_damage_in_connected_unfrozen_water(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'conduction'
        game.upgrades = ['heavy']
        game.terrain.extend(dict(x=x, y=y, kind='water')
                            for x, y in ((4, 5), (4, 6), (4, 7), (4, 9), (6, 5)))
        game.terrain.append(dict(x=4, y=8, kind='water', ice_until=game.turn + 3))
        source = fixture.enemy(game, 4, 5, kind='shield', hp=14, intent=dict(action='guard', cells=[]))
        ally = fixture.enemy(game, 4, 7, kind='shield', hp=14, intent=dict(action='guard', cells=[]))
        distant = fixture.enemy(game, 4, 9, hp=14)
        separate = fixture.enemy(game, 6, 5, hp=14)
        preview = game.preview_details('heavy', 'right')
        self.assertEqual([hit['damage'] for hit in preview['hits']], [9, 9])
        self.assertEqual(preview['conduction'], [[4, 5], [4, 6], [4, 7]])
        go(game, 'heavy', 'right')
        self.assertEqual((source['hp'], ally['hp'], distant['hp'], separate['hp']), (5, 5, 14, 14))

    def test_dry_conduction_has_six_tile_radius_and_hides_unseen_targets(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'conduction'
        source = fixture.enemy(game, 4, 5, hp=11)
        near = fixture.enemy(game, 4, 6, hp=6)
        edge = fixture.enemy(game, 10, 5, hp=6, name='雾后目标')
        outside = fixture.enemy(game, 10, 6, hp=6)
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['conduction'], [[4, 6]])
        self.assertNotIn('雾后目标', str(preview))
        go(game, 'wave', 'right')
        self.assertEqual((source['hp'], near['hp'], edge['hp'], outside['hp']), (5, 3, 3, 6))

    @patch.dict(WEAPON_DAMAGE, straight=2)
    def test_blocked_main_beam_and_parallel_hit_do_not_trigger_conduction(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'conduction'
        game.upgrades = ['parallel']
        source = fixture.enemy(game, 4, 5, kind='shield', hp=6, intent=dict(action='guard', cells=[]))
        side = fixture.enemy(game, 4, 6, hp=6)
        bystander = fixture.enemy(game, 4, 7, hp=6)
        self.assertFalse(game.preview_details('wave', 'right')['conduction'])
        go(game, 'wave', 'right')
        self.assertEqual((source['hp'], side['hp'], bystander['hp']), (6, 5, 6))
        self.assertFalse(any(effect['kind'] == 'conduction' for effect in game.effects))

    def test_refraction_jumps_once_to_nearest_reachable_enemy(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['double']
        game.inscriptions[game.weapon] = 'refraction'
        source = fixture.enemy(game, 4, 5, hp=12)
        blocked = fixture.enemy(game, 4, 7, hp=6)
        recipient = fixture.enemy(game, 6, 4, hp=6)
        other = fixture.enemy(game, 7, 3, hp=6)
        game.walls.append([4, 6])
        game._wall_cells.add((4, 6))
        game.update_visibility()
        preview = game.preview_details('wave', 'right')
        self.assertEqual([hit['damage'] for hit in preview['hits']], [9, 3])
        self.assertEqual(len(preview['refraction']), 1)
        self.assertEqual(preview['refraction'][0][0], [4, 5])
        self.assertEqual(preview['refraction'][0][-1], [6, 4])
        go(game, 'wave', 'right')
        self.assertEqual((source['hp'], blocked['hp'], recipient['hp'], other['hp']), (3, 6, 3, 6))
        self.assertEqual(sum(effect['kind'] == 'refraction' for effect in game.effects), 1)

    def test_refraction_range_is_measured_from_impact_and_fog_clips_preview(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'refraction'
        fixture.enemy(game, 4, 5, hp=6)
        far = fixture.enemy(game, 12, 5, hp=6, name='远端目标')
        outside = fixture.enemy(game, 4, 14, hp=6)
        preview = game.preview_details('wave', 'right')
        self.assertNotIn('远端目标', str(preview))
        self.assertEqual(preview['refraction'][0][-1], [9, 5])
        go(game, 'wave', 'right')
        self.assertEqual((far['hp'], outside['hp']), (3, 6))

    def test_stagger_uses_consecutive_turns_and_skips_exactly_the_next_action(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'stagger'
        fixture.enemy(game, 4, 5, hp=18, last_seen=[3, 5],
                      intent=dict(action='melee', cells=[[3, 5]], damage=1))
        go(game, 'wave', 'right')
        game = FloorDungeon.restore(game.dump())
        self.assertTrue(game.state()['enemies'][0]['stun_marked'])
        self.assertIn('击晕 · ram跳过下一拍', game.preview_details('wave', 'right')['events'])
        damage = game.enemies[0]['intent']['damage']
        hp = game.player['hp']
        go(game, 'wave', 'right')
        self.assertEqual(game.player['hp'], hp - damage)
        self.assertEqual(game.enemies[0]['intent']['action'], 'stunned')
        game = FloorDungeon.restore(game.dump())
        turn = game.enemies[0]['phase']
        go(game, 'charge')
        self.assertEqual((game.player['hp'], game.enemies[0]['phase']), (hp - damage, turn))
        self.assertEqual(game.enemies[0]['intent']['action'], 'melee')
        self.assertNotIn('stunned', game.enemies[0])

    def test_stagger_ignores_follow_up_beams_and_a_gap_restarts_progress(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['double', 'parallel']
        game.inscriptions[game.weapon] = 'stagger'
        target = fixture.enemy(game, 4, 5, hp=20)
        side = fixture.enemy(game, 4, 6, hp=20)
        go(game, 'wave', 'right')
        self.assertEqual((target['hp'], target['stagger_hit_turn']), (11, 1))
        self.assertNotIn('stunned', target)
        self.assertNotIn('stagger_hit_turn', side)
        go(game, 'guard')
        self.assertFalse(game.state()['enemies'][0]['stun_marked'])
        for enemy in game.enemies:
            enemy['intent'] = dict(action='wait', cells=[])
        go(game, 'wave', 'right')
        self.assertEqual(target['stagger_hit_turn'], 3)
        self.assertNotIn('stunned', target)

    def test_range_break_shortens_a_charged_beam_to_zero_and_preserves_recovery(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'range_break'
        fixture.enemy(game, 4, 5, kind='siegeeye', hp=12,
                      intent=dict(action='windup', cells=[], warning=[[3, 5]], direction='left'))
        self.assertIn('中断 · siegeeye下一发射程 −1', game.preview_details('wave', 'right')['events'])
        go(game, 'wave', 'right')
        game = FloorDungeon.restore(game.dump())
        eye = game.enemies[0]
        intent = game.state()['enemies'][0]['intent']
        self.assertEqual((intent['action'], intent['range_limit'], intent['cells']), ('special_wave', 0, []))
        self.assertNotIn([3, 5], game.state()['dangerCells'])
        phase = eye['phase']
        go(game, 'charge')
        self.assertEqual(game.player['hp'], 20)
        self.assertEqual(eye['phase'], phase + 1)
        self.assertTrue(eye['recovering'])
        self.assertNotIn('range_penalty', eye)
        self.assertTrue(any(effect['kind'] == 'laser' for effect in game.effects))

    def test_range_break_trims_fan_depth_or_outer_sweep_cells(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        enemy = fixture.enemy(game, 5, 5, hp=6, range_penalty=1,
                              intent=dict(action='special_wave', label='扇波', direction='left', weapon='fan',
                                          cells=[[4, 5], [4, 4], [4, 6], [3, 4], [3, 5], [3, 6]]))
        self.assertEqual(game.enemy_attack_intent(enemy)['cells'], [[4, 5], [4, 4], [4, 6]])
        enemy['intent'] = dict(action='area', label='横扫', sweep='横扫', cells=[[2, 5], [3, 5], [4, 5]])
        self.assertEqual(game.enemy_attack_intent(enemy)['cells'], [[3, 5], [4, 5]])

    @patch.dict(WEAPON_DAMAGE, straight=2)
    def test_shield_erosion_applies_and_corroded_guard_persists_after_full_block(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'shield_erosion'
        enemy = fixture.enemy(game, 4, 5, kind='shield', hp=6, intent=dict(action='guard', cells=[]))
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['hits'][0]['damage'], 0)
        self.assertIn('蚀盾 · shield防御 −1', preview['events'])
        self.assertEqual(game.enemy_defense(enemy), 2)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['defense_lost']), (6, 1))
        game = FloorDungeon.restore(game.dump())
        enemy = game.enemies[0]
        enemy['intent'] = dict(action='guard', cells=[])
        self.assertEqual(game.state()['enemies'][0]['defense'], 1)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['defense_lost']), (5, 2))
        enemy['intent'] = dict(action='guard', cells=[])
        self.assertEqual(game.state()['enemies'][0]['defense'], 0)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['defense_lost']), (3, 2))
        self.assertFalse(any(effect['kind'] == 'defense_loss' for effect in game.effects))

    def test_shield_erosion_follows_intercepted_main_beam_and_skips_parallel(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['parallel']
        game.inscriptions[game.weapon] = 'shield_erosion'
        ally = fixture.enemy(game, 5, 5, hp=6)
        escort = fixture.enemy(game, 5, 6, kind='escort', hp=6)
        side = fixture.enemy(game, 4, 6, kind='shield', hp=6, home=0,
                             intent=dict(action='guard', cells=[]))
        go(game, 'wave', 'right')
        self.assertEqual((ally['hp'], escort['hp'], side['hp']), (6, 2, 3))
        self.assertEqual(escort['defense_lost'], 1)
        self.assertNotIn('defense_lost', side)

    def test_point_blank_rune_only_boosts_adjacent_main_beam(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'lance'
        game.inscriptions[game.weapon] = 'point_blank'
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.rune, 'point_blank')
        near = fixture.enemy(game, 4, 5, kind='shield', hp=12, intent=dict(action='guard', cells=[]))
        far = fixture.enemy(game, 6, 5, hp=12)
        preview = game.preview_details('wave', 'right')
        self.assertEqual([hit['damage'] for hit in preview['hits']], [7, 6])
        self.assertIn('近战 · shield受到贴身增伤', preview['events'])
        go(game, 'wave', 'right')
        self.assertEqual((near['hp'], far['hp']), (5, 6))

    def test_point_blank_rune_rounds_up_heavy_damage_and_skips_side_beams(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['heavy', 'parallel']
        game.inscriptions[game.weapon] = 'point_blank'
        near = fixture.enemy(game, 4, 5, hp=20)
        side = fixture.enemy(game, 4, 6, hp=20)
        go(game, 'heavy', 'right')
        self.assertEqual((near['hp'], side['hp']), (3, 10))

    def test_classes_own_distinct_weapons_and_colors(self):
        colors = set()
        for hero in CLASSES:
            game = FloorDungeon(0, hero)
            restored = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
            self.assertEqual((restored.hero_class, restored.weapon), (hero, hero))
            colors.add(restored.state()['heroColor'])
            with self.assertRaises(ValueError):
                go(restored, 'equip', choice='fan')
        self.assertEqual(len(colors), len(CLASSES))

    def test_old_save_keeps_weapon_and_closes_past_talent_windows(self):
        game = FloorDungeon(0)
        go(game, 'equip', choice='return')
        saved = game.dump()
        saved.pop('talent_milestones')
        saved.pop('bag_relics')
        saved['talents'] = ['reserve']
        game = FloorDungeon.restore(saved)
        self.assertEqual(game.weapon, 'return')
        self.assertIsNone(game.hero_class)
        self.assertIsNone(game.talent_choice)
        self.assertEqual(game.cap, 4)
        with self.assertRaises(ValueError):
            go(game, 'choose_talents', choice=['reach', 'brace'])

    def test_restore_withdrawn_build_keeps_normal_equipment_and_pending_supplies(self):
        game = FloorDungeon(0, 'return')
        saved = game.dump()
        x, y = game.player['x'], game.player['y']
        saved.update(
            owned_emitters=['tide_return'], fitted_emitters={'return': 'tide_return'},
            blessing='borrow_ground', borrow_cell=[x + 1, y],
            rune_shards=2, inscriptions={'return': 'pull', 'fan': 'conduct', 'straight': 'shatter'},
            returning=[dict(owner='hero', cells=[[x + 1, y]], damage=1, pierce=1,
                            retarget=True, return_to=[x, y], rune='pull')],
            choices=[option for option in game.supply_options() if not option.get('equipment')] + [
                dict(id='tide_return', supply=True, rewardType='emitter'),
                dict(id='borrow_ground', supply=True, rewardType='blessing'),
            ],
        )
        saved['talent_milestones'] = [1]
        saved.pop('dropped_runes')
        saved['features'].append(dict(id='box', kind='supply_choice', used=False, x=x, y=y))
        restored = FloorDungeon.restore(json.loads(json.dumps(saved)))
        state = restored.state()
        self.assertEqual((state['weapon'], restored.inscriptions), ('return', {'straight': 'shatter'}))
        self.assertEqual(len(state['groundRunes']), 3)
        self.assertTrue(any(f['kind'] == 'light_wisp' and f['id'].startswith('legacy-rune-')
                            for f in restored.features))
        self.assertEqual(len(set(restored.dropped_runes)), len(restored.dropped_runes))
        self.assertNotIn('shatter', {f['rune'] for f in restored.ground_runes_here()})
        self.assertEqual([choice['id'] for choice in state['choices']], ['smoke', 'lure'])
        self.assertEqual(restored.returning, [dict(owner='hero', cells=[[x + 1, y]], damage=1, pierce=1)])
        self.assertNotIn('blessing', restored.dump())
        self.assertNotIn('fitted_emitters', restored.dump())
        go(restored, 'choose', choice='lure')
        self.assertIn('lure', restored.inventory)
        self.assertEqual(FloorDungeon.restore(restored.dump()).ground_runes_here(),
                         restored.ground_runes_here())

    def test_talent_windows_block_actions_and_only_resolve_once(self):
        game = FloorDungeon(0, 'straight')
        for depth, selection in ((1, ['reach']),
                                 (6, ['focus']),
                                 (11, ['through'])):
            game.depth = depth
            game.enter_room()
            game = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
            self.assertEqual(game.talent_choice['depth'], depth)
            with self.assertRaises(ValueError):
                go(game, 'charge')
            with self.assertRaises(ValueError):
                go(game, 'choose_talents', choice=[selection[0], selection[0]])
            turn = game.turn
            go(game, 'choose_talents', choice=selection)
            self.assertEqual(game.turn, turn)
            self.assertIsNone(game.talent_choice)
            game.enter_room()
            self.assertIsNone(game.talent_choice)
            with self.assertRaises(ValueError):
                go(game, 'choose_talents', choice=selection)
        self.assertEqual(len(game.talents), 3)

    def test_talent_preview_matches_character_and_does_not_change_state(self):
        for weapon, talent, expected in (('fan', 'through', (7, 8)),
                                          ('lance', 'through', (8, 10)),
                                          ('return', 'undertow', (7, 9))):
            with self.subTest(weapon=weapon, talent=talent):
                game = FloorDungeon(0, weapon)
                game.depth = 11
                game.enter_room()
                before = game.dump()
                option = next(option for option in game.state()['talentChoice']['options'] if option['id'] == talent)
                preview = option['preview']
                self.assertEqual((preview['before'], preview['after']), expected)
                self.assertEqual(game.dump(), before)
                go(game, 'choose_talents', choice=[talent])
                actual = (game.return_damage(game.wave_damage_before_defense('wave')) if talent == 'undertow'
                          else game.state()['waveStats']['damage'])
                self.assertEqual(preview['after'], actual)
        game = FloorDungeon(0, 'straight')
        self.assertEqual(game.talent_preview('economy')['after'], 2)
        self.assertIn('回音刻印', game.talent_preview('undertow')['note'])

    def test_bag_capacity_preserves_overflow_pickups_and_relic_expands(self):
        game = FloorDungeon(0)
        self.assertEqual(game.bag_capacity, 8)
        game.inventory = ['ankh'] * 7
        cache = next(f for f in game.features if f['kind'] == 'cache')
        cache['remaining_items'] = ['smoke', 'lure']  # legacy two-item cache
        game.player.update(x=cache['x'], y=cache['y'])
        game.finish_action()
        self.assertEqual(game.inventory, ['ankh'] * 7 + ['smoke'])
        self.assertEqual(cache['kind'], 'lure_cache')
        self.assertFalse(cache['used'])
        go(game, 'drop', choice='ankh')
        self.assertEqual(game.inventory, ['ankh'] * 6 + ['smoke'])
        go(game, 'pickup', choice=cache['id'])
        self.assertEqual(game.inventory, ['ankh'] * 6 + ['smoke', 'lure'])
        game.depth = 5
        game.enter_room()
        game.enemies = []
        game.finish_action()
        self.assertEqual(game.bag_capacity, 10)
        game.finish_action()
        game = FloorDungeon.restore(json.loads(json.dumps(game.dump())))
        self.assertEqual(game.bag_capacity, 10)
        self.assertEqual(len(game.inventory), 8)

    def test_weapon_upgrade_and_shatter_change_preview_and_real_hit(self):
        arena = test_mechanics.ExpeditionMechanicsTests()
        game = arena.arena()
        game.forge_cores = 2
        go(game, 'forge')
        go(game, 'forge')
        game.inscriptions[game.weapon] = 'shatter'
        enemy = arena.enemy(game, 8, 5, hp=11, intent=dict(action='guard', cells=[]))
        self.assertEqual(game.state()['waveStats']['range'], 5)
        self.assertEqual(game.preview('wave', 'right'), [{'name': 'ram', 'damage': 9}])
        go(game, 'wave', 'right')
        self.assertEqual(enemy['hp'], 2)

    def test_forge_preview_uses_current_mode_and_matches_upgrade(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.forge_cores = 2
        game.mode = 'power'
        game.upgrades = ['heavy']
        snapshot = game.dump()
        forge = game.state()['growth']['forge']
        self.assertEqual([(s['before'], s['after']) for s in forge['stats']], [(9, 12), (14, 17)])
        self.assertEqual(game.dump(), snapshot)
        go(game, 'forge')
        self.assertEqual(game.state()['waveStats']['damage'], forge['stats'][0]['after'])
        reach = game.state()['growth']['forge']
        self.assertEqual((reach['stats'][0]['before'], reach['stats'][0]['after']), (2, 2))
        self.assertIn('基础射程 +1', reach['note'])
        turn = game.turn
        go(game, 'forge')
        self.assertEqual(game.state()['waveStats']['range'], reach['stats'][0]['after'])
        self.assertEqual((game.forge_cores, game.turn), (0, turn))
        self.assertEqual(game.state()['growth']['forge']['blocked'], '缺少锻造核心。')

    def test_frost_prevents_enemy_move_and_echo_queues_return(self):
        arena = test_mechanics.ExpeditionMechanicsTests()
        game = arena.arena()
        game.inscriptions[game.weapon] = 'frost'
        enemy = arena.enemy(game, 6, 5, hp=10, last_seen=[3, 5])
        go(game, 'wave', 'right')
        self.assertEqual(enemy['intent']['action'], 'wait')
        go(game, 'guard')
        self.assertEqual((enemy['x'], enemy['y']), (6, 5))
        game = arena.arena()
        game.inscriptions[game.weapon] = 'echo'
        go(game, 'wave', 'right')
        self.assertEqual(game.returning[0]['damage'], 3)
        self.assertEqual(game.returning[0]['cells'], [[7,5],[6,5],[5,5],[4,5]])

    def test_heavy_discount_and_full_energy_bonus_are_applied(self):
        arena = test_mechanics.ExpeditionMechanicsTests()
        game = arena.arena()
        game.depth = 6
        game.upgrades = ['heavy']
        go(game, 'choose_talents', choice=['economy'])
        # Previously earned pairs from old saves still apply.
        game.talents.append('focus')
        enemy = arena.enemy(game, 5, 5, hp=16)
        self.assertEqual(game.preview('heavy', 'right'), [{'name': 'ram', 'damage': 13}])
        go(game, 'heavy', 'right')
        self.assertEqual((game.player['energy'], enemy['hp']), (1, 3))
