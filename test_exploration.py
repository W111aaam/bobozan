import unittest

from floor import FloorDungeon
from dungeon import DIRS
from test_floor import go, place, position, route
import test_mechanics


class ExplorationTests(unittest.TestCase):
    def test_secret_passage_shortens_route_after_search(self):
        game = FloorDungeon(0)
        game.depth = 6
        game.enter_room()
        go(game, 'choose_talents', choice=[])
        game.enemies = []
        game.plan()
        gate, = game.shortcut_doors
        start = (26, 22)
        target = [26, 16]
        place(game, start)
        game.chart_floor()
        self.assertIn(gate, game.state()['secretClues'])
        self.assertEqual(game.state()['openedShortcuts'], [])
        self.assertIn(gate, game.state()['walls'])
        old_path = game.path_to(target)
        self.assertGreater(len(old_path), 6)
        game = FloorDungeon.restore(game.dump())
        go(game, 'search')
        self.assertTrue(any('发现隐蔽通路' in entry for entry in game.log))
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.path_to(target), ['up'] * 6)
        self.assertEqual(game.state()['openedShortcuts'], [gate])
        for direction in game.path_to(target):
            go(game, 'move', direction)
        self.assertEqual(list(position(game.player)), target)
        self.assertEqual(game.path_to(list(start)), ['down'] * 6)
        game.depth = 10
        game.enter_room()
        self.assertFalse(game.shortcut_doors)
        self.assertEqual(game.state()['entrance'], list(position(game.player)))

    def test_seen_secret_clue_persists_and_paths_to_search_range(self):
        game = FloorDungeon(0)
        game.depth = 2
        game.enter_room()
        game.enemies = []
        game.plan()
        gate, = game.secret_doors
        reward = next(f for f in game.features if f['id'] == 'secret-reward')
        dx = (reward['x'] - gate[0]) // 3
        dy = (reward['y'] - gate[1]) // 3
        near = [gate[0] - dx, gate[1] - dy]
        start = position(game.player)
        game.chart_floor()
        self.assertFalse(game.state()['secretClues'])
        with self.assertRaises(ValueError):
            game.path_to(gate)
        for direction in route(game, near):
            go(game, 'move', direction)
        self.assertIn(gate, game.state()['secretClues'])
        for direction in route(game, start):
            go(game, 'move', direction)
        game = FloorDungeon.restore(game.dump())
        self.assertIn(gate, game.state()['secretClues'])
        self.assertNotIn(gate, game.state()['searchHints'])
        for direction in game.path_to(gate):
            go(game, 'move', direction)
        self.assertIn(gate, game.state()['searchHints'])
        self.assertEqual(game.path_to(gate), [])
        go(game, 'search')
        self.assertNotIn(gate, game.state()['secretClues'])
        self.assertIn(gate, game.state()['doors'])

    def test_search_reveals_door_once_and_reward_is_reachable(self):
        game = FloorDungeon(0)
        game.depth = 2
        game.enter_room()
        gate, = game.secret_doors
        reward = next(f for f in game.features if f['id'] == 'secret-reward')
        dx = (reward['x'] - gate[0]) // 3
        dy = (reward['y'] - gate[1]) // 3
        near = [gate[0] - dx, gate[1] - dy]
        direction = next(k for k, v in DIRS.items() if v == (dx, dy))
        self.assertFalse(game.state()['searchHints'])
        place(game, near)
        self.assertFalse(game.walkable(gate))
        self.assertNotIn(gate, game.ray(near, direction))
        self.assertIn(gate, game.state()['searchHints'])
        self.assertNotIn(gate, game.state()['doors'])
        self.assertNotIn(reward, game.state()['features'])
        go(game, 'search')
        self.assertEqual(game.turn, 1)
        self.assertIn(gate, game.state()['doors'])
        self.assertFalse(game.state()['searchHints'])
        game = FloorDungeon.restore(game.dump())
        go(game, 'search')
        self.assertEqual(game.doors.count(gate), 1)
        for step in route(game, (reward['x'], reward['y'])):
            go(game, 'move', step)
        self.assertEqual(game.ground_runes_here()[0]['id'], reward['id'])
        go(game, 'equip_ground_rune', choice=reward['id'])
        self.assertEqual(game.rune, reward['rune'])

    def trap_arena(self):
        game = FloorDungeon(0)
        game.enemies = []
        for room in game.rooms_data:
            room['cleared'] = True
        game.terrain = []
        x,y = game.player['x'],game.player['y']
        game.update_visibility()
        return game, x, y

    def test_dart_trap_detours_then_disarms_by_wave(self):
        game,x,y = self.trap_arena()
        tile = dict(x=x+1, y=y, kind='trap', mechanism='dart', armed=True)
        game.terrain.append(tile)
        game.update_visibility()
        self.assertNotEqual(game.path_to([x+2,y])[0], 'right')
        go(game, 'charge')
        self.assertIn('将触发陷阱', game.preview_details('wave','right')['events'])
        self.assertTrue(tile['armed'])
        go(game,'wave','right')
        self.assertFalse(tile['armed'])
        self.assertEqual(game.path_to([x+2,y]), ['right','right'])
        go(game,'move','right')
        self.assertEqual(game.player['hp'],5)

    def test_hidden_trap_is_private_until_search_then_saved_and_avoided(self):
        game, x, y = self.trap_arena()
        tile = dict(x=x+2, y=y, kind='trap', mechanism='dart', armed=True, hidden=True)
        game.terrain.append(tile)
        game.update_visibility()
        self.assertTrue(game.state()['trapClues'])
        self.assertNotIn(tile, game.state()['terrain'])
        self.assertGreater(len(game.path_to([x+3, y])), 3)
        go(game, 'charge')
        self.assertNotIn('将触发陷阱', game.preview_details('wave', 'right')['events'])
        go(game, 'search')
        self.assertEqual(game.turn, 2)
        self.assertIn(tile, game.state()['terrain'])
        self.assertFalse(game.state()['trapClues'])
        self.assertTrue(tile['armed'])
        self.assertIn('将触发陷阱', game.preview_details('wave', 'right')['events'])
        game = FloorDungeon.restore(game.dump())
        self.assertNotEqual(game.path_to([x+3, y])[0], 'right')
        go(game, 'wave', 'right')
        self.assertFalse(game.tile_at([x+2, y])['armed'])

    def test_alarm_broadcasts_to_distant_enemies_and_they_follow_the_fixed_location(self):
        fixture = test_mechanics.ExpeditionMechanicsTests()
        game = fixture.arena()
        x, y = position(game.player)
        game.terrain.append(dict(x=x+1, y=y, kind='trap', mechanism='alarm', armed=True))
        near = fixture.enemy(game, x+4, y)
        far = fixture.enemy(game, x+9, y)
        go(game, 'move', 'right')
        for enemy in (near, far):
            self.assertEqual(enemy['sound']['target'], [x+1, y])
            self.assertEqual(enemy['intent']['action'], 'move')
        go(game, 'move', 'down')
        self.assertEqual(far['sound']['target'], [x+1, y])

    def test_search_does_not_reveal_trap_behind_closed_door(self):
        game, x, y = self.trap_arena()
        door = [x+1, y]
        game.doors.append(door)
        game._door_cells.add(tuple(door))
        tile = dict(x=x+2, y=y, kind='trap', mechanism='dart', armed=True, hidden=True)
        game.terrain.append(tile)
        game.update_visibility()
        go(game, 'search')
        self.assertTrue(tile['hidden'])
        go(game, 'move', 'right')
        go(game, 'search')
        self.assertNotIn('hidden', tile)

    def test_thrown_lure_springs_hidden_alarm(self):
        game, x, y = self.trap_arena()
        target = [x+1, y]
        game.inventory = ['lure']
        tile = dict(x=target[0], y=target[1], kind='trap', mechanism='alarm', armed=True, hidden=True)
        game.terrain.extend([tile, dict(x=x+2, y=y, kind='high_grass')])
        enemy = game.add_enemy('bonepuppet', [x+3, y], 0, 2)
        game.update_visibility()
        go(game, 'item', target, 'lure')
        self.assertEqual(game.turn, 1)
        self.assertFalse(tile['armed'])
        self.assertNotIn('hidden', tile)
        self.assertIn(tile, game.state()['terrain'])
        self.assertEqual(enemy['sound']['kind'], 'alarm')
        self.assertEqual(game.inventory, [])

    def test_planting_does_not_disclose_hidden_trap_before_action(self):
        game, x, y = self.trap_arena()
        target = [x+1, y]
        game.inventory = ['grass_seed']
        tile = dict(x=target[0], y=target[1], kind='trap', mechanism='dart', armed=True, hidden=True)
        game.terrain.append(tile)
        game.update_visibility()
        self.assertIn(target, game.state()['plantTargets'])
        go(game, 'plant', target, 'grass_seed')
        self.assertEqual(game.turn, 1)
        self.assertEqual(game.inventory, ['grass_seed'])
        self.assertTrue(tile['armed'])
        self.assertIn(tile, game.state()['terrain'])

    def test_gripping_trap_blocks_move_and_blink_for_one_action(self):
        game, x, y = self.trap_arena()
        game.terrain.append(dict(x=x+1, y=y, kind='trap', mechanism='grip', armed=True))
        game.player['energy'] = 1
        game.upgrades = ['pierce', 'blink']
        go(game, 'move', 'right')
        self.assertTrue(game.state()['snared'])
        game = FloorDungeon.restore(game.dump())
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'move', 'right')
        self.assertEqual(game.dump(), before)
        go(game, 'wave', 'right')
        self.assertEqual(position(game.player), (x+1, y))
        self.assertFalse(game.state()['movementLocked'])
        go(game, 'move', 'right')
        self.assertEqual(position(game.player), (x+2, y))

    def test_gripping_trap_stops_an_enemys_next_move(self):
        game, x, y = self.trap_arena()
        game.terrain.append(dict(x=x+2, y=y, kind='trap', mechanism='grip', armed=True))
        enemy = game.add_enemy('bonepuppet', [x+3, y], 0, 2)
        enemy.update(last_seen=[x, y], search=4,
                     intent=dict(action='move', cells=[], target=[x+2, y]))
        go(game, 'guard')
        self.assertEqual(enemy['intent']['action'], 'wait')
        self.assertEqual(enemy['hp'], 2)
        self.assertFalse(game.state()['snared'])
        go(game, 'guard')
        self.assertEqual(enemy['intent']['action'], 'move')

    def test_dart_trap_only_hurts_once(self):
        game,x,y = self.trap_arena()
        game.terrain.append(dict(x=x+1, y=y, kind='trap', mechanism='dart', armed=True))
        go(game,'move','right')
        self.assertEqual(game.player['hp'],4)
        go(game,'move','left')
        go(game,'move','right')
        self.assertEqual(game.player['hp'],4)

    def test_alarm_reaches_room_enemies_out_of_sight(self):
        game,x,y = self.trap_arena()
        game.terrain.extend([dict(x=x+1, y=y, kind='trap', mechanism='alarm', armed=True),
                             dict(x=x+2, y=y, kind='high_grass')])
        enemy = game.add_enemy('bonepuppet', [x+3,y], 0, 2)
        game.plan()
        self.assertNotIn('last_seen', enemy)
        go(game,'move','right')
        self.assertTrue(game.has_threat())
        self.assertNotIn('last_seen', enemy)
        self.assertEqual(enemy['sound']['target'], [x+1,y])
        self.assertIn('警报', enemy['intent']['label'])

    def test_chart_plans_routes_without_revealing_secret_or_contents(self):
        game = FloorDungeon(0)
        game.depth = 2
        game.enter_room()
        gate, = game.secret_doors
        reward = next(f for f in game.features if f['id'] == 'secret-reward')
        before = set(map(tuple, game.explored))
        game.inventory.append('chart')
        go(game, 'item', choice='chart')
        state = game.state()
        self.assertEqual(before, set(map(tuple, game.explored)))
        self.assertNotIn('chart', game.inventory)
        self.assertNotIn(gate, state['doors'])
        self.assertNotIn([reward['x'], reward['y']], state['mapped'])
        self.assertNotIn(reward, state['features'])
        self.assertEqual(state['exit'], game.exit)
        self.assertTrue(game.path_to(game.exit))
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(state['mapped'], game.state()['mapped'])

    def test_dropped_item_frees_slot_persists_and_can_be_recovered(self):
        game,x,y = self.trap_arena()
        game.inventory = ['heal','smoke','lure','chart','heal']
        go(game, 'drop', choice='heal')
        self.assertEqual(len(game.inventory),4)
        game = FloorDungeon.restore(game.dump())
        feature = next(f for f in game.state()['features'] if f['kind']=='dropped_item')
        go(game, 'pickup', choice=feature['id'])
        self.assertEqual(len(game.inventory),5)
        self.assertFalse(any(f['kind']=='dropped_item' for f in game.state()['features']))
        go(game, 'drop', choice='smoke')
        go(game, 'move', 'right')
        go(game, 'move', 'left')
        self.assertIn('smoke', game.inventory)

    def test_full_bag_can_pick_supply_without_leaving_tile(self):
        game, x, y = self.trap_arena()
        game.features = [dict(id='cache-test', kind='cache', x=x+1, y=y, used=False)]
        game.inventory = ['ankh'] * game.bag_capacity
        go(game, 'move', 'right')
        self.assertEqual([item['name'] for item in game.state()['groundItems'][0]['items']], ['烟雾弹', '诱饵'])
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'pickup', choice='cache-test')
        self.assertEqual(game.dump(), before)

        go(game, 'drop', choice='ankh')
        self.assertEqual(len(game.inventory), game.bag_capacity - 1)
        self.assertEqual(len(game.state()['groundItems']), 2)
        game = FloorDungeon.restore(game.dump())
        with self.assertRaises(ValueError):
            go(game, 'pickup', choice=dict(feature='cache-test', item='ankh'))
        go(game, 'pickup', choice=dict(feature='cache-test', item='lure'))
        self.assertEqual(game.inventory[-1], 'lure')
        game = FloorDungeon.restore(game.dump())
        self.assertEqual([item['name'] for item in game.state()['groundItems'][0]['items']], ['烟雾弹'])
        go(game, 'drop', choice='lure')
        go(game, 'pickup', choice=dict(feature='cache-test', item='smoke'))
        self.assertEqual(game.inventory[-1], 'smoke')
        self.assertEqual(position(game.player), (x+1, y))
        with self.assertRaises(ValueError):
            go(game, 'pickup', choice='cache-test')

    def test_pickup_all_uses_one_turn_and_keeps_overflow_on_the_ground(self):
        game, x, y = self.trap_arena()
        game.inventory = ['ankh'] * (game.bag_capacity - 1) + ['heal']
        game.features = [dict(id='drop-0', kind='kit', x=x, y=y, used=False),
                         dict(id='drop-1', kind='kit', x=x, y=y, used=False),
                         dict(id='drop-2', kind='smoke', x=x, y=y, used=False),
                         dict(id='drop-3', kind='kit', x=x+1, y=y, used=False)]
        game.update_visibility()
        before = game.turn
        go(game, 'pickup', choice={'all': True})
        self.assertEqual(game.turn, before + 1)
        self.assertEqual(game.inventory, ['ankh'] * (game.bag_capacity - 1) + ['heal'] * 3)
        game = FloorDungeon.restore(game.dump())
        state = game.state()
        self.assertEqual([f['id'] for f in state['groundItems']], ['drop-2'])
        self.assertEqual([f['id'] for f in state['features']], ['drop-2', 'drop-3'])
        before = game.dump()
        with self.assertRaisesRegex(ValueError, '背包已满'):
            go(game, 'pickup', choice={'all': True})
        self.assertEqual(game.dump(), before)

    def test_seed_stack_accepts_pickup_at_capacity_but_not_a_sixth_seed(self):
        game, x, y = self.trap_arena()
        game.bag_relics = [5]
        game.inventory = ['ankh'] * (game.bag_capacity - 1) + ['grass_seed'] * 4
        game.features = [dict(id='seeds', kind='grass_seed', x=x+1, y=y, used=False),
                         dict(id='extra', kind='grass_seed', x=x+1, y=y, used=False)]
        go(game, 'move', 'right')
        game = FloorDungeon.restore(game.dump())
        slots = game.state()['bagSlots']
        self.assertEqual(len(slots), game.bag_capacity)
        self.assertEqual(slots[-1], dict(id='grass_seed', count=5, limit=5))
        with self.assertRaises(ValueError):
            go(game, 'pickup', choice=dict(feature='extra', item='grass_seed'))
        go(game, 'drop', choice='grass_seed')
        self.assertIn('grass_seed', game.state()['packableItems'])
        go(game, 'pickup', choice=dict(feature='extra', item='grass_seed'))
        self.assertEqual(game.inventory.count('grass_seed'), 5)
        self.assertEqual(len(game.state()['groundItems']), 1)

    def test_full_bag_supply_box_offers_seed_that_can_join_a_stack(self):
        game, x, y = self.trap_arena()
        game.depth = 7
        game.bag_relics = [5]
        game.inventory = ['ankh'] * (game.bag_capacity - 1) + ['grass_seed']
        game.features = [dict(id='box', kind='supply_choice', x=x, y=y, used=False)]
        go(game, 'open_supply')
        self.assertEqual([choice['blocked'] for choice in game.state()['choices']], [True, False])
        with self.assertRaises(ValueError):
            go(game, 'choose', choice='echo_smoke')
        go(game, 'choose', choice='grass_seed')
        self.assertEqual(game.inventory.count('grass_seed'), 2)

    def test_healing_potion_cures_poison_before_the_next_tick(self):
        game,_,_ = self.trap_arena()
        game.player['hp'] = 3
        game.poisoned = True
        game.inventory = ['heal']
        go(game, 'item', choice='heal')
        self.assertEqual(game.player['hp'],5)
        self.assertFalse(game.poisoned)
        effects = {effect['kind']: effect['amount'] for effect in game.state()['effects']}
        self.assertEqual(effects['healed'], 2)
        self.assertIn('cured', effects)

    def test_throw_at_closed_door_lands_on_near_side(self):
        game, x, y = self.trap_arena()
        door, landing = [x+2, y], [x+1, y]
        game.doors = [door]
        game._door_cells = {tuple(door)}
        game.inventory = ['lure', 'smoke']
        game.terrain.append(dict(x=x+1, y=y, kind='trap', mechanism='dart', armed=True))
        game.update_visibility()
        key = ','.join(map(str, door))
        self.assertEqual(game.state()['throwRedirects'][key], landing)
        self.assertNotIn(key, game.state()['smokePreviews'])
        go(game, 'item', door, 'lure')
        self.assertFalse(game.tile_at(landing)['armed'])
        self.assertEqual(game.player['hp'], game.max_hp)
        go(game, 'item', door, 'smoke')
        self.assertTrue(game.smoke_at(landing))
        self.assertFalse(game.smoke_at(door))

    def test_lure_selects_remote_cell_and_invalid_target_does_not_consume(self):
        game,x,y = self.trap_arena()
        game.inventory = ['lure']
        enemy = game.add_enemy('bonepuppet', [x+3,y], 0, 2)
        game.plan()
        target = [x+2,y+1]
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'item', [x+10,y], 'lure')
        self.assertEqual(game.dump(), before)
        state = game.state()
        self.assertIn(target, state['lureTargets'])
        preview = state['lurePreviews'][','.join(map(str, target))]
        self.assertIn(enemy['id'], preview['listeners'])
        self.assertTrue(all(cell in state['visible'] for cell in preview['cells']))
        go(game, 'item', target, 'lure')
        self.assertEqual(enemy['sound']['target'], target)
        self.assertEqual(enemy['last_seen'], [x,y])
        self.assertEqual(game.turn, 1)
        self.assertEqual(game.inventory, [])

    def test_defeat_reports_lethal_trap_and_records_it_once(self):
        game,x,y = self.trap_arena()
        game.player['hp'] = 1
        game.terrain.append(dict(x=x+1,y=y,kind='trap',mechanism='dart',armed=True))
        go(game,'move','right')
        game = FloorDungeon.restore(game.dump())
        state = game.state()
        self.assertEqual(state['result'], 'defeat')
        self.assertEqual(state['defeatCause'], '刺针陷阱')
        self.assertEqual(state['runStats']['traps'], 1)

    def test_lure_sound_crosses_grass_but_stops_at_closed_door(self):
        for terrain in ('grass', 'door'):
            with self.subTest(terrain=terrain):
                game,x,y = self.trap_arena()
                game.inventory = ['lure']
                blocker = [x+2,y]
                if terrain == 'grass':
                    game.terrain.append(dict(x=x+2,y=y,kind='high_grass'))
                else:
                    game.doors.append(blocker)
                    game._door_cells.add(tuple(blocker))
                for row in (y-1,y+1):
                    game._wall_cells.update((column,row) for column in range(x,x+5))
                enemy = game.add_enemy('bonepuppet', [x+3,y], 0, 2)
                game.update_visibility()
                game.plan()
                go(game, 'item', [x+1,y], 'lure')
                self.assertEqual(bool(enemy.get('sound')), terrain == 'grass')

    def test_enemy_at_arm_length_prioritizes_player_over_lure(self):
        game,x,y = self.trap_arena()
        game.inventory = ['lure']
        enemy = game.add_enemy('bonepuppet', [x+1,y], 0, 2)
        game.plan()
        go(game, 'item', [x,y+1], 'lure')
        self.assertNotIn('sound', enemy)
        self.assertEqual(enemy['intent']['action'], 'melee')

    def test_thrown_smoke_blocks_detection_but_allows_a_locked_wave(self):
        game, x, y = self.trap_arena()
        enemy = game.add_enemy('bonepuppet', [x+4, y], 0, 2)
        target = [x+2, y]
        game.inventory = ['smoke']
        enemy['intent'] = dict(action='wave', label='出波', cells=game.ray([x+4,y], 'left'))
        go(game, 'item', target, 'smoke')
        self.assertEqual(game.player['hp'], 4)
        self.assertEqual(game.smoke_at(target), 3)
        self.assertNotIn('last_seen', enemy)
        self.assertIn([x,y], game.ray([x+4,y], 'left'))
        game = FloorDungeon.restore(game.dump())
        self.assertEqual(game.smoke_at(target), 3)
        for _ in range(3):
            go(game, 'guard')
        self.assertFalse(game.state()['smokeCells'])
        self.assertEqual(game.enemies[0]['intent']['action'], 'notice')

    def test_recall_evades_locked_melee_and_preserves_state(self):
        game, x, y = self.trap_arena()
        game.inventory = ['recall']
        place(game, (x+2, y))
        enemy = game.add_enemy('bonepuppet', [x+3,y], 0, 2)
        enemy['intent'] = dict(action='melee', label='攻击', cells=[[x+2,y]])
        game.player['energy'] = 2
        go(game, 'item', choice='recall')
        self.assertEqual([game.player['x'],game.player['y']], [x,y])
        self.assertEqual(game.player['hp'], 5)
        self.assertEqual(game.player['energy'], 2)
        self.assertFalse(game.inventory)

    def test_recall_rejects_contested_destination_without_consuming(self):
        game, x, y = self.trap_arena()
        game.inventory = ['recall']
        place(game, (x+2, y))
        enemy = game.add_enemy('bonepuppet', [x+1,y], 0, 2)
        enemy['intent'] = dict(action='move', label='移动', cells=[], target=[x,y])
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'item', choice='recall')
        self.assertEqual(game.dump(), before)

    def test_recall_rejects_known_attack_at_entrance_without_consuming(self):
        for hazard in ('ground_fire', 'bonebursts', 'returning', 'attack'):
            with self.subTest(hazard=hazard):
                game, x, y = self.trap_arena()
                entrance = [x, y]
                place(game, (x+2, y))
                game.inventory = ['recall']
                if hazard == 'ground_fire':
                    game.ground_fire = [dict(x=x, y=y, spread=0)]
                elif hazard == 'bonebursts':
                    game.bonebursts = [[entrance]]
                elif hazard == 'returning':
                    game.returning = [dict(owner='enemy', cells=[entrance], damage=1)]
                else:
                    enemy = game.add_enemy('bonepuppet', [x+3, y], 0, 2)
                    enemy['intent'] = dict(action='area', cells=[entrance])
                self.assertEqual(game.state()['entrance'], entrance)
                before = game.dump()
                with self.assertRaises(ValueError):
                    go(game, 'item', choice='recall')
                self.assertEqual(game.dump(), before)

    def test_ankh_revives_once_from_poison_and_combat(self):
        game, x, y = self.trap_arena()
        game.inventory = ['ankh']
        game.player['hp'] = 1
        game.poisoned = True
        enemy = game.add_enemy('bonepuppet', [x+1,y], 0, 2)
        enemy['intent'] = dict(action='melee', label='攻击', cells=[[x,y]])
        go(game, 'search')
        self.assertIsNone(game.result)
        self.assertIsNone(game.defeat_cause)
        self.assertEqual(game.player['hp'], 2)
        self.assertFalse(game.inventory)
        self.assertFalse(game.poisoned)
        game = FloorDungeon.restore(game.dump())
        game.player['hp'] = 1
        game.poisoned = True
        go(game, 'search')
        self.assertEqual(game.result, 'defeat')

    def test_ankh_cannot_be_manually_used_or_save_a_fall(self):
        game, x, y = self.trap_arena()
        game.inventory = ['ankh']
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'item', choice='ankh')
        self.assertEqual(game.dump(), before)
        game.terrain.append(dict(x=x+1,y=y,kind='fragile',stage=1))
        game.player['hp'] = 1
        go(game, 'move', 'right')
        self.assertEqual(game.defeat_cause, '坠入深渊')
        self.assertEqual(game.inventory, ['ankh'])

    def test_full_health_dew_is_saved_and_only_needed_dew_is_spent(self):
        game, x, y = self.trap_arena()
        game.features = [dict(id='dew-test', kind='dew', x=x+1, y=y, used=False)]
        go(game, 'move', 'right')
        self.assertEqual(game.dew, 1)
        self.assertTrue(game.features[0]['used'])
        game = FloorDungeon.restore(game.dump())
        game.dew += 1
        game.player['hp'] = 4
        go(game, 'drink_dew')
        self.assertEqual(game.player['hp'], 5)
        self.assertEqual(game.dew, 1)

    def test_terror_preserves_locked_attack_and_forces_two_retreats(self):
        game, x, y = self.trap_arena()
        game.inventory = ['terror']
        enemy = game.add_enemy('bonepuppet', [x+1,y], 0, 2)
        enemy['intent'] = dict(action='melee', label='攻击', cells=[[x,y]])
        go(game, 'item', choice='terror')
        self.assertEqual(game.player['hp'], 4)
        for remaining in (2, 1):
            self.assertEqual(enemy['fear'], remaining)
            self.assertIn('惊退', enemy['intent']['label'])
            go(game, 'guard')
        self.assertNotIn('fear', enemy)

    def test_terror_does_not_consume_against_a_boss(self):
        game, x, y = self.trap_arena()
        game.rooms_data[0]['kind'] = 'boss'
        game.inventory = ['terror']
        game.add_enemy('bonepuppet', [x+1,y], 0, 2)
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'item', choice='terror')
        self.assertEqual(game.dump(), before)

    def test_alchemy_checks_duplicate_ingredients_and_combat_before_consuming(self):
        game, x, y = self.trap_arena()
        game.inventory = ['grass_seed']
        game.dew = 1
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'craft', choice='heal')
        self.assertEqual(game.dump(), before)
        game.inventory.append('grass_seed')
        game.add_enemy('bonepuppet', [x+2,y], 0, 2)
        game.update_visibility()
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'craft', choice='heal')
        self.assertEqual(game.dump(), before)
        game.enemies.clear()
        go(game, 'craft', choice='heal')
        self.assertEqual((game.inventory, game.dew, game.turn), (['heal'], 0, 1))

    def test_recipe_counts_materials_and_leaves_output_at_full_capacity(self):
        game, _, _ = self.trap_arena()
        game.bag_relics = [5]
        game.inventory = ['ankh'] * (game.bag_capacity - 1) + ['grass_seed'] * 3
        game.dew = 2
        recipe = next(r for r in game.state()['recipes'] if r['id'] == 'heal')
        self.assertEqual(recipe['ingredients'][0]['owned'], 3)
        self.assertEqual(recipe['batches'], 1)
        self.assertEqual(recipe['reason'], '')

        go(game, 'craft', choice='heal')
        self.assertEqual(len(game.state()['bagSlots']), game.bag_capacity)
        self.assertNotIn('heal', game.inventory)
        game = FloorDungeon.restore(game.dump())
        ground, = game.state()['groundItems']
        self.assertEqual(ground['items'][0]['id'], 'heal')
        recipe = next(r for r in game.state()['recipes'] if r['id'] == 'heal')
        self.assertEqual((recipe['ingredients'][0]['owned'], recipe['batches']), (1, 0))

        go(game, 'drop', choice='ankh')
        go(game, 'pickup', choice=dict(feature=ground['id'], item='heal'))
        self.assertEqual(game.inventory.count('heal'), 1)

    def test_echo_smoke_both_conceals_and_draws_enemies_to_its_landing(self):
        game, x, y = self.trap_arena()
        game.inventory = ['smoke', 'lure']
        go(game, 'craft', choice='echo_smoke')
        self.assertEqual(game.inventory, ['echo_smoke'])
        enemy = game.add_enemy('bonepuppet', [x+4,y], 0, 2)
        target = [x+2,y]
        key = f'{target[0]},{target[1]}'
        self.assertIn(target, game.state()['smokePreviews'][key])
        self.assertIn(enemy['id'], game.state()['lurePreviews'][key]['listeners'])
        go(game, 'item', target, 'echo_smoke')
        self.assertFalse(game.inventory)
        self.assertEqual(game.smoke_at(target), 3)
        self.assertEqual(enemy['sound']['target'], target)
        self.assertNotIn('last_seen', enemy)

    def test_frost_smoke_chills_after_locked_moves_without_harming_enemies(self):
        game, x, y = self.trap_arena()
        game.inventory = ['echo_smoke', 'grass_seed']
        go(game, 'craft', choice='frost_smoke')
        target = [x+2, y]
        enemy = game.add_enemy('bonepuppet', [x+4, y], 0, 2)
        enemy.update(last_seen=[x, y], search=4,
                     intent=dict(action='move', cells=[], target=[x+3, y]))
        game.update_visibility()
        state = game.state()
        self.assertIn('frost_smoke', state['thrownItems'])
        self.assertIn([x+3, y], state['smokePreviews'][f'{x+2},{y}'])
        self.assertEqual(state['lurePreviews'], {})
        self.assertEqual(state['frostPreviews'][f'{x+2},{y}'], [enemy['id']])

        go(game, 'item', target, 'frost_smoke')
        self.assertEqual(position(enemy), (x+3, y))
        self.assertEqual(enemy['hp'], 2)
        self.assertEqual(enemy['intent']['action'], 'wait')
        self.assertIn('冻结', enemy['intent']['label'])
        self.assertEqual(game.smoke_at(target), 3)
        self.assertFalse(game.inventory)
        game = FloorDungeon.restore(game.dump())
        go(game, 'guard')
        self.assertEqual(game.enemies[0]['intent']['action'], 'move')

    def test_frost_smoke_does_not_pass_through_closed_door(self):
        game, x, y = self.trap_arena()
        target = [x+2, y]
        door = [x+3, y]
        game.inventory = ['frost_smoke']
        game.doors.append(door)
        game._door_cells.add(tuple(door))
        game.update_visibility()
        self.assertNotIn(door, game.state()['smokePreviews'][f'{x+2},{y}'])
        go(game, 'item', target, 'frost_smoke')
        self.assertEqual(game.smoke_at(door), 0)

    def test_planted_roots_survive_reload_and_stop_a_pursuer_once(self):
        game, x, y = self.trap_arena()
        game.inventory = ['grass_seed']
        enemy = game.add_enemy('bonepuppet', [x+3,y], 0, 2)
        enemy.update(last_seen=[x,y], search=4, intent=dict(action='move', label='追击', target=[x+2,y], cells=[]))
        target = [x+1,y]
        self.assertIn(target, game.state()['plantTargets'])
        go(game, 'plant', target)
        self.assertFalse(game.inventory)
        self.assertEqual(game.tile_at(target)['kind'], 'root_plant')
        game = FloorDungeon.restore(game.dump())
        # Move away so the enemy tries to keep moving after entering the roots.
        go(game, 'move', 'left')
        enemy = game.enemies[0]
        self.assertEqual([enemy['x'], enemy['y']], target)
        self.assertIsNone(game.tile_at(target))
        self.assertEqual(enemy['intent']['label'], '缠根 · 本拍无法移动')
        go(game, 'guard')
        self.assertEqual(enemy['intent']['action'], 'move')

    def test_planting_on_existing_terrain_keeps_the_seed_and_turn(self):
        game, x, y = self.trap_arena()
        game.inventory = ['grass_seed']
        game.terrain.append(dict(x=x+1,y=y,kind='trap',armed=True,mechanism='dart'))
        game.update_visibility()
        target = [x+1,y]
        self.assertNotIn(target, game.state()['plantTargets'])
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'plant', target)
        self.assertEqual(game.dump(), before)

    def test_sungrass_is_saved_for_injury_and_heals_on_entry(self):
        game, x, y = self.trap_arena()
        game.inventory = ['sun_seed']
        before = game.dump()
        with self.assertRaises(ValueError):
            go(game, 'item', choice='sun_seed')
        self.assertEqual(game.dump(), before)
        target = [x+1,y]
        go(game, 'plant', target, 'sun_seed')
        go(game, 'move', 'right')
        self.assertEqual(game.tile_at(target)['kind'], 'sun_plant')
        go(game, 'move', 'left')
        game.player['hp'] = 3
        go(game, 'move', 'right')
        self.assertEqual(game.player['hp'], 5)
        self.assertIsNone(game.tile_at(target))
