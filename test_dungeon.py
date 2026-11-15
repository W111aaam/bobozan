from copy import deepcopy
from collections import deque
import unittest

from dungeon import Dungeon, DIRS, UPGRADES


def enemy(kind='charger', x=5, y=4, hp=2, action='wait', cells=None, **extra):
    return dict(id=0, kind=kind, name='测试怪', x=x, y=y, hp=hp, energy=1, phase=0,
                intent=dict(action=action,cells=cells or [],**extra))


def arena():
    g=Dungeon(10)
    g.walls=[[x,y] for x in range(9) for y in range(9) if x in (0,8) or y in (0,8)]
    g.player.update(x=3,y=4,energy=1)
    g.enemies=[enemy()]
    return g


def act(g, action, direction=None, choice=None):
    g.act(action,direction,g.version,choice)


class DungeonRulesTests(unittest.TestCase):
    def test_invalid_actions_are_transactional(self):
        for action,direction in [('move','unknown'),('heavy','right'),('unknown',None)]:
            g=arena();before=g.dump()
            with self.assertRaises(ValueError): act(g,action,direction)
            self.assertEqual(g.dump(),before)
        g=arena();g.player['energy']=0;before=g.dump()
        with self.assertRaises(ValueError):act(g,'wave','right')
        self.assertEqual(g.dump(),before)

    def test_wall_and_enemy_block_movement(self):
        for obstruction in ('wall','enemy'):
            g=arena()
            if obstruction=='wall':g.walls.append([4,4])
            else:g.enemies[0]['x']=4
            before=g.dump()
            with self.assertRaises(ValueError):act(g,'move','right')
            self.assertEqual(g.dump(),before)

    def test_contested_destination_blocks_both(self):
        g=arena();g.enemies=[enemy(action='move',target=[4,4])]
        act(g,'move','right')
        self.assertEqual((g.player['x'],g.enemies[0]['x']),(3,5))

    def test_dodge_locked_ray(self):
        g=arena();g.enemies=[enemy(action='wave',direction='left',cells=[[4,4],[3,4],[2,4],[1,4]])]
        act(g,'move','down')
        self.assertEqual(g.player['hp'],6)
        self.assertEqual(g.player['y'],5)

    def test_simultaneous_kill_still_takes_damage(self):
        g=arena();g.enemies=[enemy(hp=1,action='wave',direction='left',cells=[[4,4],[3,4]])]
        act(g,'wave','right')
        self.assertEqual(g.player['hp'],5)
        self.assertTrue(g.cleared)

    def test_simultaneous_death_is_defeat(self):
        g=arena();g.player['hp']=1;g.enemies=[enemy(hp=1,action='wave',direction='left',cells=[[4,4],[3,4]])]
        act(g,'wave','right')
        self.assertEqual(g.result,'defeat')
        self.assertFalse(g.choices)

    def test_wave_blocked_by_wall(self):
        g=arena();g.walls.append([4,4]);act(g,'wave','right')
        self.assertEqual(g.enemies[0]['hp'],2)

    def test_wave_has_four_tile_range(self):
        g=arena();g.player['x']=1;g.enemies[0]['x']=6
        act(g,'wave','right');self.assertEqual(g.enemies[0]['hp'],2)

    def test_guard_absorbs_only_one_total_damage(self):
        g=arena();g.enemies=[enemy(action='area',cells=[[3,4]])]
        act(g,'guard');self.assertEqual(g.player['hp'],5)

    def test_guard_upgrade_once_per_room(self):
        g=arena();g.player['hp']=3;g.upgrades=['heart']
        for _ in range(2):
            g.enemies[0]['intent']=dict(action='melee',cells=[[3,4]])
            act(g,'guard')
        self.assertEqual(g.player['hp'],4)

    def test_echo_only_first_charge_and_cap(self):
        g=arena();g.player['energy']=0;g.upgrades=['echo']
        act(g,'charge');self.assertEqual(g.player['energy'],2)
        act(g,'charge');self.assertEqual(g.player['energy'],3)
        before=g.dump()
        with self.assertRaises(ValueError):act(g,'charge')
        self.assertEqual(before,g.dump())

    def test_pierce_hits_two_not_three(self):
        g=arena();g.upgrades=['pierce'];g.enemies=[enemy(x=4),enemy(x=5),enemy(x=6)]
        for i,e in enumerate(g.enemies):e['id']=i
        act(g,'wave','right')
        self.assertEqual([e['hp'] for e in g.enemies],[1,1,2])

    def test_refund_kills_and_heavy_guard(self):
        g=arena();g.upgrades=['refund','heavy','bag'];g.player['energy']=4
        g.enemies=[enemy(hp=1,action='guard'),dict(enemy(x=6),id=1)]
        act(g,'heavy','right')
        self.assertEqual(g.player['energy'],2)
        self.assertEqual(len(g.enemies),1)

    def test_choice_required_and_cannot_take_twice(self):
        g=arena();g.enemies[0]['hp']=1;act(g,'wave','right')
        self.assertEqual(len(g.choices),3)
        with self.assertRaises(ValueError):act(g,'move','up')
        choice=g.choices[0]['id'];act(g,'choose',choice=choice)
        self.assertIn(choice,g.upgrades)
        with self.assertRaises(ValueError):act(g,'choose',choice=choice)

    def test_exit_requires_position_clear_and_preserves_health(self):
        g=arena()
        with self.assertRaises(ValueError):act(g,'exit')
        g.enemies=[];g.cleared=True;g.player.update(hp=3,x=7,y=1,energy=2)
        act(g,'exit')
        self.assertEqual(g.room,1)
        self.assertEqual(g.player,dict(x=1,y=7,hp=3,energy=0))
        self.assertFalse(g.cleared)

    def test_shrine_optional_and_single_use(self):
        g=arena();g.room=2;g.enter_room();g.player.update(x=4,y=5,hp=2)
        act(g,'move','up');self.assertTrue(g.choices)
        act(g,'choose',choice='heal');self.assertEqual(g.player['hp'],4)
        act(g,'move','down');act(g,'move','up');self.assertFalse(g.choices)
        with self.assertRaises(ValueError):act(g,'charge')

    def test_boss_telegraph_and_win(self):
        g=arena();g.room=4;g.enemies=[enemy(kind='boss',hp=1)]
        g.enemies[0]['phase']=2;g.plan()
        self.assertEqual(g.enemies[0]['intent']['action'],'area')
        self.assertEqual(len(g.enemies[0]['intent']['cells']),3)
        act(g,'wave','right')
        self.assertEqual(g.result,'victory')
        self.assertEqual(g.player['hp'],4)

    def test_stale_version_cannot_act(self):
        g=arena();version=g.version;act(g,'charge');before=g.dump()
        with self.assertRaises(ValueError):g.act('guard',None,version)
        self.assertEqual(g.dump(),before)

    def test_save_restores_locked_intents_and_random_choices(self):
        g=arena();act(g,'charge');restored=Dungeon.restore(g.dump())
        self.assertEqual(g.state(),restored.state())
        act(g,'guard');act(restored,'guard')
        self.assertEqual(g.state(),restored.state())

    def test_seeded_layouts_reachable_and_spawns_valid(self):
        for seed in range(40):
            for room in range(5):
                g=Dungeon(seed);g.room=room;g.enter_room()
                visited={(1,7)};queue=deque(visited)
                while queue:
                    x,y=queue.popleft()
                    for dx,dy in DIRS.values():
                        p=(x+dx,y+dy)
                        if p not in visited and g.walkable(p):visited.add(p);queue.append(p)
                self.assertIn(tuple(g.exit),visited)
                if room==2:self.assertIn((4,4),visited)
                for e in g.enemies:self.assertIn((e['x'],e['y']),visited)
                self.assertEqual(g.state(),Dungeon.restore(g.dump()).state())


if __name__=='__main__':unittest.main()
