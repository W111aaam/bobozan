import unittest

from dungeon import DIRS
from floor import FloorDungeon
from test_floor import go
import test_mechanics


class WaveRelicTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_mechanics.ExpeditionMechanicsTests()
        self.game = self.fixture.arena()

    def test_defense_forecast_compares_guard_and_charge_without_spending_a_turn(self):
        game = self.game
        game.player['energy'] = 1
        self.fixture.enemy(game, 4, 5, intent=dict(action='melee', cells=[[3, 5]], damage=5))
        self.fixture.enemy(game, 2, 5, intent=dict(action='wave', cells=[[3, 5]],
                                                rune='shatter', damage=1))
        before = game.dump()
        results = [game.preview_details(action, None) for action in ('guard', 'charge')]
        self.assertEqual([(result['blocked'], result['damage']) for result in results], [(4, 2), (0, 6)])
        self.assertEqual(game.dump(), before)
        go(game, 'guard')
        self.assertEqual(game.player['hp'], 18)

    def test_defense_forecast_does_not_expose_hidden_damage_or_guard_budget(self):
        game = self.game
        self.fixture.enemy(game, 11, 5, name='隐藏敌人', intent=dict(action='area', cells=[[3, 5]], damage=3))
        self.fixture.enemy(game, 4, 5, intent=dict(action='melee', cells=[[3, 5]], damage=1))
        preview = game.preview_details('guard', None)
        self.assertEqual((preview['blocked'], preview['damage']), (1, 0))
        self.assertNotIn('隐藏敌人', str(preview))
        self.assertEqual(preview['received'], [])

    def test_defense_forecast_tests_step_against_the_resolved_attack_and_contested_moves(self):
        game = self.game
        self.fixture.enemy(game, 4, 5, intent=dict(action='melee', cells=[[3, 5]], damage=2))
        self.fixture.enemy(game, 2, 4, intent=dict(action='move', target=[3, 4], cells=[]))
        before = game.dump()
        up = game.preview_details('move', 'up')
        down = game.preview_details('move', 'down')
        self.assertEqual((up['stepOutcome'], up['damage']), ('blocked', 2))
        self.assertEqual((down['stepOutcome'], down['damage']), ('moved', 0))
        self.assertEqual(game.dump(), before)
        go(game, 'move', 'down')
        self.assertEqual((game.player['x'], game.player['y'], game.player['hp']), (3, 6, 20))

    def test_step_forecast_reports_known_holes_without_revealing_hidden_traps(self):
        game = self.game
        game.terrain.extend([
            dict(x=3, y=4, kind='fragile', stage=1),
            dict(x=3, y=6, kind='trap', mechanism='fall', armed=True, hidden=True),
        ])
        up = game.preview_details('move', 'up')
        down = game.preview_details('move', 'down')
        self.assertEqual((up['stepOutcome'], down['stepOutcome']), ('fall', 'moved'))
        self.assertEqual((game.depth, game.turn), (1, 0))

    def test_anchor_chain_reward_pulls_enemy_for_one_turn_and_recharges_next_floor(self):
        game = self.game
        game.upgrades = [key for key in game.upgrade_catalog if key != 'anchor_chain']
        game.make_choices(3)
        self.assertEqual([choice['id'] for choice in game.choices], ['anchor_chain'])
        go(game, 'choose', choice='anchor_chain')
        enemy = self.fixture.enemy(game, 6, 5, intent=dict(action='move', target=[6, 4], cells=[]))
        energy, turn = game.player['energy'], game.turn
        preview = game.state()['anchorChain']['targets']['6,5']
        self.assertEqual(preview, dict(landing=[5, 5], path=[[4, 5], [5, 5], [6, 5]], pullEnemy=True))
        go(game, 'anchor_chain', [6, 5])
        self.assertEqual((enemy['x'], enemy['y']), (5, 5))
        self.assertEqual((game.turn, game.player['energy']), (turn + 1, energy))
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.state()['anchorChain'], dict(charges=0, targets={}))
        with self.assertRaisesRegex(ValueError, '充能已用尽'):
            go(game, 'anchor_chain', [3, 7])
        game.exit = [3, 5]
        go(game, 'exit')
        self.assertEqual(game.depth, 2)
        self.assertEqual(game.state()['anchorChain']['charges'], 1)

    def test_anchor_chain_uses_safe_path_and_repositions_before_locked_attack(self):
        game = self.game
        game.upgrades.append('anchor_chain')
        enemy = self.fixture.enemy(game, 6, 5, intent=dict(action='melee', cells=[[3, 5]]))
        game.terrain += [dict(x=3, y=4, kind='rubble'), dict(x=4, y=5, kind='fragile', stage=1)]
        game.update_visibility()
        targets = game.state()['anchorChain']['targets']
        self.assertNotIn('7,5', targets)
        self.assertNotIn('4,5', targets)
        self.assertNotIn('4,4', targets)
        snapshot = game.dump()
        with self.assertRaisesRegex(ValueError, '请选择四格内'):
            go(game, 'anchor_chain', [4, 4])
        self.assertEqual(game.dump(), snapshot)
        go(game, 'anchor_chain', [3, 8])
        self.assertEqual((game.player['x'], game.player['y'], game.player['hp']), (3, 8, 20))
        self.assertEqual(enemy['hp'], 3)
        effect = next(effect for effect in game.effects if effect['kind'] == 'anchor_chain')
        self.assertEqual(effect['cells'], [[3, 6], [3, 7], [3, 8]])

    def test_stored_charge_fills_current_cap_and_spends_an_enemy_turn(self):
        game = self.game
        game.upgrades = [key for key in game.upgrade_catalog if key != 'stored_charge']
        game.talents = ['reserve']
        game.make_choices(3)
        self.assertEqual([choice['id'] for choice in game.choices], ['stored_charge'])
        self.assertEqual(game.state()['choices'][0]['preview']['stats'],
                         [dict(label='补能目标', after='5 能量')])
        go(game, 'choose', choice='stored_charge')
        enemy = self.fixture.enemy(game, 4, 5, intent=dict(action='melee', cells=[[3, 5]]))
        game.player['energy'] = 0
        turn, hp, echo = game.turn, game.player['hp'], game.echo_charges
        go(game, 'stored_charge')
        self.assertEqual((game.player['energy'], game.player['hp'], game.turn), (5, hp - 1, turn + 1))
        self.assertEqual((enemy['phase'], game.echo_charges), (1, echo))
        effect = next(effect for effect in game.state()['effects'] if effect['kind'] == 'energy_gain')
        self.assertEqual((effect['amount'], effect['source']), (5, '预藏'))

    def test_stored_charge_keeps_full_energy_use_and_saves_each_relic_independently(self):
        game = self.game
        game.upgrades = ['stored_charge', 'anchor_chain']
        saved = game.dump()
        saved.pop('relic_used_depth')
        saved['anchor_chain_used_depth'] = 1
        game = FloorDungeon.restore(saved)
        before = game.dump()
        with self.assertRaisesRegex(ValueError, '能量已满'):
            go(game, 'stored_charge')
        self.assertEqual(game.dump(), before)
        self.assertEqual((game.state()['storedCharge'], game.state()['anchorChain']['charges']), (1, 0))
        game.player['energy'] = 1
        go(game, 'stored_charge')
        game = FloorDungeon.restore(game.dump())
        game.player['energy'] = 1
        with self.assertRaisesRegex(ValueError, '充能已用尽'):
            go(game, 'stored_charge')
        game.exit = [3, 5]
        go(game, 'exit')
        self.assertEqual(game.depth, 2)
        self.assertEqual((game.state()['storedCharge'], game.state()['anchorChain']['charges']), (1, 1))

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

    def test_relic_choice_previews_use_current_build_without_mutating_it(self):
        game = FloorDungeon(0, 'straight')
        game.talents = ['reserve', 'economy']
        game.mode = 'power'
        game.talent_milestones = [1]
        game.upgrades = ['echo']
        game.choices = [dict(id=key, name=game.upgrade_catalog[key][0],
                             description=game.upgrade_catalog[key][1])
                        for key in ('bag', 'pierce', 'reflect')]
        saved = game.dump()
        choices = {choice['id']: choice['preview'] for choice in game.state()['choices']}
        self.assertEqual(game.dump(), saved)
        self.assertEqual(choices['bag']['stats'][0], dict(label='能量上限', before=4, after=5))
        self.assertEqual(choices['bag']['combos'][0]['missing'], [])
        self.assertEqual(choices['pierce']['combos'][0]['missing'], [])
        self.assertEqual(choices['reflect']['stats'], [dict(label='反弹耗能', after='1 能量')])
        go(game, 'choose', choice='bag')
        self.assertEqual(game.cap, choices['bag']['stats'][0]['after'])
        self.assertTrue(next(build for build in game.builds() if build['name'] == '蓄能')['active'])

    def test_double_passes_defeated_enemy_and_parallel_hits_side_lane(self):
        game = self.game
        game.upgrades = ['double', 'parallel', 'burn']
        self.fixture.enemy(game, 4, 5, hp=1)
        second = self.fixture.enemy(game, 6, 5, hp=9)
        side = self.fixture.enemy(game, 5, 6, hp=9)
        go(game, 'wave', 'right')
        self.assertEqual(game.player['energy'], 2)
        self.assertEqual((second['hp'], side['hp']), (6, 4))
        self.assertNotIn('burning', second)
        self.assertNotIn('burning', side)

    def test_flank_array_requires_parallel_and_previews_three_lanes(self):
        game = self.game
        game.upgrades = [key for key in game.upgrade_catalog if key not in ('parallel', 'flank_array')]
        game.make_choices(3)
        self.assertEqual([choice['id'] for choice in game.choices], ['parallel'])
        go(game, 'choose', choice='parallel')
        game.make_choices(3)
        choice, = game.state()['choices']
        self.assertEqual(choice['id'], 'flank_array')
        self.assertEqual(choice['preview']['stats'], [
            dict(label='发射行数上限', before='2 行', after='3 行'),
        ])
        go(game, 'choose', choice='flank_array')
        self.assertIn('flank_array', game.upgrades)

    def test_flank_array_shoots_both_sides_and_checks_entry_to_each_lane(self):
        for blocked in (None, 4, 6):
            with self.subTest(blocked=blocked):
                game = self.fixture.arena()
                game.upgrades = ['parallel', 'flank_array']
                if blocked is not None:
                    game.walls = [[3, blocked]]
                    game._wall_cells = {(3, blocked)}
                foes = {y: self.fixture.enemy(game, 5, y, hp=10, name=str(y),
                                              intent=dict(action='wait', cells=[]))
                        for y in (4, 5, 6)}
                expected = [[5, y] for y in foes if y != blocked]
                preview = game.preview_details('wave', 'right')
                self.assertEqual([cell for cell in expected if cell in preview['cells']], expected)
                self.assertEqual({hit['name'] for hit in preview['hits']},
                                 {str(y) for y in foes if y != blocked})
                go(game, 'wave', 'right')
                self.assertEqual(game.player['energy'], 2)
                self.assertEqual({y: enemy['hp'] for y, enemy in foes.items()},
                                 {y: 10 if y == blocked else 4 if y == 5 else 5 for y in foes})

    def test_impact_pushes_enemy_into_fragile_floor(self):
        game = self.game
        game.upgrades = ['impact']
        game.terrain = [dict(x=6, y=5, kind='fragile', stage=1)]
        enemy = self.fixture.enemy(game, 5, 5, hp=10)
        preview = game.preview_details('wave', 'right')
        self.assertIn('ram被推入深渊', preview['events'])
        go(game, 'wave', 'right')
        self.assertNotIn(enemy, game.enemies)
        self.assertEqual(game.tile_at([6, 5])['stage'], 2)

    def test_gate_shield_recharges_after_each_block_and_previews_its_real_landing(self):
        game = self.game
        game.upgrades = ['gate_shield', 'parallel']
        go(game, 'guard')
        self.assertFalse(game.state()['gateShieldReady'])
        attacker = self.fixture.enemy(game, 5, 5, hp=24,
                                      intent=dict(action='melee', cells=[[3, 5]]))
        self.fixture.enemy(game, 5, 6, hp=24)
        go(game, 'guard')
        self.assertTrue(game.state()['gateShieldReady'])
        game = FloorDungeon.restore(game.dump())
        for foe in game.enemies:
            foe['intent'] = dict(action='wait', cells=[])
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['knockback'], [[6, 5]])
        self.assertTrue(game.state()['gateShieldReady'])
        go(game, 'wave', 'right')
        first = next(foe for foe in game.enemies if foe['id'] == attacker['id'])
        self.assertEqual([first['x'], first['y']], preview['knockback'][0])
        self.assertFalse(game.state()['gateShieldReady'])
        first['intent'] = dict(action='melee', cells=[[3, 5]])
        go(game, 'guard')
        self.assertTrue(game.state()['gateShieldReady'])
        game.enemies = [first]
        first['intent'] = dict(action='wait', cells=[])
        go(game, 'wave', 'right')
        self.assertEqual(first['x'], 7)
        self.assertFalse(game.state()['gateShieldReady'])

    def test_gate_shield_misses_consume_charge_and_impact_does_not_stack(self):
        for impact in (False, True):
            with self.subTest(impact=impact):
                game = self.fixture.arena()
                game.upgrades = ['gate_shield', 'impact'] if impact else ['gate_shield']
                game.gate_shield_ready = True
                if impact:
                    target = self.fixture.enemy(game, 5, 5, hp=7)
                go(game, 'wave', 'right')
                self.assertFalse(game.state()['gateShieldReady'])
                if impact:
                    self.assertEqual(target['x'], 6)

    def test_mirror_chain_splits_actual_path_and_stops_each_branch_at_obstacles(self):
        for wall in (False, True):
            with self.subTest(wall=wall):
                game = self.fixture.arena()
                game.upgrades = ['mirror_chain']
                game.terrain = [dict(x=4, y=5, kind='mirror', slash=chr(92)),
                                dict(x=4, y=6, kind='mirror', slash='/')]
                if wall:
                    game.walls = [[2, 7]]
                    game._wall_cells = {(2, 7)}
                north = self.fixture.enemy(game, 2, 4, hp=4, name='北', intent=dict(action='wait', cells=[]))
                south = self.fixture.enemy(game, 2, 8, hp=4, name='南', intent=dict(action='wait', cells=[]))
                preview = game.preview_details('wave', 'right')
                self.assertIn('镜链 · 主束末端分裂', preview['events'])
                self.assertIn([2, 4], preview['cells'])
                self.assertEqual([2, 8] in preview['cells'], not wall)
                go(game, 'wave', 'right')
                self.assertEqual((north['hp'], south['hp']), (1, 4 if wall else 1))
                self.assertEqual(sum(fx['kind'] == 'mirror_split' for fx in game.effects), 1 if wall else 2)
                self.assertEqual(game.player['energy'], 2)

    def test_mirror_chain_needs_two_mirrors_before_the_main_beam_stops(self):
        game = self.game
        game.upgrades = ['mirror_chain', 'double']
        game.terrain = [dict(x=4, y=y, kind='mirror', slash=chr(92)) for y in (5, 7)]
        self.fixture.enemy(game, 4, 6, hp=1)
        go(game, 'wave', 'right')
        self.assertFalse(any(fx['kind'] == 'mirror_split' for fx in game.effects))

    def test_generated_store_has_a_four_cell_double_reflection(self):
        game = FloorDungeon(0)
        game.depth = 3
        game.enter_room()
        self.assertEqual(game.lock_style, 'store')
        mirrors = {(t['x'], t['y']) for t in game.terrain if t['kind'] == 'mirror'}
        origins = [([x - dx, y - dy], direction) for x, y in mirrors for direction, (dx, dy) in DIRS.items()]
        self.assertTrue(any(game.walkable(origin) and len(set(map(tuple, game.trace(origin, direction))) & mirrors) >= 2
                            for origin, direction in origins))

    def test_burn_ticks_for_two_later_actions(self):
        game = self.game
        game.upgrades = ['burn']
        enemy = self.fixture.enemy(game, 6, 5, hp=10)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['burning']), (4, 2))
        go(game, 'guard')
        self.assertEqual((enemy['hp'], enemy['burning']), (3, 1))
        go(game, 'guard')
        self.assertEqual((enemy['hp'], enemy['burning']), (2, 0))

    def test_shallow_water_extinguishes_existing_and_new_burns(self):
        game = self.game
        game.upgrades = ['burn', 'impact']
        enemy = self.fixture.enemy(game, 5, 5, hp=10)
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
        enemy = self.fixture.enemy(game, 6, 5, hp=18, last_seen=[3, 5])
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
        game.upgrades.append('reflect')
        self.fixture.enemy(game, 5, 5, intent=dict(action='wave', cells=[[4, 5], [3, 5]]))
        self.fixture.enemy(game, 12, 5, intent=dict(action='area', cells=[[3, 5]], damage=2))
        before = game.dump()
        wave = game.preview_details('wave', 'right')
        self.assertEqual(wave['received'], [dict(damage=1, name='ram')])
        self.assertEqual(wave['reflected'], 0)
        defense = game.preview_details('reflect', 'right')
        self.assertEqual(defense['received'], [])
        self.assertEqual(defense['reflected'], 1)
        self.assertEqual(defense['hitSources'], {'reflection': [{'name': 'ram', 'damage': 1}]})
        self.assertEqual(game.dump(), before)

    def test_preview_breaks_out_new_wave_return_and_ongoing_fire_damage(self):
        game = self.game
        target = self.fixture.enemy(game, 5, 5, name='目标', hp=11, burning=1)
        game.ground_fire = [dict(x=5, y=5, spread=0)]
        game.returning = [dict(owner='hero', cells=[[5, 5], [4, 5]], damage=1, pierce=1)]
        before = game.dump()
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['hitSources'], {
            source: [{'name': '目标', 'damage': 6 if source == 'wave' else 1}] for source in ('wave', 'return', 'burn', 'groundFire')
        })
        self.assertEqual(preview['hits'], [{'name': '目标', 'damage': 9}])
        self.assertNotIn('wave', game.preview_details('wave', 'left')['hitSources'])
        self.assertEqual(game.dump(), before)
        go(game, 'wave', 'right')
        self.assertEqual(target['hp'], 2)

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
        self.assertEqual((game.player['x'], game.player['y'], game.player['hp']), (7, 5, 18))
