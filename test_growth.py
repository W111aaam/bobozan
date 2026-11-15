import json
import unittest

from floor import FloorDungeon
from growth import CLASSES
from test_floor import go
import test_mechanics


class GrowthTests(unittest.TestCase):
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
        saved['features'].append(dict(id='box', kind='supply_choice', used=False, x=x, y=y))
        restored = FloorDungeon.restore(json.loads(json.dumps(saved)))
        state = restored.state()
        self.assertEqual((state['weapon'], restored.inscriptions), ('return', {'straight': 'shatter'}))
        self.assertEqual(state['growth']['shards'], 4)
        self.assertEqual([choice['id'] for choice in state['choices']], ['smoke', 'lure'])
        self.assertEqual(restored.returning, [dict(owner='hero', cells=[[x + 1, y]], damage=1, pierce=1)])
        self.assertNotIn('blessing', restored.dump())
        self.assertNotIn('fitted_emitters', restored.dump())
        go(restored, 'choose', choice='lure')
        self.assertIn('lure', restored.inventory)
        self.assertEqual(FloorDungeon.restore(restored.dump()).rune_shards, 4)

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
        game.forge_cores, game.rune_shards = 2, 1
        go(game, 'forge')
        go(game, 'forge')
        go(game, 'etch', choice='shatter')
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
        game.rune_shards = 1
        go(game, 'etch', choice='frost')
        enemy = arena.enemy(game, 6, 5, hp=4, last_seen=[3, 5])
        go(game, 'wave', 'right')
        self.assertEqual(enemy['intent']['action'], 'wait')
        go(game, 'guard')
        self.assertEqual((enemy['x'], enemy['y']), (6, 5))
        game = arena.arena()
        game.rune_shards = 1
        go(game, 'etch', choice='echo')
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
