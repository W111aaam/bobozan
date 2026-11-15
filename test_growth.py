import json
import unittest

from floor import FloorDungeon
from growth import CLASSES, RUNES
from test_floor import go
import test_mechanics


class GrowthTests(unittest.TestCase):
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

    def test_conduction_deals_equal_damage_in_connected_unfrozen_water(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'conduction'
        game.upgrades = ['heavy']
        game.terrain.extend(dict(x=x, y=y, kind='water')
                            for x, y in ((4, 5), (4, 6), (4, 7), (4, 9), (6, 5)))
        game.terrain.append(dict(x=4, y=8, kind='water', ice_until=game.turn + 3))
        source = fixture.enemy(game, 4, 5, kind='shield', hp=6, intent=dict(action='guard', cells=[]))
        ally = fixture.enemy(game, 4, 7, kind='shield', hp=6, intent=dict(action='guard', cells=[]))
        distant = fixture.enemy(game, 4, 9, hp=6)
        separate = fixture.enemy(game, 6, 5, hp=6)
        preview = game.preview_details('heavy', 'right')
        self.assertEqual([hit['damage'] for hit in preview['hits']], [1, 1])
        self.assertEqual(preview['conduction'], [[4, 5], [4, 6], [4, 7]])
        go(game, 'heavy', 'right')
        self.assertEqual((source['hp'], ally['hp'], distant['hp'], separate['hp']), (5, 5, 6, 6))

    def test_dry_conduction_has_six_tile_radius_and_hides_unseen_targets(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'conduction'
        source = fixture.enemy(game, 4, 5, hp=6)
        near = fixture.enemy(game, 4, 6, hp=6)
        edge = fixture.enemy(game, 10, 5, hp=6, name='雾后目标')
        outside = fixture.enemy(game, 10, 6, hp=6)
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['conduction'], [[4, 6]])
        self.assertNotIn('雾后目标', str(preview))
        go(game, 'wave', 'right')
        self.assertEqual((source['hp'], near['hp'], edge['hp'], outside['hp']), (5, 5, 5, 6))

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
        source = fixture.enemy(game, 4, 5, hp=6)
        blocked = fixture.enemy(game, 4, 7, hp=6)
        recipient = fixture.enemy(game, 6, 4, hp=6)
        other = fixture.enemy(game, 7, 3, hp=6)
        game.walls.append([4, 6])
        game._wall_cells.add((4, 6))
        game.update_visibility()
        preview = game.preview_details('wave', 'right')
        self.assertEqual([hit['damage'] for hit in preview['hits']], [2, 1])
        self.assertEqual(len(preview['refraction']), 1)
        self.assertEqual(preview['refraction'][0][0], [4, 5])
        self.assertEqual(preview['refraction'][0][-1], [6, 4])
        go(game, 'wave', 'right')
        self.assertEqual((source['hp'], blocked['hp'], recipient['hp'], other['hp']), (4, 6, 5, 6))
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
        self.assertEqual((far['hp'], outside['hp']), (5, 6))

    def test_stagger_uses_consecutive_turns_and_skips_exactly_the_next_action(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'stagger'
        fixture.enemy(game, 4, 5, hp=7, last_seen=[3, 5],
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
        target = fixture.enemy(game, 4, 5, hp=8)
        side = fixture.enemy(game, 4, 6, hp=8)
        go(game, 'wave', 'right')
        self.assertEqual((target['hp'], target['stagger_hit_turn']), (6, 1))
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
        fixture.enemy(game, 4, 5, kind='siegeeye', hp=6,
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
        self.assertEqual(game.player['hp'], 5)
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

    def test_shield_erosion_applies_and_corroded_guard_persists_after_full_block(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.inscriptions[game.weapon] = 'shield_erosion'
        enemy = fixture.enemy(game, 4, 5, kind='shield', hp=6, intent=dict(action='guard', cells=[]))
        preview = game.preview_details('wave', 'right')
        self.assertEqual(preview['hits'][0]['damage'], 0)
        self.assertIn('蚀盾 · shield防御 −1', preview['events'])
        self.assertEqual(game.enemy_defense(enemy), 1)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['defense_lost']), (6, 1))
        game = FloorDungeon.restore(game.dump())
        enemy = game.enemies[0]
        enemy['intent'] = dict(action='guard', cells=[])
        self.assertEqual(game.state()['enemies'][0]['defense'], 0)
        go(game, 'wave', 'right')
        self.assertEqual((enemy['hp'], enemy['defense_lost']), (5, 1))
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
        self.assertEqual((ally['hp'], escort['hp'], side['hp']), (6, 6, 6))
        self.assertEqual(escort['defense_lost'], 1)
        self.assertNotIn('defense_lost', side)

    def test_point_blank_rune_only_boosts_adjacent_main_beam(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.weapon = 'lance'
        game.inscriptions[game.weapon] = 'point_blank'
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.rune, 'point_blank')
        near = fixture.enemy(game, 4, 5, kind='shield', hp=6, intent=dict(action='guard', cells=[]))
        far = fixture.enemy(game, 6, 5, hp=6)
        preview = game.preview_details('wave', 'right')
        self.assertEqual([hit['damage'] for hit in preview['hits']], [1, 1])
        self.assertIn('近战 · shield受到贴身增伤', preview['events'])
        go(game, 'wave', 'right')
        self.assertEqual((near['hp'], far['hp']), (5, 5))

    def test_point_blank_rune_rounds_up_heavy_damage_and_skips_side_beams(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        game.upgrades = ['heavy', 'parallel']
        game.inscriptions[game.weapon] = 'point_blank'
        near = fixture.enemy(game, 4, 5, hp=6)
        side = fixture.enemy(game, 4, 6, hp=6)
        go(game, 'heavy', 'right')
        self.assertEqual((near['hp'], side['hp']), (3, 5))

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
            choices=game.supply_options() + [
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
        self.assertEqual(len(state['groundRunes']), 4)
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
        for weapon, talent, expected in (('fan', 'through', (2, 3)),
                                          ('lance', 'through', (2, 3)),
                                          ('return', 'undertow', (1, 2))):
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
                          else game.state()['waveStats']['range' if weapon == 'fan' else 'pierce'])
                self.assertEqual(preview['after'], actual)
        game = FloorDungeon(0, 'straight')
        self.assertIn('取得重波遗物', game.talent_preview('economy')['note'])
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
        enemy = arena.enemy(game, 8, 5, hp=4, intent=dict(action='guard', cells=[]))
        self.assertEqual(game.state()['waveStats']['range'], 5)
        self.assertEqual(game.preview('wave', 'right'), [{'name': 'ram', 'damage': 2}])
        go(game, 'wave', 'right')
        self.assertEqual(enemy['hp'], 2)

    def test_forge_preview_uses_current_mode_and_matches_upgrade(self):
        game = test_mechanics.ExpeditionMechanicsTests().arena()
        game.forge_cores = 2
        game.mode = 'power'
        game.upgrades = ['heavy']
        snapshot = game.dump()
        forge = game.state()['growth']['forge']
        self.assertEqual([(s['before'], s['after']) for s in forge['stats']], [(2, 3), (3, 4)])
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
        enemy = arena.enemy(game, 6, 5, hp=4, last_seen=[3, 5])
        go(game, 'wave', 'right')
        self.assertEqual(enemy['intent']['action'], 'wait')
        go(game, 'guard')
        self.assertEqual((enemy['x'], enemy['y']), (6, 5))
        game = arena.arena()
        game.inscriptions[game.weapon] = 'echo'
        go(game, 'wave', 'right')
        self.assertEqual(game.returning[0]['damage'], 1)
        self.assertEqual(game.returning[0]['cells'], [[7,5],[6,5],[5,5],[4,5]])

    def test_heavy_discount_and_full_energy_bonus_are_applied(self):
        arena = test_mechanics.ExpeditionMechanicsTests()
        game = arena.arena()
        game.depth = 6
        game.upgrades = ['heavy']
        go(game, 'choose_talents', choice=['economy'])
        # Previously earned pairs from old saves still apply.
        game.talents.append('focus')
        enemy = arena.enemy(game, 5, 5, hp=6)
        self.assertEqual(game.preview('heavy', 'right'), [{'name': 'ram', 'damage': 3}])
        go(game, 'heavy', 'right')
        self.assertEqual((game.player['energy'], enemy['hp']), (1, 3))
