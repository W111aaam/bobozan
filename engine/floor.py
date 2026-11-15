from collections import Counter, deque
from copy import deepcopy
from random import Random
import re
from dungeon import Dungeon, DIRS, NAMES, UPGRADES
from mechanics import ExpeditionMechanics, PROFILES, position
from enemy_design import ENEMY_DESIGNS, ENEMY_LOOT, FIXED_ENEMY_LOOT, REINFORCEMENTS, enemy_health, enemy_attack_bonus
from growth import Growth, CLASSES, GROWTH_ACTIONS, TALENT_FLOORS, BAG_RELICS
from layout import LAST_FLOOR, REGIONS, ROOM_LABELS, RELIC_FLOORS, SPRING_FLOORS, chapter, generate_layout

DEW_CAPACITY = 3
HISTORY_LIMIT = 20

ITEMS = {
    'terror': ('惊退卷轴', '让视野内可惊退的敌人接下来两拍尝试远离你。守关者、伪装宝箱、产巢和沟渠鱼免疫。'),
    'ankh': ('护命符', '放在背包里，受到致命伤时自动消耗，回复至 2 生命并解除中毒与霜冻。坠落时不会触发。'),
    'recall': ('回程卷轴', '消耗一拍，传送到本层入口。入口有敌人或站位不安全时无法使用。'),
    'chart': ('测绘卷轴', '显示本层已连通的房间、门和阶梯。不会扩大视野或揭开未发现的暗门。'),
    'sun_seed': ('阳草种子', '种下阳草。受伤时踩上可恢复 2 生命，敌人踩上会毁掉它。'),
    'grass_seed': ('响草种子', '可投作诱饵，也能种下缠根。敌人踩上缠根后，下拍无法移动。'),
    'heal': ('疗愈药剂', '恢复 2 生命并解除当前中毒。'),
    'frost_smoke': ('凝霜雾弹', '投出持续三拍的烟雾。爆开时扑灭范围内的地火，限制敌人的下拍移动，并冰封浅水两拍。'),
    'echo_smoke': ('响雾弹', '投出持续三拍的烟雾，同时吸引附近敌人调查落点。'),
    'smoke': ('烟雾弹', '投出一团持续三拍的烟雾。烟雾挡视线，能量波可以穿过。'),
    'lure': ('诱饵', '投到四格内的可见空地，让附近敌人搜寻落点。落在陷阱上时会触发机关。'),
}
GROUND_SUPPLIES = {
    'kit': ('heal',), 'smoke': ('smoke',), 'cache': ('smoke', 'lure'), 'lure_cache': ('lure',),
    **{kind: (kind,) for kind in ('chart', 'recall', 'ankh', 'terror', 'sun_seed',
                                  'echo_smoke', 'grass_seed')},
}
RECIPES = {
    'heal': (('grass_seed', 'grass_seed'), 1),
    'echo_smoke': (('smoke', 'lure'), 0),
    'frost_smoke': (('echo_smoke', 'grass_seed'), 0),
}
PLANTS = {'grass_seed': ('root_plant', '缠根'), 'sun_seed': ('sun_plant', '阳草')}
SMOKE_ITEMS = ('smoke', 'echo_smoke', 'frost_smoke')
THROWN_ITEMS = ('lure', 'grass_seed', *SMOKE_ITEMS)
SOUND_ITEMS = ('lure', 'grass_seed', 'echo_smoke')

FLOOR_UPGRADES = {
    'echo': '每成功攒三次，第三次额外获得 1 能量。',
    'heart': '每个区域首次有效格挡回复 1 生命。',
}

WAVE_RELICS = {
    'parallel': ('并行束', '主束右侧一格额外发射一束，副束伤害 −1（最低 1）；侧边被挡时不会发射。'),
    'double': ('双击扳机', '同方向再发射一次，第二束造成一半伤害（最低 1），可越过刚击倒的目标。'),
    'impact': ('冲击波', '主束造成伤害后，在本拍攻击结算后推开存活目标一格。可推入裂地。'),
    'burn': ('灼烧', '主束点燃高草并融化冰封浅水。命中的目标接下来两拍各受 1 伤，再次点燃刷新时间，浅水可熄灭灼烧。'),
    'freeze': ('冰冻', '主束造成伤害时叠一层霜。两层霜会冻结敌人的下一次移动。'),
    'blink': ('飞雷神', '出波后传送到主束最远的空地格，再结算敌人攻击。跳过致死裂地，需要穿透遗物。'),
}


