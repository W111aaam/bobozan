import json
import unittest

from enemy_design import ENEMY_DESIGNS
from floor import FloorDungeon
from test_floor import go


class SideEncounterTests(unittest.TestCase):
    def arena(self):
        g = FloorDungeon(0)
        g.player.update(x=3, y=5, energy=2)
        g.enemies, g.doors, g.walls, g.terrain, g.features = [], [], [], [], []
        g._door_cells, g._wall_cells = set(), set()
        g.rooms_data = [dict(id=0, bounds=[0, 0, 10, 10], kind='entry', name='试验场', cleared=True)]
        g.locked = False
        g.update_visibility()
        return g

    def enemy(self, g, kind, x, y, **fields):
        name, _, hp, _ = ENEMY_DESIGNS[kind]
        e = dict(id=len(g.enemies), kind=kind, name=name, home=0, hp=hp, maxHp=hp,
                 x=x, y=y, energy=0, phase=0, last_seen=[g.player['x'],g.player['y']])
        g.init_side_enemy(e)
        e.update(fields)
        g.enemies.append(e)
        g.plan()
        return e

    def test_thief_can_be_blocked_and_energy_recovered(self):
        g = self.arena()
        e = self.enemy(g, 'sparkthief', 4, 5, hp=1)
        go(g, 'guard')
        self.assertFalse(e.get('stolen'))
        go(g, 'charge')
        self.assertEqual(g.player['energy'], 2)
        self.assertEqual(e['stolen'], 1)
        go(g, 'wave', 'right')
        go(g, 'move', 'right')
        self.assertEqual(g.player['energy'], 2)
        self.assertTrue(g.features[0]['used'])

    def test_chant_survives_save_but_can_be_occupied_or_interrupted(self):
        g = self.arena()
        self.enemy(g, 'bonesummoner', 5, 5)
        go(g, 'guard')
        saved = json.loads(json.dumps(g.dump()))
        for action, direction, expected in (('guard',None,1), ('move','right',0), ('wave','right',0)):
            copy = FloorDungeon.restore(saved)
            go(copy, action, direction)
            self.assertEqual(sum(e['kind']=='bonepuppet' for e in copy.enemies), expected)

    def test_hook_pulls_only_when_unblocked(self):
        for action, direction, x in (('guard',None,3), ('reflect','right',3), ('charge',None,4)):
            g = self.arena()
            self.enemy(g,'magnetguard',6,5,energy=1)
            go(g, action, direction)
            self.assertEqual(g.player['x'], x)

    def test_web_blocks_blink_and_can_be_cut(self):
        g = self.arena()
        e = self.enemy(g,'webspinner',6,5)
        go(g,'guard')
        self.assertEqual(g.tile_at([3,5])['kind'],'web')
        g.upgrades = ['pierce','blink']
        go(g,'wave','right')
        self.assertEqual(g.player['x'],3)
        go(g,'move','up')
        go(g,'wave','down')
        self.assertIsNone(g.tile_at([3,5]))

    def test_poison_ticks_once_and_guard_can_prevent_application(self):
        for first, expected in (('guard',5), ('charge',3)):
            g = self.arena()
            self.enemy(g,'webspinner',6,5,web_laid=True,energy=1)
            go(g, first)
            self.assertEqual(g.poisoned, first != 'guard')
            go(g,'move','up')
            self.assertEqual(g.player['hp'],expected)
            self.assertFalse(g.poisoned)

    def test_elemental_fire_frost_and_reflection(self):
        g = self.arena()
        g.terrain = [dict(x=5,y=6,kind='high_grass')]
        self.enemy(g,'elementcore',4,6,element='fire')
        go(g,'guard')
        self.assertEqual(g.tile_at([5,6])['kind'],'grass')
        self.assertEqual(g.state()['fireCells'], [[5, 6]])
        g = self.arena()
        self.enemy(g,'elementcore',5,5,element='frost')
        go(g,'guard')
        self.assertTrue(g.movement_locked())
        with self.assertRaises(ValueError):
            go(g,'move','up')
        go(g,'guard')
        self.assertFalse(g.movement_locked())
        g = self.arena()
        g.terrain = [dict(x=6,y=5,kind='mirror',slash='/')]
        # Rightbound spark turns up at the mirror and hits a target on its column.
        g.player.update(x=6,y=4)
        e = self.enemy(g,'elementcore',3,5,element='spark',energy=1)
        self.assertIn([6,4],e['intent']['cells'])

    def test_electric_wave_warns_and_conducts_only_through_connected_water(self):
        for action, expected_hp in [('charge', 4), ('guard', 5), ('move', 5)]:
            with self.subTest(action=action):
                g = self.arena()
                g.player.update(x=6, y=6)
                g.terrain = [dict(x=x, y=y, kind='water')
                             for x, y in [(6, 5), (6, 6), (7, 6), (8, 7)]]
                core = self.enemy(g, 'elementcore', 3, 5, element='spark', energy=1)
                g.update_visibility()
                self.assertNotIn([6, 6], core['intent']['cells'])
                self.assertIn([6, 6], g.state()['dangerCells'])
                self.assertNotIn([8, 7], core['intent']['water'])
                go(g, action, 'down' if action == 'move' else None)
                self.assertEqual(g.player['hp'], expected_hp)

    def test_frost_smoke_interrupts_water_conduction_and_ice_thaws_after_reload(self):
        g = self.arena()
        g.player.update(x=6, y=6)
        g.terrain = [dict(x=6, y=y, kind='water') for y in (5, 6, 7)]
        g.inventory = ['frost_smoke']
        self.enemy(g, 'elementcore', 3, 5, element='spark', energy=1)
        g.update_visibility()
        self.assertIn([6, 6], g.state()['dangerCells'])
        go(g, 'item', [6, 5], 'frost_smoke')
        self.assertEqual(g.player['hp'], 5)
        self.assertFalse(g.movement_locked())
        self.assertEqual(g.conducted_water([[6, 5]]), [])

        g = FloorDungeon.restore(json.loads(json.dumps(g.dump())))
        go(g, 'guard')
        self.assertEqual(g.conducted_water([[6, 5]]), [])
        go(g, 'guard')
        self.assertEqual(g.conducted_water([[6, 5]]), [[6, 5], [6, 6], [6, 7]])

    def test_burning_main_beam_melts_ice_before_enemy_electric_wave(self):
        g = self.arena()
        g.player.update(x=6, y=6)
        g.terrain = [dict(x=x, y=y, kind='water') for x, y in [(6,5), (7,5), (7,6), (6,6)]]
        self.enemy(g, 'elementcore', 3, 5, element='spark', energy=1)
        g.terrain.remove(g.tile_at([6, 5]))
        g.freeze_water([[7, 6]])
        self.assertNotIn([6, 6], g.conducted_water([[7, 5]]))
        g.upgrades = ['burn']
        g.update_visibility()
        before = g.dump()
        self.assertIn('将融化冰封浅水，恢复导电', g.preview_details('wave', 'right')['events'])
        self.assertEqual(g.dump(), before)
        go(g, 'wave', 'right')
        self.assertNotIn('ice_until', g.tile_at([7, 6]))
        self.assertEqual(g.player['hp'], 4)

    def test_frozen_water_does_not_stop_a_direct_electric_hit(self):
        g = self.arena()
        g.player.update(x=6, y=5)
        g.terrain = [dict(x=5, y=5, kind='water')]
        g.inventory = ['frost_smoke']
        self.enemy(g, 'elementcore', 3, 5, element='spark', energy=1)
        g.update_visibility()
        go(g, 'item', [5, 5], 'frost_smoke')
        self.assertEqual(g.player['hp'], 4)
        self.assertEqual(g.conducted_water([[5, 5]]), [])

    def test_reflected_electric_wave_conducts_and_hits_once_per_enemy(self):
        g = self.arena()
        g.player.update(x=6, y=5)
        g.terrain = [dict(x=x, y=y, kind='water') for x, y in [(3, 5), (4, 5), (5, 5), (5, 6)]]
        core = self.enemy(g, 'elementcore', 3, 5, element='spark', energy=1)
        target = self.enemy(g, 'bonepuppet', 5, 6, hp=2)
        target['intent'] = dict(action='wait', label='休整', cells=[])
        go(g, 'reflect', 'left')
        self.assertEqual(g.player['hp'], 5)
        self.assertEqual(core['hp'], 2)
        self.assertEqual(target['hp'], 1)

    def test_statue_inscription_and_reward(self):
        g = self.arena()
        self.enemy(g,'armedidol',5,5,emitter='straight',inscription='frost',energy=1,hp=1,dormant=False)
        go(g,'charge')
        self.assertTrue(g.movement_locked())
        go(g,'wave','right')
        self.assertFalse(g.movement_locked())
        self.assertEqual(g.features[0]['kind'], 'rune')
        self.assertIn(g.features[0]['rune'], g.dropped_runes)

    def test_dormant_statue_can_be_scouted_and_revisited_before_engaging(self):
        g = self.arena()
        g.talent_milestones = [1]
        e = self.enemy(g, 'armedidol', 5, 5, hp=3, emitter='straight', inscription='frost')
        g.update_visibility()
        self.assertEqual(g.state()['statueLandmarks'],
                         [dict(x=5, y=5, emitter='straight', inscription='frost')])
        self.assertEqual(g.path_to([5, 5]), ['right'])
        self.assertFalse(g.can_investigate_sound(e))
        self.assertTrue(g.can_upgrade_weapon())
        go(g, 'move', 'right')
        self.assertTrue(e['dormant'])
        self.assertEqual(e['intent']['action'], 'wait')
        g.player.update(x=12, y=5)
        g.update_visibility()
        g = FloorDungeon.restore(json.loads(json.dumps(g.dump())))
        self.assertFalse(g.state()['enemies'])
        self.assertEqual(len(g.state()['statueLandmarks']), 1)
        g.player.update(x=4, y=5)
        g.update_visibility()
        go(g, 'wave', 'right')
        self.assertEqual(g.player['hp'], 5)
        self.assertFalse(g.enemies[0].get('dormant'))
        self.assertFalse(g.state()['statueLandmarks'])
        self.assertEqual(g.enemies[0]['intent']['action'], 'notice')

    def test_wraith_marks_decoy_and_real_destination(self):
        g = self.arena()
        e = self.enemy(g,'mirrorwraith',6,5)
        target = e['intent']['target']
        self.assertEqual(len(e['intent']['warning']),2)
        self.assertIn(target,e['intent']['warning'])
        go(g,'guard')
        self.assertEqual([e['x'],e['y']],target)
        self.assertEqual(e['intent']['action'],'wait')

    def test_mimic_reveals_from_a_ranged_hit(self):
        g = self.arena()
        e = self.enemy(g,'chestmimic',6,5)
        g.update_visibility()
        self.assertEqual(g.state()['enemies'][0]['name'],'可疑的宝箱')
        go(g,'wave','right')
        self.assertFalse(e['disguised'])
        self.assertEqual(e['intent']['action'],'notice')

    def test_nest_caps_spawn_and_does_not_activate_behind_a_door(self):
        g = self.arena()
        g.doors, g._door_cells = [[5,5]], {(5,5)}
        e = self.enemy(g,'broodnest',6,5)
        go(g,'guard')
        self.assertNotIn('chant_target',e)
        g.doors, g._door_cells = [],set()
        for _ in range(10):
            go(g,'guard')
        self.assertEqual(sum(m['kind']=='broodling' for m in g.enemies),2)
        self.assertEqual(e['broods'],2)

    def test_fish_moves_only_in_water_and_cannot_be_pushed_ashore(self):
        g = self.arena()
        g.terrain = [dict(x=x,y=5,kind='water') for x in (5,6)]
        fish = self.enemy(g,'canalfish',6,5)
        go(g,'guard')
        self.assertEqual(fish['x'],5)
        g.push_enemy(fish,[-1,0])
        self.assertEqual(fish['x'],5)
