from collections import deque
import unittest
from floor import FloorDungeon
from dungeon import DIRS
from layout import generate_layout


def go(g,action,direction=None,choice=None):g.act(action,direction,g.version,choice)


def route(g,target):
    start=(g.player['x'],g.player['y']);q=deque([(start,[])]);seen={start}
    hazards = {position(tile) for tile in g.terrain if tile['kind'] == 'fragile'
               or tile['kind'] == 'trap' and tile['mechanism'] == 'fall' and tile['armed']}
    while q:
        p,path=q.popleft()
        if p==tuple(target):return path
        for d,(dx,dy) in DIRS.items():
            n=(p[0]+dx,p[1]+dy)
            if n not in seen and n not in hazards and g.walkable(n):
                seen.add(n);q.append((n,path+[d]))
    raise AssertionError('No path')


def position(actor):
    return actor['x'], actor['y']


def place(g, cell):
    g.player.update(x=cell[0], y=cell[1])
    g.update_visibility()


def feature(g, ident):
    return next(f for f in g.features if f['id'] == ident)


def center(g, room):
    return tuple(g.rooms_data[room]['anchor'])


class FloorTests(unittest.TestCase):
    def test_floor_snapshots_keep_consumed_resources_and_persistent_player_state(self):
        g = FloorDungeon(13)
        upper = g.exit[:]
        relic = feature(g, 'key')
        relic['used'] = True
        g.keys = 1
        g.locked = False
        g.enemies[0]['hp'] = 1
        place(g, upper)
        go(g, 'exit')
        lower = g.entrance_cell()
        self.assertEqual(g.state()['upStairs'], lower)
        g.keys = 0
        g.inventory.append('heal')
        g = FloorDungeon.restore(g.dump())
        go(g, 'ascend')
        self.assertEqual((g.depth, list(position(g.player)), g.sanity), (1, upper, 448))
        self.assertTrue(feature(g, 'key')['used'])
        self.assertFalse(g.locked)
        self.assertEqual((g.keys, g.enemies[0]['hp']), (1, 1))
        go(g, 'exit')
        self.assertEqual((g.depth, list(position(g.player)), g.keys, g.inventory), (2, lower, 0, ['heal']))

    def test_fall_trap_uses_safe_cell_on_next_floor(self):
        g = FloorDungeon(13)
        x, y = position(g.player)
        g.terrain.append(dict(x=x+1, y=y, kind='trap', mechanism='fall', armed=True))
        g.update_visibility()
        with self.assertRaisesRegex(ValueError, '绕过'):
            g.path_to([x+1, y])
        self.assertEqual(g.path_to([x+1, y], True), ['right'])
        go(g, 'move', 'right')
        self.assertEqual((g.result, g.depth, g.player['hp'], g.sanity), (None, 2, 3, 449))
        target = position(g.player)
        self.assertNotIn((g.tile_at(target) or {}).get('kind'), ('trap', 'fragile'))
        self.assertTrue(g.walkable(target))
        self.assertFalse(any(position(f) == target for f in g.features))
        self.assertIn(g.rooms_data[g.room]['kind'], ('entry', 'standard', 'combat', 'branch'))
        self.assertEqual(g.state()['fallTransition']['landing'], list(target))

    def test_corrosion_ticks_and_light_refills_sanity(self):
        g = FloorDungeon(13)
        g.sanity = 151
        g.enemies = []
        go(g, 'guard')
        self.assertEqual(g.sanity, 150)
        self.assertGreater(len(g.corruption_rooms), 0)
        old_ids = [enemy['id'] for enemy in g.enemies]
        g = FloorDungeon.restore(g.dump())
        go(g, 'guard')
        self.assertEqual([enemy['id'] for enemy in g.enemies], old_ids)
        g.sanity = 1
        g.player['energy'] = 0
        go(g, 'charge')
        self.assertEqual((g.sanity, g.player['hp']), (0, 4))
        g.corrosion = 115
        go(g, 'guard')
        self.assertEqual(g.player['hp'], 3)
        x, y = position(g.player)
        g.features.append(dict(id='test-light', kind='light_wisp', x=x, y=y, used=False))
        go(g, 'guard')
        self.assertEqual((g.sanity, g.player['hp'], g.corrosion), (64, 3, 0))
        self.assertEqual(g.state()['lightBlessings'], {'light_wisp': 65})
        self.assertNotIn('test-light', [f['id'] for f in g.state()['features']])

    def test_ordinary_floors_generate_real_loot_and_do_not_spawn_empty_features(self):
        for seed in range(8):
            for depth in (1, 2, 3, 4, 7, 12, 19, 24):
                generated = generate_layout(seed, depth)
                self.assertFalse({'materials', 'dry_spring'} & {f['kind'] for f in generated['features']})
                self.assertTrue(any(f['id'] == 'light' for f in generated['features']))
                self.assertGreaterEqual(sum(t['kind'] == 'trap' for t in generated['terrain']), 2)
                self.assertGreaterEqual(sum(t['kind'] == 'high_grass' for t in generated['terrain']), 8)
    def test_loop_and_all_objectives_reachable(self):
        layouts = set()
        for seed in range(40):
            for depth in (1, 2, 3):
                g = FloorDungeon(seed)
                g.depth = depth
                g.enter_room()
                layouts.add(tuple(map(tuple, g.doors)))
                for target in [center(g, i) for i in range(1, 6)] + [g.exit]:
                    self.assertTrue(route(g, target))
                for room in (1, 4, 5):
                    bounds = g.rooms_data[room]['bounds']
                    doors = [p for p in g.doors if bounds[0] <= p[0] <= bounds[2]
                             and bounds[1] <= p[1] <= bounds[3]]
                    self.assertGreaterEqual(len(doors), 2)
                    for x, y in doors:
                        dx = int(x == bounds[0]) - int(x == bounds[2])
                        dy = int(y == bounds[1]) - int(y == bounds[3])
                        for side in (-1, 0, 1):
                            self.assertTrue(g.walkable((x + dx - dy*side, y + dy + dx*side)))
        self.assertGreater(len(layouts), 40)

    def test_room_shapes_have_real_walls_and_reachable_objectives(self):
        shapes = set()
        for seed in range(8):
            g = FloorDungeon(seed)
            for depth in (2, 7, 12, 17, 22):
                g.depth = depth
                g.enter_room()
                self.assertEqual(g.room_at(g.rooms_data[-1]['anchor']), g.rooms_data[-1]['id'])
                g.locked = False
                for room in g.rooms_data:
                    shape = room['shape']
                    shapes.add(shape)
                    left, top, right, bottom = room['bounds']
                    if shape == 'chamfered':
                        self.assertFalse(g.walkable((left+1, top+1)))
                    if shape == 'hall':
                        self.assertEqual((max(right-left, bottom-top), min(right-left, bottom-top)), (10, 8))
                    route(g, room['anchor'])
                route(g, g.exit)
        self.assertEqual(shapes, {'rectangle', 'hall', 'chamfered', 'compact', 'cross', 'alcove'})

    def test_themed_floor_has_extra_terrain_and_survives_restore(self):
        seen = set()
        for seed in range(20):
            g = FloorDungeon(seed)
            self.assertIsNone(g.state()['floorTheme'])
            g.depth = 2
            g.enter_room()
            theme = g.state()['floorTheme']
            if not theme:
                continue
            seen.add(theme)
            layout = generate_layout(seed, 2)
            self.assertEqual(g.terrain, layout['terrain'])
            cells = [(t['x'], t['y']) for t in g.terrain]
            self.assertEqual(len(cells), len(set(cells)))
            terrain_kind = 'water' if theme == 'water' else 'high_grass'
            groups = {room['id'] for room in g.rooms_data
                      if room['kind'] in ('combat', 'standard') and
                      sum(t['kind'] == terrain_kind and g.room_at((t['x'], t['y'])) == room['id']
                          for t in g.terrain) >= 3}
            self.assertGreaterEqual(len(groups), 2)
            self.assertIsNone(g.tile_at(position(g.player)))
            self.assertEqual(FloorDungeon.restore(g.dump()).state()['floorTheme'], theme)
            g.depth = 5
            g.enter_room()
            self.assertIsNone(g.state()['floorTheme'])
        self.assertEqual(seen, {'water', 'grass'})

    def test_region_growth_survives_reload_and_healing_uses_new_cap(self):
        g = FloorDungeon(0)
        g.depth = 10
        g.enter_room()
        self.assertEqual(g.max_hp, 6)
        g.player['hp'] = 5
        g.depth = 11
        g.enter_room()
        self.assertEqual((g.player['hp'], g.max_hp), (5, 7))
        self.assertEqual(g.wave_damage_before_defense('wave'), 1)
        g = FloorDungeon.restore(g.dump())
        go(g, 'choose_talents', choice=[])
        g.inventory = ['heal']
        go(g, 'item', choice='heal')
        self.assertEqual(g.state()['maxHp'], 7)
        self.assertEqual(g.player['hp'], 7)

    def test_campaign_has_twenty_regular_floors_five_arenas_and_final_altar(self):
        g = FloorDungeon(0)
        for depth in range(1, 27):
            g.depth = depth
            g.enter_room()
            state = g.state()
            if depth == 26:
                self.assertEqual(state['floorKind'], 'relic')
                self.assertFalse(g.enemies)
                self.assertTrue(g.exit_unlocked())
            elif depth % 5 == 0:
                self.assertEqual(state['floorKind'], 'boss')
                self.assertFalse(g.exit_unlocked())
                self.assertTrue(any(e['kind'] in ('boss', 'breaker', 'mirrorboss') for e in g.enemies))
            else:
                self.assertEqual(state['floorKind'], 'regular')
                self.assertEqual(g.exit_unlocked(), depth % 5 != 4)
            self.assertTrue(route(g, g.exit))
        place(g, g.exit)
        go(g, 'exit')
        self.assertEqual(g.result, 'victory')

    def test_safe_charge_and_round_trip_preserve_resources(self):
        g = FloorDungeon(0)
        go(g, 'charge'); go(g, 'charge')
        g.counter = True
        go(g, 'move', 'right'); go(g, 'move', 'left')
        self.assertEqual((g.player['energy'], g.player['hp'], g.room), (2, 5, 0))
        self.assertTrue(g.counter)

    def test_persisted_enemy_and_rewards_do_not_reset(self):
        g = FloorDungeon(0)
        g.enemies[0]['hp'] = 1
        go(g, 'charge')
        g.echo_used = g.heart_used = True
        g = FloorDungeon.restore(g.dump())
        self.assertEqual(g.enemies[0]['hp'], 1)
        self.assertTrue(g.echo_used and g.heart_used)

    def test_chest_once_and_save_restoration(self):
        g = FloorDungeon(0)
        g.depth = 3
        g.enter_room()
        x, y = position(feature(g, 'chest'))
        place(g, (x-1, y))
        go(g, 'move', 'right')
        choice = g.choices[0]['id']
        go(g, 'choose', choice=choice)
        restored = FloorDungeon.restore(g.dump())
        self.assertEqual(g.state(), restored.state())
        go(restored, 'move', 'left'); go(restored, 'move', 'right')
        self.assertFalse(restored.choices)
        self.assertEqual(restored.upgrades, [choice])

    def test_shrine_once_and_cap(self):
        g = FloorDungeon(0)
        g.depth = 2
        g.enter_room()
        x, y = position(feature(g, 'spring'))
        place(g, (x-1, y))
        g.player['hp'] = 4
        go(g, 'move', 'right')
        self.assertEqual(g.player['hp'], 5)
        go(g, 'move', 'left'); go(g, 'move', 'right')
        self.assertFalse(g.choices)

    def test_fog_filters_enemies_geometry_and_features(self):
        g = FloorDungeon(0)
        start = position(g.player)
        state = g.state()
        self.assertFalse(state['enemies'])
        self.assertFalse(state['features'])
        self.assertIsNone(state['exit'])
        self.assertTrue(all(p in state['explored'] for p in state['walls']))
        x, y = center(g, 1)
        enemy = next(e for e in g.enemies if e['home'] == 1)
        enemy.update(x=x, y=y+1)
        place(g, (x, y))
        self.assertTrue(g.state()['enemies'])
        memory = list(g.explored)
        place(g, start)
        self.assertFalse(g.state()['enemies'])
        self.assertTrue(all(p in g.explored for p in memory))

    def test_feature_memory_remembers_only_seen_drops(self):
        g = FloorDungeon(0)
        start = position(g.player)
        x, y = center(g, 1)
        place(g, (x, y))
        place(g, start)
        drop = dict(id='drop-out-of-sight', kind='kit', x=x, y=y, used=False)
        g.features.append(drop)
        g.update_visibility()
        self.assertIn([x, y], g.explored)
        self.assertNotIn(drop['id'], [f['id'] for f in g.state()['features']])
        g = FloorDungeon.restore(g.dump())
        self.assertNotIn(drop['id'], [f['id'] for f in g.state()['features']])

        place(g, (x, y))
        place(g, start)
        g = FloorDungeon.restore(g.dump())
        self.assertIn(drop['id'], [f['id'] for f in g.state()['features']])
        self.assertNotIn([x, y], g.visible)

        g.depth = 2
        g.enter_room()
        self.assertNotIn(drop['id'], g.discovered_features)

    def test_legacy_save_keeps_previously_discovered_supplies(self):
        g = FloorDungeon(0)
        start = position(g.player)
        kit = feature(g, 'kit')
        place(g, position(kit))
        place(g, start)
        saved = g.dump()
        del saved['discovered_features']
        self.assertIn(kit['id'], [f['id'] for f in FloorDungeon.restore(saved).state()['features']])

    def test_path_only_known_ground_and_uses_one_safe_step_in_combat(self):
        g = FloorDungeon(0)
        before = g.dump()
        x, y = position(g.player)
        self.assertEqual(g.path_to([x+1,y]), ['right'])
        self.assertEqual(g.dump(), before)
        for target in (list(center(g, 2)), [0,0], [True,5], None):
            with self.assertRaises(ValueError):
                g.path_to(target)
        x, y = center(g, 1)
        enemy = next(e for e in g.enemies if e['home'] == 1)
        enemy.update(x=x, y=y+1)
        place(g, (x, y))
        g.plan()
        enemy['intent'] = dict(action='area', cells=[[x+1, y]])
        path = g.path_to([x+2, y])
        self.assertEqual(len(path), 1)
        self.assertNotEqual(path[0], 'right')

    def test_chapter_budget_and_gate_guard_unlock(self):
        g = FloorDungeon(2)
        for first in range(1, 26, 5):
            supplies = []
            for depth in range(first, first + 4):
                g.depth = depth
                g.enter_room()
                supplies.extend(f['kind'] for f in g.features)
            for kind in ('chest', 'kit', 'shrine'):
                self.assertEqual(supplies.count(kind), 1, (first, kind))

        self.assertEqual(sum(enemy['home'] == 1 for enemy in g.enemies), 2)
        place(g, g.exit)
        self.assertFalse(g.exit_unlocked())
        self.assertEqual(g.state()['exitLockReason'], '清理封锁阶梯的守卫')
        with self.assertRaises(ValueError):
            go(g, 'exit')
        g.enemies = [enemy for enemy in g.enemies if enemy['home'] != 1]
        self.assertTrue(g.enemies)
        g.finish_action()
        self.assertTrue(g.exit_unlocked())
        self.assertFalse(g.choices)
        self.assertIsNone(g.state()['exitLockReason'])
        go(g, 'exit')
        self.assertEqual(g.depth, 25)

    def test_floor_exit_requires_boss_and_position(self):
        g = FloorDungeon(0)
        with self.assertRaises(ValueError):
            go(g, 'exit')
        g.depth = 5
        g.enter_room()
        place(g, g.exit)
        with self.assertRaises(ValueError):
            go(g, 'exit')
        g.enemies = []
        g.finish_action()
        self.assertIn('heavy', [choice['id'] for choice in g.choices])
        go(g, 'skip_reward')
        go(g, 'exit')
        self.assertEqual(g.depth, 6)
        self.assertIsNone(g.result)

    def test_dart_vault_requires_opening_a_safe_lane(self):
        g = FloorDungeon(2)
        g.depth = 3
        g.enter_room()
        g.enemies = []
        g.plan()
        wing = g.rooms_data[-1]
        self.assertEqual(wing['kind'], 'dart_vault')
        target = wing['anchor']
        dx, dy = [(b-a)//3 for a, b in zip(g.lock, target)]
        direction = next(key for key, vector in DIRS.items() if vector == (dx, dy))
        place(g, (g.lock[0]-dx, g.lock[1]-dy))
        self.assertEqual(g.state()['lockStyle'], 'dart_vault')
        g.keys = 1
        go(g, 'unlock')
        go(g, 'move', direction)
        go(g, 'move', direction)
        self.assertIn(target, g.explored)
        with self.assertRaises(ValueError):
            g.path_to(target)
        g = FloorDungeon.restore(g.dump())
        go(g, 'charge')
        go(g, 'wave', direction)
        self.assertEqual(g.path_to(target), [direction, direction])
        hp = g.player['hp']
        go(g, 'move', direction)
        go(g, 'move', direction)
        self.assertEqual(g.player['hp'], hp)
        self.assertEqual(g.ground_runes_here()[0]['id'], 'cache')
        go(g, 'equip_ground_rune', choice='cache')
        self.assertTrue(feature(g, 'cache')['used'])

    def test_special_vaults_use_existing_key_and_give_distinct_rewards(self):
        for seed in (2, 1):
            g = FloorDungeon(seed)
            g.depth = 2
            g.enter_room()
            wing = g.rooms_data[-1]
            self.assertEqual(wing['kind'], 'garden' if seed == 2 else 'alarm_store')
            target = wing['anchor']
            g.chart_floor()
            self.assertEqual(g.state()['lock'], g.lock)
            self.assertIsNone(g.state()['lockStyle'])
            dx, dy = [(b-a)//3 for a, b in zip(g.lock, target)]
            place(g, (g.lock[0]-dx, g.lock[1]-dy))
            self.assertEqual(g.state()['lockStyle'], wing['kind'])
            self.assertFalse(g.walkable(g.lock))
            g.keys = 1
            go(g, 'unlock')
            self.assertEqual(g.keys, 0)
            direction = next(key for key, vector in DIRS.items() if vector == (dx, dy))
            if seed == 2:
                g.player['hp'] = 3
                for step in route(g, target):
                    go(g, 'move', step)
                self.assertEqual(g.player['hp'], 5)
                self.assertIsNone(g.tile_at(target))
                g = FloorDungeon.restore(g.dump())
                g.player['hp'] = 3
                go(g, 'guard')
                self.assertEqual(g.player['hp'], 3)
            else:
                guard = next(e for e in g.enemies if e['home'] == wing['parent'])
                g.player['energy'] = 1
                go(g, 'wave', direction)
                trap = g.tile_at([g.lock[0]+dx, g.lock[1]+dy])
                self.assertFalse(trap['armed'])
                self.assertEqual(guard['sound']['kind'], 'alarm')
                g.enemies = []
                for step in route(g, target):
                    go(g, 'move', step)
                self.assertEqual(g.inventory, ['echo_smoke'])

    def test_supply_box_can_be_deferred_and_claimed_once_after_reload(self):
        g = FloorDungeon(0)
        for first in range(1, 26, 5):
            options = []
            for depth in range(first, first + 4):
                g.depth = depth
                g.enter_room()
                if any(f['kind'] == 'supply_choice' for f in g.features):
                    options.append(depth)
            self.assertEqual(len(options), 1)
        g.depth = 2
        g.enter_room()
        box = feature(g, 'chest')
        self.assertEqual(g.state()['supplyOptions'], [])
        with self.assertRaises(ValueError):
            go(g, 'open_supply')
        place(g, position(box))
        expected = ['smoke', 'lure']
        self.assertEqual([item['id'] for item in g.state()['supplyOptions']], expected)
        g.inventory = ['ankh'] * g.bag_capacity
        go(g, 'open_supply')
        self.assertTrue(all(entry['blocked'] for entry in g.state()['choices']))
        before = g.dump()
        with self.assertRaises(ValueError):
            go(g, 'choose', choice='smoke')
        self.assertEqual(g.dump(), before)
        go(g, 'skip_reward')
        g.inventory.pop()

        go(g, 'open_supply')
        go(g, 'skip_reward')
        self.assertFalse(box['used'])
        go(g, 'open_supply')
        g = FloorDungeon.restore(g.dump())
        self.assertEqual([entry['id'] for entry in g.state()['choices']], expected)
        go(g, 'choose', choice='smoke')
        self.assertEqual(g.inventory[-1], 'smoke')
        self.assertTrue(feature(g, 'chest')['used'])
        self.assertEqual(g.state()['supplyOptions'], [])
        self.assertEqual((g.turn, g.forge_cores, g.upgrades), (0, 0, []))
        with self.assertRaises(ValueError):
            go(g, 'open_supply')

    def test_locked_supply_and_consumable(self):
        g = FloorDungeon(0)
        cache = position(feature(g, 'cache'))
        dx, dy = [(b-a)//3 for a, b in zip(g.lock, cache)]
        place(g, (g.lock[0]-dx, g.lock[1]-dy))
        self.assertFalse(g.walkable(g.lock))
        with self.assertRaises(ValueError):
            go(g, 'unlock')
        g.keys = 1
        go(g, 'unlock')
        self.assertEqual(g.keys, 0)
        for direction in route(g, cache):
            go(g, 'move', direction)
        self.assertEqual(g.inventory, ['smoke'])
        turn = g.turn
        go(g, 'item', choice='smoke')
        self.assertEqual((g.turn, g.smoke, g.inventory), (turn+1, 3, []))

    def test_route_opens_closed_door_that_blocks_sight_and_shots(self):
        g = FloorDungeon(0)
        g.enemies = []
        for room in g.rooms_data:
            room['cleared'] = True
        door, outside, inside, direction = doorway(g, 1)
        dx, dy = DIRS[direction]
        place(g, (outside[0]-dx, outside[1]-dy))
        self.assertFalse(g.has_sight(outside, inside))
        self.assertEqual(g.path_to(list(door)), [direction, direction])
        go(g, 'move', direction)
        self.assertNotIn(list(inside), g.ray(outside, direction))
        go(g, 'move', direction)
        self.assertIn(list(door), g.state()['openDoors'])
        self.assertTrue(g.has_sight(outside, inside))
        go(g, 'move', direction)
        self.assertTrue(g.door_closed(door))

    def test_notice_then_pursuit_follows_across_door(self):
        g = FloorDungeon(0)
        door, outside, inside, direction = doorway(g, 1)
        dx, dy = DIRS[direction]
        enemy = next(e for e in g.enemies if e['home'] == 1)
        g.enemies = [enemy]
        for room in g.rooms_data:
            room['cleared'] = True
        enemy.update(x=inside[0]+dx, y=inside[1]+dy, kind='ram', energy=0)
        place(g, outside)
        g.plan()
        self.assertNotIn('last_seen', enemy)
        go(g, 'move', direction)
        self.assertEqual(enemy['intent']['action'], 'notice')
        self.assertEqual(g.player['hp'], 5)
        # Leave the door before the enemy attacks. It pursues the last seen
        # doorway and opens the same door on arrival.
        reverse = next(k for k, v in DIRS.items() if v == (-dx, -dy))
        go(g, 'move', reverse)
        self.assertEqual(enemy['last_seen'], list(door))
        self.assertTrue(g.door_closed(door))
        for _ in range(2):
            go(g, 'guard')
        self.assertEqual(position(enemy), door)
        self.assertFalse(g.door_closed(door))


def doorway(g, room):
    left, top, right, bottom = g.rooms_data[room]['bounds']
    x, y = next((x, y) for x, y in g.doors
                if left <= x <= right and top <= y <= bottom)
    dx = int(x == left) - int(x == right)
    dy = int(y == top) - int(y == bottom)
    direction = next(k for k, v in DIRS.items() if v == (dx, dy))
    return (x, y), (x-dx,y-dy), (x+dx,y+dy), direction