class FloorDungeon(Growth, ExpeditionMechanics, Dungeon):
    upgrade_catalog = {**UPGRADES, **WAVE_RELICS}
    extra_actions = ('item', 'unlock', 'reflect', 'equip', 'tune', 'search', 'drop', 'pickup', 'drink_dew', 'craft', 'plant')

    def __init__(self, seed=None, hero_class=None):
        if hero_class is not None and hero_class not in CLASSES:
            raise ValueError('请选择有效的职业。')
        self.counter = False
        self.depth = 1
        self.enemy_heal_region = None
        self.hero_rank = 0
        self.heart_region = None
        self.dew = 0
        self.history = []
        self.result_archived = False
        self.defeat_cause = None
        self.run_stats = dict(defeated=0, secrets=0, traps=0)
        self.init_growth(hero_class)
        super().__init__(seed)

    @classmethod
    def restore(cls, data):
        game = super().restore(data)
        game.heart_region = getattr(game, 'heart_region', None)
        game.hero_rank = getattr(game, 'hero_rank', 0)
        game.history = getattr(game, 'history', [])
        game.result_archived = getattr(game, 'result_archived', False)
        game.dew = getattr(game, 'dew', 0)
        game.defeat_cause = getattr(game, 'defeat_cause', None)
        if not hasattr(game, 'run_stats'):
            game.run_stats = dict(defeated=0, secrets=0, traps=0)
        for enemy in game.enemies:
            distraction = enemy.pop('distracted', 0)
            if distraction and enemy.get('last_seen'):
                enemy['sound'] = dict(target=enemy.pop('last_seen'), kind='lure',
                                      remaining=distraction)
        game.floor_version = getattr(game, 'floor_version', 1)
        game.player['hp'] = min(game.player['hp'], game.max_hp)
        game._door_cells = set(map(tuple, game.doors))
        if 'depth' not in data:
            game.depth = 1
            game.echo_charges = 0
            game.heart_uses = int(game.heart_used)
            game.inventory, game.keys = [], 0
            game.smoke = game.lure = 0
            game.add_branch()
            game.update_visibility()
        if not hasattr(game, 'talent_milestones'):
            if not hasattr(game, 'talents'):
                game.init_growth()
            game.talent_milestones = [depth for depth in TALENT_FLOORS if depth <= game.depth]
            game.bag_relics = [
                depth for depth in BAG_RELICS
                if depth < game.depth or (depth == game.depth and any(
                    room['kind'] == 'boss' and room['cleared'] for room in game.rooms_data))
            ]
            game.__dict__.pop('talent_points', None)
            game.__dict__.pop('growth_floors', None)
        game._wall_cells = set(map(tuple, game.walls))
        if not hasattr(game, 'mechanics_version'):
            game.setup_mechanics(populate=False)
            game.update_visibility()
            game.plan()
        if 'discovered_features' not in data:
            explored = set(map(tuple, game.explored))
            game.discovered_features = [f['id'] for f in game.features if (f['x'], f['y']) in explored]
        if 'secret_clues' not in data:
            game.secret_clues = game.nearby_secrets()
        for room in game.rooms_data:
            room['name'] = ROOM_LABELS[room['kind']]
        return game

    def archive_result(self):
        if self.result not in ('victory', 'defeat') or self.result_archived:
            return
        record = dict(seed=self.seed, heroClass=self.hero_class, depth=self.depth,
                      result=self.result, turns=self.turn, relics=len(self.upgrades),
                      cause=self.defeat_cause if self.result == 'defeat' else None,
                      stats=self.run_stats.copy())
        self.history = [record, *self.history[:HISTORY_LIMIT - 1]]
        self.result_archived = True

    def dump(self):
        return deepcopy({k: v for k, v in self.__dict__.items() if not k.startswith('_')})

    def add_branch(self):
        self.lock = [5, 24]
        self.locked = True
        self.features.extend([
            dict(id='key', kind='key', x=27, y=5, used=False),
            dict(id='kit', kind='kit', x=6, y=19, used=False),
            dict(id='cache', kind='cache', x=5, y=26, used=False),
        ])
        self.height = 29
        self.walls.extend([x, y] for y in range(25, 29) for x in range(self.width)
                          if not (4 <= x <= 6 and 25 <= y <= 27))
        self.walls.remove(self.lock)
        self.walls.remove([5, 23])
        for cell in ([27, 5], [6, 19]):
            if cell in self.walls:
                self.walls.remove(cell)
        self._wall_cells = set(map(tuple, self.walls))

    def enter_room(self):
        self.floor_version = 3
        layout = generate_layout(self.seed, self.depth)
        x, y = layout.pop('start')
        spawn = layout.pop('spawn')
        self.floor_theme = None
        self.shortcut_doors = []
        self.__dict__.update(layout)
        self.player.update(x=x, y=y, hp=min(self.player['hp'], self.max_hp))
        previous_rank = self.hero_rank
        self.hero_rank = chapter(self.depth)
        if self.hero_rank > previous_rank and self.player['hp'] > 0:
            gain = self.hero_rank - previous_rank
            self.note(f'进入新区域，生命上限 +{gain}。')
        self.recall_cell = [x, y]
        self.effects = []
        self.echo_charges = self.heart_uses = 0
        self.inventory = getattr(self, 'inventory', [])
        self.keys = 0
        self.locked = self.lock is not None
        self.smoke = 0
        self.smoke_clouds = {}
        self.echo_used = self.heart_used = False
        self.explored = []
        self.discovered_features = []
        self.secret_clues = []
        self.seen_statues = []
        self.enemy_loot_count = 0
        self.mapped = []
        self.visible = []
        self.enemies = []
        for home, kind, x, y in spawn:
            hp = enemy_health(kind, self.depth, self.rooms_data[home]['kind'] == 'boss')
            self.enemies.append(dict(id=len(self.enemies), kind=kind, name=PROFILES[kind][0] if kind in PROFILES else NAMES[kind],
                                     home=home, x=x, y=y, hp=hp, maxHp=hp, energy=0, phase=0,
                                     regular_loot=self.depth % 5 != 0))
        if self.depth > 1:
            roaming_kinds = REINFORCEMENTS[chapter(self.depth)]
            patrol = next((e for e in self.enemies if e['kind'] in roaming_kinds
                           and self.rooms_data[e['home']]['kind'] == 'standard'), None)
            if patrol:
                patrol['patrol'] = True
        self._door_cells = set(map(tuple, self.doors))
        self.setup_mechanics()
        self.room=0
        self.cleared=True
        self.update_visibility()
        self.plan()
        self.note(f'进入第 {self.depth} 层。可以自由往返，安全时可攒能量。')
        if self.depth % 5 == 4:
            self.note('本层阶梯由战斗区的守卫封锁。')

    @property
    def max_hp(self):
        return 5 + self.hero_rank

    @property
    def cap(self):
        return super().cap + int('reserve' in self.talents)

    def restrict_safe_actions(self):
        return False

    def room_at(self,p):
        for r in self.rooms_data:
            x1,y1,x2,y2=r['bounds']
            if x1<p[0]<x2 and y1<p[1]<y2:return r['id']
        return -1

    def walkable(self,pos):
        return 0<=pos[0]<self.width and 0<=pos[1]<self.height and tuple(pos) not in self._wall_cells and not self.solid_terrain(pos) and not (self.locked and list(pos) == self.lock)

    def door_closed(self, pos):
        x, y = pos
        return ((x, y) in self._door_cells
                and (x, y) != (self.player['x'], self.player['y'])
                and not any((e['x'], e['y']) == (x, y) and e['hp'] > 0 for e in self.enemies))

    def doorway_vertical(self, cell):
        x, y = cell
        return sum((x + dx, y) in self._wall_cells for dx in (-1, 1)) > sum(
            (x, y + dy) in self._wall_cells for dy in (-1, 1))

    def smoke_at(self, cell):
        return getattr(self, 'smoke_clouds', {}).get(','.join(map(str, cell)), 0)

    def smoke_area(self, target):
        x, y = target
        cells = [list(target)]
        for dx, dy in DIRS.values():
            cell = [x + dx, y + dy]
            if self.walkable(cell) and not self.door_closed(cell):
                cells.append(cell)
        return cells

    def can_see_player(self, cell, player):
        if self.smoke:
            return False
        distance = abs(cell[0]-player[0]) + abs(cell[1]-player[1])
        if distance > 1 and (self.smoke_at(cell) or self.smoke_at(player)):
            return False
        return self.has_sight(cell, player, include_smoke=True)

    def blocks_sight(self, pos, ignore_grass=False, include_smoke=False):
        tile = self.tile_at(pos)
        return (not self.walkable(pos) or self.door_closed(pos)
                or (include_smoke and self.smoke_at(pos))
                or (not ignore_grass and tile is not None and tile['kind'] == 'high_grass'))

    def has_sight(self,start,end,ignore_grass=False,include_smoke=False):
        """Symmetric supercover line; no visibility through diagonal wall corners."""
        x,y=start;tx,ty=end
        nx,ny=abs(tx-x),abs(ty-y)
        sx=1 if tx>x else -1;sy=1 if ty>y else -1
        ix=iy=0
        while ix<nx or iy<ny:
            decision=(1+2*ix)*ny-(1+2*iy)*nx
            if decision==0:
                if self.blocks_sight((x+sx,y), ignore_grass, include_smoke) or self.blocks_sight((x,y+sy), ignore_grass, include_smoke):return False
                x+=sx;y+=sy;ix+=1;iy+=1
            elif decision<0:x+=sx;ix+=1
            else:y+=sy;iy+=1
            if (x,y)==(tx,ty):return True
            if self.blocks_sight((x,y), ignore_grass, include_smoke):return False
        return True

    def update_visibility(self):
        px,py=self.player['x'],self.player['y']
        self.visible=[[x,y] for y in range(max(0,py-6),min(self.height,py+7))
                      for x in range(max(0,px-6),min(self.width,px+7))
                      if (x-px)**2+(y-py)**2<=36 and self.has_sight((px,py),(x,y))]
        visible = set(map(tuple, self.visible))
        known = set(map(tuple, self.explored)) | visible
        self.explored = [list(cell) for cell in sorted(known)]
        discovered = set(getattr(self, 'discovered_features', []))
        discovered.update(f['id'] for f in self.features if (f['x'], f['y']) in visible)
        self.discovered_features = sorted(discovered)
        clues = set(map(tuple, getattr(self, 'secret_clues', [])))
        clues.update(map(tuple, self.nearby_secrets()))
        self.secret_clues = [cell for cell in getattr(self, 'secret_doors', []) if tuple(cell) in clues]
        statues = set(getattr(self, 'seen_statues', []))
        self.seen_statues = [e['id'] for e in self.enemies if e.get('dormant')
                             and (e['id'] in statues or tuple(position(e)) in visible)]
        if hasattr(self, 'terrain_memory'):
            for cell in self.visible:
                key = ','.join(map(str, cell))
                tile = self.tile_at(cell)
                if tile and not tile.get('hidden'):
                    self.terrain_memory[key] = deepcopy(tile)
                else:
                    self.terrain_memory.pop(key, None)

    def charge_amount(self):
        if 'echo' not in self.upgrades:
            return 1
        self.echo_charges += 1
        interval = 2 if 'bag' in self.upgrades else 3
        return 1 + (self.echo_charges % interval == 0)

    def use_heart(self):
        region = chapter(self.depth)
        if self.heart_region == region or not 0 < self.player['hp'] < self.max_hp:
            return False
        self.heart_region = region
        return True

    def plan(self):
        self._enemy_hazards = self.enemy_hazards()
        try:
            self.plan_floor_enemies()
        finally:
            del self._enemy_hazards

    def enemy_hazards(self):
        hazardous = {tuple(position(tile)) for tile in getattr(self, 'ground_fire', [])}
        hazardous.update(tuple(position(tile)) for tile in self.terrain
                         if (tile['kind'] == 'fragile' and tile['stage'] >= 1)
                         or (tile['kind'] == 'trap' and tile['armed'] and not tile.get('hidden')))
        return hazardous

    def step_toward(self, enemy):
        avoid = getattr(self, '_enemy_hazards', None)
        return super().step_toward(enemy, self.enemy_hazards() if avoid is None else avoid)

    def enemy_safe_ground(self, cell):
        avoid = getattr(self, '_enemy_hazards', None)
        return self.walkable(cell) and tuple(cell) not in (
            self.enemy_hazards() if avoid is None else avoid)

    def plan_floor_enemies(self):
        player = [self.player['x'], self.player['y']]
        active = []
        for enemy in self.enemies:
            cell = (enemy['x'], enemy['y'])
            distance_squared = (cell[0] - player[0]) ** 2 + (cell[1] - player[1]) ** 2
            sees = distance_squared <= 36 and self.can_see_player(cell, player)
            if self.plan_side_passive(enemy, sees, player):
                continue
            sound = enemy.get('sound')
            follows_sound = sound and distance_squared > 1 and (
                sound['kind'] == 'lure' or sound.get('priority'))
            if sees and not follows_sound:
                enemy.pop('sound', None)
                first_notice = not enemy.get('last_seen')
                enemy.update(last_seen=player, search=4)
                if first_notice:
                    enemy['intent'] = dict(action='notice', label='察觉动静 · 本拍不攻击', cells=[])
                else:
                    active.append(enemy)
                continue
            if sound and self.plan_sound(enemy, player, sound):
                continue
            target = enemy.get('last_seen')
            enemy['intent'] = dict(action='wait', label='脱战' if not target else '搜索', cells=[])
            if not target:
                if enemy.get('patrol'):
                    self.plan_patrol(enemy, player)
                continue
            step = self.step_toward(enemy)
            if step and step != player:
                enemy['intent'] = dict(action='move', label='追踪足迹', target=step, cells=[])
            else:
                enemy['search'] -= 1
                if enemy['search'] <= 0:
                    enemy.pop('last_seen')
                    enemy['intent']['label'] = '脱战'
        super().plan(active)
        self.plan_special(active)
        self.plan_committed_enemies()
        for enemy in self.enemies:
            if enemy.get('fear', 0) and not enemy.get('dormant'):
                self.plan_fear(enemy, player)
            intent = enemy['intent']
            attack = intent['action']
            bonus = enemy_attack_bonus(enemy['kind'], self.depth, attack)
            if bonus:
                damage = intent.get('damage', 2 if attack in ('area', 'siege') else 1) + bonus
                intent['damage'] = damage
                intent['label'] = re.sub(r'\d+伤', f'{damage}伤', intent['label'], count=1)
            rooted = enemy.pop('rooted', False)
            frosted = enemy.pop('frosted', False)
            if enemy['intent']['action'] != 'move':
                continue
            if rooted:
                enemy['intent'] = dict(action='wait', label='缠根 · 本拍无法移动', cells=[])
            elif frosted or enemy.pop('frozen', False):
                enemy['intent'] = dict(action='wait', label='冻结 · 无法移动', cells=[])
                enemy.pop('frozen', None)
            elif self.mob_bound([enemy['x'], enemy['y']]) and enemy['intent'].get('mob_jump'):
                enemy['intent'] = dict(action='wait', label='蛛网 · 无法跃进', cells=[])

    def plan_patrol(self, enemy, player):
        enemy['intent']['label'] = '巡逻 · 观察四周'
        if (self.turn + enemy['id']) % 3:
            return
        occupied = {(e['x'], e['y']) for e in self.enemies}
        # Patrol within the assigned room and keep doorway landings clear.
        cells = []
        for dx, dy in DIRS.values():
            target = [enemy['x'] + dx, enemy['y'] + dy]
            x, y = target
            if (target == player or (x, y) in occupied or self.room_at(target) != enemy['home']
                    or not self.enemy_safe_ground(target) or self.unsafe_ground(target)
                    or any(abs(x - a) + abs(y - b) <= 1 for a, b in self._door_cells)):
                continue
            tile = self.tile_at(target)
            if tile and tile['kind'] in ('trap', 'high_grass', 'sun_plant', 'root_plant'):
                continue
            cells.append(target)
        if cells:
            rng = Random(self.seed + self.depth * 3079 + self.turn * 103)
            enemy['intent'] = dict(action='move', label='巡逻 · 移动一格', target=rng.choice(cells), cells=[])

    def plan_fear(self, enemy, player):
        def distance(cell):
            return abs(cell[0] - player[0]) + abs(cell[1] - player[1])

        x, y = enemy['x'], enemy['y']
        current = distance((x, y))
        occupied = {(other['x'], other['y']) for other in self.enemies}
        for dx, dy in DIRS.values():
            target = [x + dx, y + dy]
            if (distance(target) > current and tuple(target) not in occupied
                    and self.enemy_safe_ground(target) and not self.unsafe_ground(target)):
                enemy['intent'] = dict(action='move', label='惊退 · 远离玩家', target=target, cells=[])
                return
        enemy['intent'] = dict(action='wait', label='惊退 · 无路可退', cells=[])

    def plan_sound(self, enemy, player, sound):
        if sound['remaining'] <= 0:
            enemy.pop('sound')
            return False
        sound['remaining'] -= 1
        source = '诱饵' if sound['kind'] == 'lure' else '警报'
        step = self.step_toward(dict(enemy, last_seen=sound['target']))
        if step and step != player:
            enemy['intent'] = dict(action='move', label=f'循声调查 · {source}', target=step, cells=[])
        else:
            enemy['intent'] = dict(action='wait', label=f'停下搜查 · {source}', cells=[])
            # The enemy spends this beat investigating before returning to its previous pursuit.
            sound['remaining'] = 0
        return True

    def lure_audible_cells(self, target):
        """Sound crosses grass and corners, but stops at walls and closed doors."""
        reached = {tuple(target)}
        frontier = reached
        for _ in range(4):
            frontier = {(x+dx, y+dy) for x,y in frontier for dx,dy in DIRS.values()
                        if (x+dx, y+dy) not in reached
                        and self.walkable((x+dx, y+dy)) and not self.door_closed((x+dx, y+dy))}
            reached.update(frontier)
        return reached

    @staticmethod
    def can_investigate_sound(enemy):
        return (enemy['hp'] > 0 and not enemy.get('disguised') and not enemy.get('stolen')
                and not enemy.get('dormant')
                and enemy['kind'] not in ('broodnest', 'canalfish'))

    def lure_preview(self, target, visible):
        audible = self.lure_audible_cells(target)
        visible_sound = audible & visible
        listeners = [enemy['id'] for enemy in self.enemies
                     if (enemy['x'], enemy['y']) in visible_sound
                     and self.can_investigate_sound(enemy)]
        return dict(cells=[list(cell) for cell in sorted(visible_sound)], listeners=listeners)

    def frost_smoke_preview(self, area, enemies):
        occupied = {tuple(position(enemy)) for enemy in enemies} | {tuple(position(self.player))}
        moves = Counter(tuple(enemy['intent']['target']) for enemy in enemies
                        if enemy['intent']['action'] == 'move' and 'target' in enemy['intent'])
        chilled = []
        for enemy in enemies:
            if enemy.get('disguised'):
                continue
            cell = tuple(position(enemy))
            intent = enemy['intent']
            if intent['action'] == 'move':
                if 'target' not in intent:
                    continue
                target = tuple(intent['target'])
                if target not in occupied and moves[target] == 1:
                    cell = target
            if cell in area:
                chilled.append(enemy['id'])
        return chilled

    def alert_by_sound(self, enemy, target, kind):
        if not self.can_investigate_sound(enemy):
            return
        # The cue changes the next plan, leaving this beat's locked action intact.
        enemy['sound'] = dict(target=list(target), kind=kind, remaining=4)

    def lure_targets(self):
        x, y = self.player['x'], self.player['y']
        return [cell for cell in self.visible
                if 0 < (x-cell[0])**2 + (y-cell[1])**2 <= 16
                and self.walkable(cell) and not self.door_closed(cell)
                and not self.unsafe_ground(cell)
                and not any((e['x'],e['y']) == tuple(cell) for e in self.enemies)]

    def plant_targets(self):
        targets = []
        for cell in self.lure_targets():
            tile = self.tile_at(cell)
            if tuple(cell) not in self._door_cells and (tile is None or tile.get('hidden')):
                targets.append(cell)
        return targets

    def recall_destination(self):
        target = getattr(self, 'recall_cell', None) or self.rooms_data[0].get('anchor')
        if not target or not self.walkable(target) or self.unsafe_ground(target):
            return None
        tile = self.tile_at(target)
        if tile and tile['kind'] == 'trap' and tile['armed']:
            return None
        if target == [self.player['x'], self.player['y']]:
            return None
        for enemy in self.enemies:
            intent = enemy['intent']
            if ([enemy['x'], enemy['y']] == target or
                    (intent['action'] == 'move' and intent.get('target') == target)):
                return None
        return list(target)

    def crafting_block(self):
        if self.has_threat() or self.returning or self.movement_locked() or any(
                [enemy['x'], enemy['y']] in self.visible and not enemy.get('disguised') and not enemy.get('dormant')
                for enemy in self.enemies):
            return '脱战后才能制作。'
        return ''

    def recipe_details(self, output, owned, crafting_block):
        ingredients, dew = RECIPES[output]
        costs = Counter(ingredients)
        limits = [owned[item] // count for item, count in costs.items()]
        if dew:
            limits.append(self.dew // dew)
        batches = min(limits)
        return dict(id=output, name=ITEMS[output][0], description=ITEMS[output][1],
                    ingredients=[dict(name=ITEMS[item][0], count=count, owned=owned[item])
                                 for item, count in costs.items()],
                    dew=dew, batches=batches,
                    reason=crafting_block or ('材料不足。' if not batches else ''))

    def alert_lure_listeners(self, target):
        audible = self.lure_audible_cells(target)
        for enemy in self.enemies:
            if (enemy['x'], enemy['y']) in audible:
                self.alert_by_sound(enemy, target, 'lure')

    def item_stack_limit(self, item):
        return 3 if 5 in self.bag_relics and item in PLANTS else 1

    def packed_inventory(self):
        slots = []
        for item in self.inventory:
            limit = self.item_stack_limit(item)
            slot = next((slot for slot in slots if slot['id'] == item and slot['count'] < limit), None)
            if slot is None:
                slots.append(dict(id=item, count=1, limit=limit))
            else:
                slot['count'] += 1
        return slots

    def can_pack(self, item):
        slots = self.packed_inventory()
        return len(slots) < self.bag_capacity or any(
            slot['id'] == item and slot['count'] < slot['limit'] for slot in slots)

    @staticmethod
    def ground_items(feature):
        if feature['kind'] == 'dropped_item':
            return (feature['item'],)
        if feature['kind'] == 'cache' and 'remaining_items' in feature:
            return tuple(feature['remaining_items'])
        return GROUND_SUPPLIES.get(feature['kind'], ())

    def collect_ground_items(self, feature, selected=None):
        items = self.ground_items(feature)
        collected = []
        for item in (selected,) if selected is not None else items:
            if self.can_pack(item):
                self.inventory.append(item)
                collected.append(item)
        if not collected:
            return
        if len(collected) < len(items):
            remaining = [item for item in items if item not in collected]
            if remaining == ['lure']:
                feature['kind'] = 'lure_cache'
            feature['remaining_items'] = remaining
        else:
            feature['used'] = True
        verb = '拾回' if feature['kind'] == 'dropped_item' else '拾取'
        self.note(verb + '、'.join(ITEMS[item][0] for item in collected) + '。')

    def ground_supplies_here(self):
        return [f for f in self.features if not f['used']
                and position(f) == position(self.player) and self.ground_items(f)]

    def prepare_action(self, action, choice):
        if action == 'plant':
            if choice is None:
                choice = 'grass_seed'
            if not isinstance(choice, str) or choice not in PLANTS or choice not in self.inventory:
                raise ValueError('请选择背包中的种子。')
            if self._item_target not in self.plant_targets():
                raise ValueError('请选择四格内可播种的空地。')
        if action == 'craft':
            if not isinstance(choice, str) or choice not in RECIPES:
                raise ValueError('请选择有效的配方。')
            reason = self.recipe_details(choice, Counter(self.inventory), self.crafting_block())['reason']
            if reason:
                raise ValueError(reason)
        if action == 'drink_dew' and (not self.dew or self.player['hp'] >= self.max_hp):
            raise ValueError('有存露且生命未满时才能饮用。')
        if action in ('item', 'drop') and choice not in self.inventory:
            raise ValueError('背包中没有这件道具。')
        if action == 'item' and choice in THROWN_ITEMS:
            target = getattr(self, '_item_target', None)
            if (choice != 'smoke' or target is not None) and target not in self.lure_targets():
                raise ValueError('请选择四格内的可见空地。')
        if action == 'item' and choice == 'terror':
            affected = [enemy for enemy in self.enemies
                        if [enemy['x'], enemy['y']] in self.visible
                        and not enemy.get('disguised')
                        and not enemy.get('dormant')
                        and self.rooms_data[enemy['home']]['kind'] != 'boss'
                        and enemy['kind'] not in ('broodnest', 'canalfish')]
            if not affected:
                raise ValueError('视野里没有可惊退的敌人。')
        if action == 'item' and choice == 'sun_seed':
            raise ValueError('请通过播种使用阳草种子。')
        if action == 'item' and choice == 'ankh':
            raise ValueError('护命符在受到致命伤时自动触发。')
        if action == 'item' and choice == 'recall':
            destination = self.recall_destination()
            if destination is None:
                raise ValueError('无法回到本层入口。')
        if action == 'pickup':
            feature_id = choice.get('feature') if isinstance(choice, dict) else choice
            selected = choice.get('item') if isinstance(choice, dict) else None
            cell_supplies = self.ground_supplies_here()
            pickup_all = isinstance(choice, dict) and choice.get('all') is True and len(choice) == 1
            pickups = cell_supplies if pickup_all else [f for f in cell_supplies if f['id'] == feature_id][:1]
            if not pickups or (isinstance(choice, dict) and not pickup_all
                               and selected not in self.ground_items(pickups[0])):
                raise ValueError('这格没有这件可拾取的物品。')
            if not any(self.can_pack(item) for f in pickups for item in self.ground_items(f)
                       if selected is None or selected == item):
                raise ValueError('背包已满。')
        self.prepare_mechanics(action, choice)
        self._movement_locked = self.movement_locked()
        self.player_frosted = self.player_snared = False
        if action == 'plant':
            x, y = self._item_target
            tile = self.tile_at((x, y))
            if tile and tile.pop('hidden', False):
                self.note('播种时发现了陷阱，种子已收回。')
                return
            kind, name = PLANTS[choice]
            self.inventory.remove(choice)
            self.terrain.append(dict(kind=kind, x=x, y=y))
            self.note('种下' + name + '。')
            return
        if action == 'craft':
            ingredients, dew = RECIPES[choice]
            for ingredient in ingredients:
                self.inventory.remove(ingredient)
            self.dew -= dew
            name = ITEMS[choice][0]
            if self.can_pack(choice):
                self.inventory.append(choice)
                self.note('制作了' + name + '。')
            else:
                self.features.append(dict(id=f'crafted-{self.turn}', kind='dropped_item', item=choice,
                                          x=self.player['x'], y=self.player['y'], used=False))
                self.note('制作了' + name + '。背包已满，成品放在脚下。')
            return
        if action == 'drink_dew':
            amount = min(self.dew, self.max_hp - self.player['hp'])
            self.dew -= amount
            self.player['hp'] += amount
            self.note(f'饮用露珠，恢复 {amount} 生命。')
        if action == 'search':
            self.search_surroundings()
        if action == 'unlock':
            self.keys -= 1
            self.locked = False
            self.note('打开库房支路。')
        if action == 'pickup':
            for pickup in pickups:
                self.collect_ground_items(pickup, selected)
            return
        if action == 'drop':
            self.inventory.remove(choice)
            self.features.append(dict(id=f'dropped-{self.turn}', kind='dropped_item', item=choice,
                                      x=self.player['x'], y=self.player['y'], used=False))
            self.note('放下' + ITEMS[choice][0] + '。')
            return
        if action != 'item':
            return
        self.inventory.remove(choice)
        if choice == 'heal':
            self.player['hp'] = min(self.max_hp, self.player['hp'] + 2)
            if getattr(self, 'poisoned', False):
                self.poisoned = False
                self.note('疗愈药剂解除了中毒。')
        elif choice in SMOKE_ITEMS:
            if target is None:
                # Older clients can still use the original personal smoke effect.
                self.smoke = 4
            else:
                clouds = getattr(self, 'smoke_clouds', {}).copy()
                self._thrown_smoke_area = self.smoke_area(target)
                for cell in self._thrown_smoke_area:
                    clouds[','.join(map(str, cell))] = 4
                self.smoke_clouds = clouds
                if choice == 'echo_smoke':
                    self.alert_lure_listeners(target)
        elif choice == 'chart':
            self.chart_floor()
        elif choice == 'recall':
            self._recall_landing = destination
        elif choice == 'terror':
            for enemy in affected:
                enemy['fear'] = 3
        else:
            self.alert_lure_listeners(target)
        self.note('使用' + ITEMS[choice][0] + '。')

    def chart_floor(self):
        # Follow public passages. Locked storage can be drawn; secret walls stay closed.
        start = (self.player['x'], self.player['y'])
        queue = [start]
        surveyed = {start}
        for x, y in queue:
            for dx, dy in DIRS.values():
                cell = (x+dx, y+dy)
                if cell in surveyed or not (0 <= cell[0] < self.width and 0 <= cell[1] < self.height):
                    continue
                surveyed.add(cell)
                if cell not in self._wall_cells:
                    queue.append(cell)
        self.mapped = [list(cell) for cell in sorted(surveyed)]
        self.note('卷轴绘出了本层的通道、房间和阶梯。')

    def nearby_secrets(self):
        x, y = self.player['x'], self.player['y']
        return [cell for cell in getattr(self, 'secret_doors', [])
                if max(abs(x-cell[0]), abs(y-cell[1])) <= 1 and cell in self.visible]

    def search_surroundings(self):
        found = self.nearby_secrets()
        origin = (self.player['x'], self.player['y'])
        visible = set(map(tuple, self.visible))
        traps = [tile for tile in self.terrain if tile.get('hidden')
                 and (tile['x'], tile['y']) in visible
                 and max(abs(tile['x'] - origin[0]), abs(tile['y'] - origin[1])) <= 2]
        for tile in traps:
            tile.pop('hidden')
        if not found and not traps:
            self.note('搜查了周围，没有发现暗门或陷阱。')
            return
        for cell in found:
            self.secret_doors.remove(cell)
            self.walls.remove(cell)
            self._wall_cells.remove(tuple(cell))
            self.doors.append(cell)
            self._door_cells.add(tuple(cell))
        if found:
            self.secret_clues = [cell for cell in getattr(self, 'secret_clues', []) if cell not in found]
            self.run_stats['secrets'] += len(found)
            shortcuts = getattr(self, 'shortcut_doors', [])
            if any(cell in shortcuts for cell in found):
                self.note('发现隐蔽通路。可以从暗门穿到另一间房。')
            if any(cell not in shortcuts for cell in found):
                self.note('发现暗门。走进去看看墙后有什么。')
        if traps:
            self.note(f'发现 {len(traps)} 处隐藏陷阱。已在地图标记。')

    def wave_damage(self, damage, target, hits):
        if hits == 0 and target['intent']['action'] == 'guard' and {'pierce', 'heavy'} <= set(self.upgrades):
            return damage
        return super().wave_damage(damage, target, hits)

    def on_block(self):
        if 'heart' in self.upgrades and 'refund' in self.upgrades:
            self.player['energy'] = min(self.cap, self.player['energy'] + 1)

    def builds(self):
        combos = [
            ('反击', ('heart', 'refund'), '成功格挡时额外获得 1 能量'),
            ('蓄能', ('echo', 'bag'), '回响改为每两次攒触发'),
            ('穿透', ('pierce', 'heavy'), '重波与普通波均无视第一个敌人的盾'),
        ]
        return [dict(name=name, requires=list(required), effect=effect,
                     active=all(k in self.upgrades for k in required))
                for name, required, effect in combos]

    def preview(self, action, direction):
        return self.preview_details(action, direction)['hits']

    def preview_details(self, action, direction):
        if action not in ('wave', 'heavy', 'reflect'):
            raise ValueError('请选择波、重波或反弹防御。')
        targets = {e['id']: e for e in self.state()['enemies'] if not e.get('disguised')}
        game = self.restore(self.dump())
        game.terrain = [tile for tile in game.terrain if not tile.get('hidden')]
        game.act(action, direction, game.version)
        hits = [{'name': e['name'], 'damage': game.preview_hits[i]}
                for i, e in targets.items() if i in game.preview_hits]
        events = []
        for tile in self.terrain:
            if [tile['x'], tile['y']] not in self.visible:
                continue
            after = game.tile_at((tile['x'], tile['y']))
            if tile.get('rotating') and after and tile['slash'] != after['slash']:
                events.append(f"镜面 ({tile['x']},{tile['y']}) 旋转为 {after['slash']}")
        if any(cell in self.visible for effect in game.effects if effect['kind'] == 'grass'
               for cell in effect['cells']):
            events.append('高草被压倒或打碎')
        if any(effect['kind'] == 'trap' and any(cell in self.visible for cell in effect['cells'])
               for effect in game.effects):
            events.append('将触发陷阱')
        if any(cell in self.visible for effect in game.effects if effect['kind'] == 'thaw'
               for cell in effect['cells']):
            events.append('将融化冰封浅水，恢复导电')
        if any(position(fire) in self.visible for fire in game.ground_fire):
            events.append('下一拍仍有地火')
        if any(w['owner'] == 'hero' for w in game.returning):
            events.append('下一拍沿去程返回')
        events.extend(label for enemy_id, label in game._shot_events if enemy_id in targets)
        landing = game._wave_landing
        if landing:
            if landing in self.visible:
                events.append(f'飞雷神落点 ({landing[0]},{landing[1]})')
            else:
                events.append('飞雷神将进入视野外')
                landing = None
        elif action != 'reflect' and 'blink' in self.upgrades:
            events.append('飞雷神无落脚点')
        cells = [cell for effect in game.effects if effect['kind'] == 'wave'
                 for cell in effect['cells'] if cell in self.visible]
        # Report known sources only. A shot preview must not reveal an unseen attacker.
        received = [dict(damage=hit['amount'], name=targets[hit['source']]['name']
                         if hit['source'] in targets else hit['cause'])
                    for hit in game._received_hits if hit['amount']
                    and hit['cell'] in self.visible
                    and (hit['source'] in targets or hit['source'] is None)]
        reflected = game._reflected_hit
        reflected_damage = reflected[1] if reflected and reflected[0] in targets else 0
        return dict(hits=hits, events=events, landing=landing, cells=cells,
                    received=received, reflected=reflected_damage)

    def supply_box(self):
        return next((f for f in self.features if f['kind'] == 'supply_choice'
                     and not f['used'] and position(f) == position(self.player)), None)

    def supply_options(self):
        items = ('smoke', 'lure') if self.depth < 6 else ('echo_smoke', 'grass_seed')
        return [dict(id=item, name=ITEMS[item][0], description=ITEMS[item][1], supply=True)
                for item in items]

    def make_choices(self,source):
        pool = [key for key in self.upgrade_catalog if key not in self.upgrades
                and (key != 'blink' or 'pierce' in self.upgrades)]
        # Give the first boss a dependable reward, while keeping build choices.
        picks = ['heavy'] if self.depth == 5 and 'heavy' in pool else []
        remaining = [key for key in pool if key not in picks]
        rng = Random(self.seed + self.depth * 739 + source * 113)
        picks += rng.sample(remaining, min(3 - len(picks), len(remaining)))
        self.choices = [dict(id=key, name=self.upgrade_catalog[key][0],
                             description=self.upgrade_catalog[key][1]) for key in picks]

    def finish_action(self):
        for tile in self.terrain:
            if tile.get('ice_until', self.turn + 1) <= self.turn:
                del tile['ice_until']
        for enemy in self.enemies:
            if enemy.get('fear', 0) > 1:
                enemy['fear'] -= 1
            else:
                enemy.pop('fear', None)
        self.smoke = max(0, self.smoke - 1)
        self.smoke_clouds = {key: turns-1 for key, turns in getattr(self, 'smoke_clouds', {}).items() if turns > 1}
        if self.player['hp'] == 0 and self.defeat_cause != '坠入深渊' and 'ankh' in self.inventory:
            self.inventory.remove('ankh')
            self.player['hp'] = 2
            self.poisoned = self.player_frosted = self.player_snared = False
            self.defeat_cause = None
            self.effects.append(dict(kind='revive', cells=[[self.player['x'], self.player['y']]]))
            self.note('护命符碎裂，你恢复到 2 生命。')
        previous_room=self.room
        self.room=self.room_at((self.player['x'],self.player['y']))
        if self.player['hp']==0:
            self.result='defeat';self.note('冒险结束。你可以重试同一地牢。')
        else:
            for room in self.rooms_data:
                if not room['cleared'] and not any(e['home']==room['id'] for e in self.enemies):
                    room['cleared']=True
                    self.note('已清理「'+room['name']+'」，再次经过不会刷新敌人。')
                    if room['kind']=='boss':
                        self.note('守关者已倒下。可继续探索，或前往阶梯完成试炼。')
                        self.award_boss_growth()
                        self.make_choices(room['id'])
                    elif self.depth % 5 == 4 and room['id'] == 1:
                        self.note('阶梯守卫已倒下，下层阶梯解锁。')
            for feature in self.features:
                if not feature['used'] and (self.player['x'],self.player['y'])==(feature['x'],feature['y']):
                    kind = feature['kind']
                    if self.ground_items(feature):
                        if position(self.player) != getattr(self, '_positions_before', {}).get('hero'):
                            self.collect_ground_items(feature)
                        continue
                    elif kind == 'stolen_energy':
                        if self.player['energy'] >= self.cap:
                            continue
                        self.player['energy'] += 1
                        self.note('拾回被偷走的 1 能量。')
                    elif kind == 'rune_shard':
                        self.rune_shards += 1
                        self.note('拾取一枚刻印碎片。')
                    elif kind == 'dew':
                        if self.player['hp'] < self.max_hp:
                            self.player['hp'] += 1
                            self.effects.append(dict(kind='healed', cells=[[feature['x'], feature['y']]], amount=1))
                            self.note('拾取露珠，恢复 1 生命。')
                        elif self.dew < DEW_CAPACITY:
                            self.dew += 1
                            self.note('收集露珠，留待受伤时饮用。')
                        else:
                            continue
                    elif kind == 'wonder':
                        self.player['hp'] = min(self.max_hp, self.player['hp'] + 3)
                        self.player['energy'] = self.cap
                        self.note('镜间奇遇：恢复 3 生命，能量充满。')
                    elif kind == 'key':
                        self.keys += 1
                        self.note('取得库房钥匙。')
                    elif kind == 'dry_spring':
                        continue
                    elif kind == 'shrine':
                        if self.depth not in SPRING_FLOORS and self.depth % 5:
                            continue  # Springs from pre-balance saves follow the same schedule.
                        if self.player['hp'] >= self.max_hp:
                            continue
                        self.player['hp'] += 1
                        self.effects.append(dict(kind='healed', cells=[[feature['x'], feature['y']]], amount=1))
                        self.note('泉水恢复 1 生命。')
                    elif kind == 'supply_choice':
                        continue
                    elif kind in ('chest', 'materials'):
                        if self.depth in RELIC_FLOORS:
                            if self.choices:
                                continue
                            self.forge_cores += 1
                            self.make_choices(3)
                            self.note('找到锻造核心和一份遗物选择。')
                        else:
                            self.note('检查了补给箱。')
                    feature['used'] = True
            if self.room!=previous_room:
                self.note('来到'+(self.rooms_data[self.room]['name'] if self.room>=0 else '连接走廊')+'。能量与反击保持不变。')
        self.cleared=self.room>=0 and self.rooms_data[self.room]['cleared']
        self.update_visibility()

    def act(self,action,direction,version,choice=None):
        if version != self.version:
            raise ValueError('局面已更新，请重新选择。')
        if action == 'choose_talents':
            self.resolve_talent_choice(choice)
            self.version += 1
            return
        if self.talent_choice:
            raise ValueError('请先完成本层天赋选择。')
        if action == 'open_supply':
            if self.result or self.choices or not self.supply_box():
                raise ValueError('请站在未开启的战术补给箱上。')
            options = self.supply_options()
            if not any(self.can_pack(option['id']) for option in options):
                raise ValueError('背包已满，请先腾出一个槽位。')
            self.choices = options
            self.version += 1
            return
        if self.choices and self.choices[0].get('supply') and action == 'choose':
            box = self.supply_box()
            if self.result or box is None or choice not in [entry['id'] for entry in self.choices]:
                raise ValueError('请选择箱中的一件补给。')
            if not self.can_pack(choice):
                raise ValueError('背包已满，请先腾出一个槽位。')
            self.inventory.append(choice)
            box['used'] = True
            self.choices = []
            self.version += 1
            self.note('取得战术补给：' + ITEMS[choice][0] + '。')
            return
        if action == 'skip_reward':
            if self.result or not self.choices:
                raise ValueError('当前没有可跳过的奖励。')
            supply = self.choices[0].get('supply')
            self.choices = []
            self.version += 1
            self.note('合上补给箱，可稍后回来挑选。' if supply else '已跳过本次奖励。')
            return
        if action in GROWTH_ACTIONS:
            if self.result or self.choices:
                raise ValueError('请先完成当前选择。')
            self.apply_growth(action, choice)
            self.version += 1
            return
        if not self.result and not self.choices:
            self.validate_mechanic_action(action, direction, choice)
            if action == 'move' and self.movement_locked():
                raise ValueError('当前无法移动，先攒、出波或防一拍。')
        if action=='exit':
            if version!=self.version:raise ValueError('局面已更新，请重新选择。')
            if self.result or self.choices:raise ValueError('请先完成当前选择。')
            if [self.player['x'],self.player['y']]!=self.exit or not self.exit_unlocked():
                raise ValueError('请走到目标格，并清除本层封锁阶梯的敌人。')
            self.version += 1
            if self.depth < LAST_FLOOR:
                self.depth += 1
                self.enter_room()
            else:
                self.result = 'victory'
                self.note('你已抵达终点祭坛，完成地牢试炼！')
            return
        if action == 'unlock':
            if version != self.version or self.result or self.choices:
                raise ValueError('当前不能开门。')
            if not self.locked or not self.lock:
                raise ValueError('这里没有需要开启的锁门。')
            distance = abs(self.player['x'] - self.lock[0]) + abs(self.player['y'] - self.lock[1])
            if distance != 1 or not self.locked or not self.keys:
                raise ValueError('需要站在锁门旁，并持有钥匙。')
            super().act('unlock', None, version)
            return
        if action == 'plant' or (action == 'item' and choice in THROWN_ITEMS
                                 and (choice != 'smoke' or direction is not None)):
            if (not isinstance(direction, list) or len(direction) != 2
                    or any(type(value) is not int for value in direction)):
                raise ValueError('请先选择诱饵落点。')
            self._item_target = direction
            self._thrown_item = choice if action == 'item' else None
            try:
                super().act(action, None, version, choice)
            finally:
                del self._item_target, self._thrown_item
                self.__dict__.pop('_thrown_smoke_area', None)
            return
        super().act(action, direction, version, choice)

    def path_to(self, target):
        charted = getattr(self, 'mapped', [])
        if (not isinstance(target, list) or len(target) != 2
                or any(type(value) is not int for value in target) or (target not in self.explored and target not in charted)):
            raise ValueError('请选择已探索的地面。')
        if self.result or self.choices or self.talent_choice:
            raise ValueError('请先完成当前选择。')
        if self.movement_locked():
            raise ValueError('当前无法移动，先攒、出波或防一拍。')
        def remembered_hazard(cell, kind):
            tile = self.terrain_memory.get(','.join(map(str, cell)))
            return tile and tile['kind'] == kind and (kind != 'trap' or tile['armed'])

        if remembered_hazard(target, 'fragile'):
            raise ValueError('自动寻路会绕开裂地，请手动选择是否踏入。')
        if remembered_hazard(target, 'trap'):
            raise ValueError('自动行走会绕过尚未触发的陷阱。')
        locked_target = self.locked and target == self.lock
        clue_target = target in getattr(self, 'secret_clues', [])
        statue_cells = {tuple(position(enemy)) for enemy in self.known_statues()}
        statue_target = tuple(target) in statue_cells
        if not (locked_target or clue_target) and not self.walkable(target):
            raise ValueError('这里无法通行。')

        start = (self.player['x'], self.player['y'])
        destination = tuple(target)
        known = set(map(tuple, self.explored + charted))
        visible = set(map(tuple, self.visible))
        occupied = statue_cells | {tuple(position(enemy)) for enemy in self.enemies
                                   if tuple(position(enemy)) in visible}
        danger = {tuple(cell) for enemy in self.enemies for cell in enemy['intent']['cells']
                  if tuple(cell) in visible}
        danger.update(tuple(cell) for enemy in self.enemies for cell in enemy['intent'].get('water', [])
                      if tuple(cell) in visible)
        danger.update(tuple(cell) for wave in self.returning if wave['owner'] == 'enemy'
                      for cell in wave['cells'] if tuple(cell) in visible)
        danger.update(tuple(cell) for burst in getattr(self, 'bonebursts', []) for cell in burst
                      if tuple(cell) in visible)
        fire = {tuple(position(tile)) for tile in getattr(self, 'ground_fire', []) if tuple(position(tile)) in visible}
        if destination in fire:
            raise ValueError('目标格正在燃烧，请等待地火熄灭。')
        danger.update(fire)
        contested = {tuple(enemy['intent']['target']) for enemy in self.enemies
                     if (enemy['x'], enemy['y']) in visible and enemy['intent']['action'] == 'move'}
        cautious = bool(any(tuple(position(e)) in visible and not e.get('dormant') for e in self.enemies)
                        or fire or self.has_threat() or self.returning)
        unsafe_first_steps = danger | contested

        queue = deque([(start, [])])
        visited = {start}
        while queue:
            cell, path = queue.popleft()
            adjacent = (abs(cell[0] - destination[0]), abs(cell[1] - destination[1]))
            at_landmark = (locked_target or statue_target) and sum(adjacent) == 1
            at_clue = clue_target and max(adjacent) <= 1 and self.has_sight(cell, destination)
            if cell == destination or at_landmark or at_clue:
                return path[:1] if cautious else path
            for direction, (dx, dy) in DIRS.items():
                next_cell = cell[0] + dx, cell[1] + dy
                if next_cell in visited or next_cell not in known or next_cell in occupied:
                    continue
                if (not self.walkable(next_cell) or remembered_hazard(next_cell, 'fragile')
                        or remembered_hazard(next_cell, 'trap')):
                    continue
                if cell == start and cautious and next_cell in unsafe_first_steps:
                    continue
                visited.add(next_cell)
                queue.append((next_cell, path + [direction]))
        if cautious:
            raise ValueError('没有安全的下一步，请选择相邻格手动行动。')
        raise ValueError('暂时没有已探索的可达路线。')

    def exit_unlocked(self):
        if self.depth % 5 == 4 and not self.rooms_data[1]['cleared']:
            return False
        return all(room['cleared'] for room in self.rooms_data if room['kind'] == 'boss')

    def has_threat(self):
        return bool(getattr(self, 'poisoned', False) or getattr(self, 'bonebursts', [])) or any(e.get('last_seen') or e.get('sound') or (e['intent']['cells'] and e['intent']['action'] != 'wait')
                   for e in self.enemies)

    def known_statues(self):
        seen = getattr(self, 'seen_statues', [])
        return [e for e in self.enemies if e.get('dormant') and e['id'] in seen]

    def state(self):
        explored=set(map(tuple,self.explored));visible=set(map(tuple,self.visible))
        fire_cells = [position(tile) for tile in getattr(self, 'ground_fire', []) if tuple(position(tile)) in visible]
        mapped=set(map(tuple,getattr(self, 'mapped', []))) - explored
        known=explored | mapped
        known_features = set(self.discovered_features)
        enemies=deepcopy([e for e in self.enemies if (e['x'],e['y']) in visible])
        for e in enemies:
            if e['kind'] in PROFILES:
                e['description'] = PROFILES[e['kind']][1]
            if e['kind'] in ENEMY_DESIGNS:
                base = ENEMY_DESIGNS[e['kind']][3]
                bonus = max(enemy_attack_bonus(e['kind'], self.depth, move) for move in ('melee', 'special_wave'))
                e['attack'] = base + bonus
                if e['kind'] == 'leapripper' and bonus:
                    e['description'] += ' 深层横扫造成 2 伤。'
                if e['kind'] == 'rushcrab':
                    e['description'] += ' 挥钳造成 2 伤。'
                if bonus and e['kind'] == 'siegeeye':
                    e['description'] = e['description'].replace('2 伤长波', f'{e["attack"]} 伤长波')
            elif e['kind'] in ('ram', 'charger', 'escort'):
                e['attack'] = 2
            elif e['kind'] == 'boss':
                e['attack'] = 3 + enemy_attack_bonus('boss', self.depth, 'area')
            elif e['kind'] == 'breaker':
                e['attack'] = 2 + enemy_attack_bonus('breaker', self.depth, 'siege')
                e['description'] = re.sub(r'2 伤|2伤', f'{e["attack"]} 伤', e['description'])
            if not e.get('disguised'):
                if e.get('stolen'):
                    e['lootHint'] = '归还偷走的能量'
                elif e['kind'] in FIXED_ENEMY_LOOT:
                    e['lootHint'] = ('固定掉落：疗愈药剂' if FIXED_ENEMY_LOOT[e['kind']] == 'kit'
                                     else '固定掉落：刻印碎片')
                elif e.get('regular_loot') and e['kind'] in ENEMY_LOOT:
                    _, kind = ENEMY_LOOT[e['kind']]
                    item = GROUND_SUPPLIES.get(kind, (None,))[0]
                    name = ITEMS[item][0] if item else '露珠'
                    chance = self.enemy_loot_chance(e)
                    suffix = f'掉落概率 {chance}%' if chance else '已达掉落上限'
                    e['lootHint'] = f'{name} · {suffix}'
            e.pop('regular_loot', None)
            e.pop('patrol', None)
            e['defense'] = int(e['kind'] == 'escort' or e['intent']['action'] == 'guard')
            e.pop('last_seen', None)
            e.pop('search', None)
            e.pop('distracted', None)
            e.pop('sound', None)
            e.pop('eye_aim', None)
            e.pop('sweep_aim', None)
            e.pop('chant_target', None)
            e.pop('escape', None)
            if e.get('disguised'):
                e.update(name='可疑的宝箱', description='箱盖似乎在呼吸。可从远处用波试探。')
            e['intent']['cells']=[c for c in e['intent']['cells'] if tuple(c) in visible]
            if 'water' in e['intent']:
                e['intent']['water'] = [c for c in e['intent']['water'] if tuple(c) in visible]
            if 'warning' in e['intent']:
                e['intent']['warning'] = [c for c in e['intent']['warning'] if tuple(c) in visible]
            if 'target' in e['intent'] and tuple(e['intent']['target']) not in visible:
                del e['intent']['target']
        room_summaries=[]
        for r in self.rooms_data:
            x1,y1,x2,y2=r['bounds']
            discovered=any(x1<x<x2 and y1<y<y2 for x,y in known)
            anchor = r.get('anchor')
            room_summaries.append(dict(id=r['id'],name=r['name'] if discovered else '未探索',discovered=discovered,
                                       cleared=r['cleared'] if discovered else False,
                                       anchor=anchor if anchor and tuple(anchor) in known else None,
                                       blocksExit=discovered and self.depth % 5 == 4 and r['id'] == 1
                                                  and not r['cleared']))
        upgrades=[dict(id=k,name=self.upgrade_catalog[k][0],description=FLOOR_UPGRADES.get(k, self.upgrade_catalog[k][1])) for k in self.upgrades]
        choices=deepcopy(self.choices)
        bag_slots = self.packed_inventory()
        packable = (set(ITEMS) if len(bag_slots) < self.bag_capacity else
                    {slot['id'] for slot in bag_slots if slot['count'] < slot['limit']})
        for choice in choices:
            choice['description'] = FLOOR_UPGRADES.get(choice['id'], choice['description'])
            if choice.get('supply'):
                choice['blocked'] = choice['id'] not in packable
        lure_targets = self.lure_targets() if any(item in THROWN_ITEMS for item in self.inventory) else []
        smoke_previews = {','.join(map(str, target)): [cell for cell in self.smoke_area(target)
                          if tuple(cell) in visible] for target in lure_targets
                          } if any(item in SMOKE_ITEMS for item in self.inventory) else {}
        frost_previews = {key: self.frost_smoke_preview(set(map(tuple, area)), enemies)
                          for key, area in smoke_previews.items()} if 'frost_smoke' in self.inventory else {}
        owned_items = Counter(self.inventory)
        crafting_block = self.crafting_block()
        return dict(**self.mechanic_state(explored, visible), **self.growth_state(), floorVersion=self.floor_version, depth=self.depth, lastFloor=LAST_FLOOR,
            dew=self.dew, dewCapacity=DEW_CAPACITY,
            history=deepcopy(self.history),
            runStats=self.run_stats.copy(), defeatCause=self.defeat_cause if self.result == 'defeat' else None,
            region=REGIONS[chapter(self.depth)] if self.depth < LAST_FLOOR else '终点',
            floorKind='relic' if self.depth == LAST_FLOOR else
                      'boss' if any(r['kind'] == 'boss' for r in self.rooms_data) else 'regular',
            floorTheme=getattr(self, 'floor_theme', None),
            recipes=[self.recipe_details(output, owned_items, crafting_block) for output in RECIPES],
            bagSlots=bag_slots,
            packableItems=sorted(packable),
            inventory=[dict(id=k, name=ITEMS[k][0], description=ITEMS[k][1], passive=k in ('ankh', 'sun_seed'), plantable=k in PLANTS) for k in self.inventory],
            builds=self.builds(), pursuing=self.has_threat(),
            keys=self.keys, lock=self.lock if self.locked and tuple(self.lock) in known else None,
            lockStyle=getattr(self, 'lock_style', 'store')
                      if self.locked and tuple(self.lock) in explored else None,
            echoProgress=self.echo_charges % (2 if 'bag' in self.upgrades else 3), heartLeft=int(self.heart_region != chapter(self.depth)),width=self.width,height=self.height,seed=self.seed,version=self.version,
            room=self.room,roomName=self.rooms_data[self.room]['name'] if self.room>=0 else '连接走廊',
            rooms=[r['name'] for r in room_summaries],roomStates=room_summaries,turn=self.turn,
            maxHp=self.max_hp, heroRank=self.hero_rank, player=deepcopy(self.player),poisoned=getattr(self, 'poisoned', False),
            movementLocked=self.movement_locked(),snared=getattr(self, 'player_snared', False),smokeRemaining=self.smoke,energyCap=self.cap,counter=self.counter,
            searchHints=self.nearby_secrets(),
            secretClues=deepcopy(getattr(self, 'secret_clues', [])),
            statueLandmarks=[dict(x=e['x'], y=e['y'], inscription=e['inscription'], emitter=e['emitter'])
                            for e in self.known_statues()],
            trapClues=any(tile.get('hidden') and self.room_at((tile['x'], tile['y'])) == self.room
                          for tile in self.terrain) if self.room >= 0 else False,
            thrownItems=THROWN_ITEMS, smokeItems=SMOKE_ITEMS,
            lureTargets=lure_targets,
            plantTargets=self.plant_targets() if any(seed in PLANTS for seed in self.inventory) else [],
            smokePreviews=smoke_previews, frostPreviews=frost_previews,
            smokeCells=[dict(x=x, y=y, turns=self.smoke_at((x,y))) for x,y in sorted(visible)
                        if self.smoke_at((x,y))],
            lurePreviews={','.join(map(str, target)): self.lure_preview(target, visible) for target in lure_targets}
                         if any(item in SOUND_ITEMS for item in self.inventory) else {},
            walls=[p for p in self.walls if tuple(p) in known],explored=deepcopy(self.explored),
            mapped=[list(cell) for cell in sorted(mapped)],visible=deepcopy(self.visible),
            doors=[p for p in self.doors if tuple(p) in known],
            verticalDoors=[p for p in self.doors + ([self.lock] if self.lock else [])
                           if tuple(p) in known and self.doorway_vertical(p)],
            openDoors=[p for p in self.doors if tuple(p) in visible and not self.door_closed(p)],
            fireCells=fire_cells,
            dangerCells=fire_cells + [cell for cells in ([e['intent']['cells'] + e['intent'].get('water', []) for e in self.enemies]
                                            + getattr(self, 'bonebursts', []))
                         for cell in cells if tuple(cell) in visible],
            exit=self.exit if tuple(self.exit) in known else None, exitUnlocked=self.exit_unlocked(),
            exitLockReason=('清理封锁阶梯的守卫' if self.depth % 5 == 4 else '击败守关者')
                           if not self.exit_unlocked() else None,
            groundItems=[dict(id=f['id'], items=[dict(id=item, name=ITEMS[item][0])
                                                for item in self.ground_items(f)])
                         for f in self.ground_supplies_here()],
            fullBagLandmarks=[f['id'] for f in self.features if f['id'] in known_features and not f['used']
                              and self.ground_items(f) and packable.isdisjoint(self.ground_items(f))],
            supplyOptions=self.supply_options() if any(f['kind'] == 'supply_choice' and not f['used']
                                                       and f['id'] in known_features for f in self.features) else [],
            features=[dict(deepcopy(f), **({'itemCount': item_count} if (item_count := len(self.ground_items(f))) > 1 else {}),
                           **({'itemName': ITEMS[f['item']][0]} if f['kind']=='dropped_item'
                              else {'itemName': ITEMS[f['remaining_items'][0]][0]}
                              if f.get('remaining_items') else {}))
                      for f in self.features if f['id'] in known_features
                      and not (f['used'] and (f['kind']=='dropped_item' or f['id'].startswith('drop-')))],
            upgradeCount=len(self.upgrade_catalog), enemies=enemies,cleared=self.cleared,result=self.result,choices=choices,upgrades=upgrades,
            log=self.log[:],effects=[dict(kind=f['kind'], cells=[c for c in f['cells'] if tuple(c) in visible],
                              origin=f.get('origin') if f.get('origin') in self.visible else None,
                              spread=f.get('spread', False), amount=f.get('amount'))
                       for f in self.effects],
            shrine=False)
