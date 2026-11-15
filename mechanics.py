"""Wave shapes, interactable terrain and the expedition's special enemies."""
from copy import deepcopy
from random import Random

from dungeon import DIRS, NAMES
from enemy_design import ENEMY_DESIGNS
from encounters import SideEncounters

WEAPONS = {
    'straight': ('直线器', '射程 4，命中首个敌人后停止。'),
    'fan': ('扇形器', '射程 2，覆盖前方扇面，每个敌人只受伤一次。'),
    'return': ('回旋器', '射程 4；下一拍沿实际去程返回，可再次命中。'),
    'lance': ('穿透器', '射程 4，穿过至多两个敌人。'),
}
MODES = {
    'balanced': ('均衡', '标准伤害与防御。'),
    'power': ('短距强波', '波伤害 +1，普通波消耗 2 能量，射程减半（至少 1 格）。'),
    'armor': ('耗能厚盾', '普通防消耗 1 能量，最多挡 2 点总伤害。'),
}
PROFILES = {
    'escort': ('护卫怪', '接近同伴与玩家之间的射线；替相邻同伴承受波伤害，自身护甲抵挡 1 点。近身攻击 2 点。'),
    'twin': ('共鸣双子', '同伴受伤后，下拍切换为扇形共鸣波；同伴死亡后持续使用共鸣波。普通近身攻击 1 点。'),
    'breaker': ('破城守关者', '锁定直线震波，下一拍造成 2 伤并拆掉沿途脆墙。可以引导它打开墙后的补给。随后休整。'),
    'mirrorboss': ('镜像守关者', '将你当前的发射器、强波模式及穿透能力复制到公开的下拍意图。能量不足时攒，能量充足且你有重波时会复制重波。'),
}

PROFILES.update({kind: data[:2] for kind, data in ENEMY_DESIGNS.items()})

def position(actor):
    return [actor['x'], actor['y']]


class ExpeditionMechanics(SideEncounters):
    def setup_mechanics(self, populate=True):
        self.mechanics_version = 1
        self.weapon = getattr(self, 'weapon', 'straight')
        self.mode = getattr(self, 'mode', 'balanced')
        self.returning = []
        self.bonebursts = []
        self.ground_fire = []
        self.poisoned = self.player_frosted = self.player_snared = False
        self.enemy_serial = max((e['id'] for e in self.enemies), default=-1) + 1
        self.terrain_memory = {}
        self.falls = []
        # Legacy saves retain their original geometry on the current floor.
        if self.floor_version == 1:
            self.terrain = []
            self.rare_room = False
        self._wall_cells = set(map(tuple, self.walls))
        if populate:
            if self.rare_room:
                self.note('库房的锁门后传来镜面共鸣。')
            for enemy in self.enemies:
                if 6 <= self.depth <= 9 and enemy['kind'] == 'shield':
                    enemy['kind'] = 'escort'
                elif self.floor_version < 3 and self.depth >= 11 and enemy['home'] == 4 and enemy['kind'] in ('shield', 'ram'):
                    enemy['kind'] = 'twin'
                if enemy['kind'] == 'twin':
                    enemy['pair'] = 'twins'
                    enemy['resonance'] = False
                if enemy['kind'] in PROFILES:
                    enemy['name'] = PROFILES[enemy['kind']][0]
                self.init_side_enemy(enemy)

    def tile_at(self, cell):
        return next((t for t in getattr(self, 'terrain', []) if position(t) == list(cell)), None)

    def spring_trap(self, cell):
        tile = self.tile_at(cell)
        if not tile or tile['kind'] != 'trap' or not tile['armed']:
            return
        tile['armed'] = False
        tile.pop('hidden', None)
        self.run_stats['traps'] += 1
        self.effects.append(dict(kind='trap', cells=[cell]))
        if tile['mechanism'] == 'fall':
            tile.clear()
            tile.update(x=cell[0], y=cell[1], kind='fragile', stage=2)
            actor = next((actor for actor in [self.player, *self.enemies] if position(actor) == cell), None)
            if actor is not None:
                self.resolve_fragile_actor('hero' if actor is self.player else actor['id'], actor, None)
            else:
                self.note('坠落陷阱打开，露出一处深坑。')
            return
        if tile['mechanism'] == 'dart':
            if position(self.player) == cell:
                self._trap_hits.append((1, None, {'cause': '刺针陷阱'}))
                self.note('踩中刺针陷阱 · 1 伤。')
            else:
                self.note('刺针陷阱触发，针刺已经收回。')
            return
        if tile['mechanism'] == 'grip':
            if position(self.player) == cell:
                self.player_snared = True
                self.note('夹足陷阱扣住了你，下拍无法移动。')
            else:
                victim = next((enemy for enemy in self.enemies
                               if enemy['hp'] > 0 and position(enemy) == cell), None)
                if victim:
                    victim['rooted'] = True
                    self.note(victim['name'] + '踩中了夹足陷阱。')
                else:
                    self.note('空地上的夹足陷阱合拢了。')
            return
        for enemy in self.enemies:
            if enemy['hp'] > 0:
                enemy['sound'] = dict(target=list(cell), kind='alarm', priority=True)
                if enemy.pop('dormant', False):
                    self.note('警报惊醒了武器石像。')
                if enemy.get('disguised'):
                    self.reveal_mimic(enemy)
        self.note('警报传遍整层，敌人开始追踪你最后出现的位置。')

    def trample_plant(self, actor):
        cell = position(actor)
        tile = self.tile_at(cell)
        if not tile or tile['kind'] not in ('root_plant', 'sun_plant') or actor['hp'] <= 0:
            return
        if tile['kind'] == 'sun_plant':
            if actor is self.player:
                healed = min(2, self.max_hp - actor['hp'])
                if not healed:
                    return
                actor['hp'] += healed
                self.record_status('healed', self.player, healed, source='阳草')
                self.note(f'阳草恢复 {healed} 生命。')
            else:
                self.note(actor['name'] + '踩坏了阳草。')
            self.terrain.remove(tile)
            return
        self.terrain.remove(tile)
        self.effects.append(dict(kind='roots', cells=[cell]))
        if actor is self.player:
            self.note('你踩断了缠根。')
        else:
            actor['rooted'] = True
            self.note(actor['name'] + '踩中了缠根。')

    def solid_terrain(self, cell):
        tile = self.tile_at(cell)
        return bool(tile and tile['kind'] in ('mirror', 'rubble'))

    def unsafe_ground(self, cell):
        tile = self.tile_at(cell)
        return bool(tile and tile['kind'] == 'fragile')

    def trace(self, origin, direction, distance=4, through_rubble=False):
        """A bounded reflected ray; mirrors consume one unit of travel."""
        dx, dy = DIRS[direction]
        x, y = origin
        cells = []
        for _ in range(distance):
            x, y = x + dx, y + dy
            cell = [x, y]
            if not (0 <= x < self.width and 0 <= y < self.height):
                break
            if not self.projectile_cell(cell):
                break
            tile = self.tile_at(cell)
            cells.append(cell)
            if tile and tile['kind'] == 'rubble' and not through_rubble:
                break
            if tile and tile['kind'] == 'mirror':
                dx, dy = self.mirror_vector(dx, dy, tile['slash'])
        return cells

    @staticmethod
    def mirror_vector(dx, dy, slash):
        return (-dy, -dx) if slash == '/' else (dy, dx)

    def ray(self, pos, direction):
        return self.trace(pos, direction)

    @staticmethod
    def wave_range(weapon, mode, bonus=0):
        distance = (2 if weapon == 'fan' else 4) + bonus
        return max(1, distance // 2) if mode == 'power' else distance

    def wave_paths(self, origin, direction, weapon, mode, bonus=0):
        distance = self.wave_range(weapon, mode, bonus)
        if weapon != 'fan':
            return [self.trace(origin, direction, distance)]
        return [[cell for cell in self.fan_cells(origin, direction, distance)
                 if self.has_sight(origin, cell, ignore_grass=True) and self.projectile_cell(cell)]]

    def parallel_paths(self, origin, direction):
        if 'parallel' not in self.upgrades:
            return
        dx, dy = DIRS[direction]
        distance = self.wave_range(self.weapon, self.mode, self.range_bonus)
        offsets = (1, -1) if 'flank_array' in self.upgrades else (1,)
        for offset in offsets:
            side = [origin[0] - dy * offset, origin[1] + dx * offset]
            if self.walkable(side) and self.projectile_cell(side):
                yield side, self.trace(side, direction, distance)

    @staticmethod
    def fan_cells(origin, direction, distance):
        dx, dy = DIRS[direction]
        return [[origin[0] + dx * step - dy * offset, origin[1] + dy * step + dx * offset]
                for step in range(1, distance + 1) for offset in range(1 - step, step)]

    def projectile_cell(self, cell):
        return (0 <= cell[0] < self.width and 0 <= cell[1] < self.height
                and tuple(cell) not in self._wall_cells and not (self.locked and cell == self.lock)
                and not self.door_closed(cell))

    def validate_mechanic_action(self, action, direction, choice):
        if action == 'reflect':
            if direction not in DIRS:
                raise ValueError('请选择反射方向。')
            if self.player['energy'] < 1:
                raise ValueError('反弹防御需要 1 能量。')
        if action == 'guard' and self.mode == 'armor' and self.player['energy'] < 1:
            raise ValueError('厚盾需要 1 能量，可切回均衡模式。')
        if action == 'equip':
            if self.hero_class:
                raise ValueError('本次冒险使用职业专属发射器。')
            if choice not in WEAPONS:
                raise ValueError('请选择有效的发射器。')
        if action == 'tune' and choice not in MODES:
            raise ValueError('请选择有效的改装。')
        if (action == 'equip' and choice == self.weapon) or (action == 'tune' and choice == self.mode):
            raise ValueError('已经装备，无需消耗行动。')

    def prepare_mechanics(self, action, choice):
        self._hp_before_action = self.player['hp']
        self._poison_before_action = getattr(self, 'poisoned', False)
        self._positions_before = {'hero': position(self.player)}
        self._positions_before.update({e['id']: position(e) for e in self.enemies})
        if action == 'equip':
            self.weapon = choice
            self.note('更换发射器：' + WEAPONS[choice][0] + '。')
        elif action == 'tune':
            self.mode = choice
            self.note('改装为' + MODES[choice][0] + '。')

    def plan_boss(self, enemy, player, distance):
        if enemy['phase'] % 4 != 2 or distance > 5:
            return None
        enraged = 2 * enemy['hp'] <= enemy.get('maxHp', enemy['hp'])
        x, y = player
        offsets = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)) if enraged else ((0, 0), (-1, 0), (1, 0))
        origin = position(enemy)
        warning = [[x + dx, y + dy] for dx, dy in offsets
                   if self.projectile_cell([x + dx, y + dy])
                   and self.has_sight(origin, [x + dx, y + dy], ignore_grass=True)]
        if player not in warning:
            return None
        name = '暴走震荡' if enraged else '震荡横扫'
        return dict(action='sweep_windup', label=f'{name}蓄力 · 下一拍锁定攻击',
                    cells=[], warning=warning, sweep=name, damage=3 if enraged else 2)

    def plan_special(self, active):
        player = position(self.player)
        for enemy in active:
            kind = enemy['kind']
            if kind not in PROFILES:
                continue
            distance = abs(enemy['x'] - player[0]) + abs(enemy['y'] - player[1])
            direction = self.direction_toward(position(enemy), player)
            if kind in ENEMY_DESIGNS:
                self.plan_regional(enemy, player, distance, direction)
            elif kind == 'escort':
                allies = [e for e in self.enemies if e is not enemy and e['home'] == enemy['home']]
                for ally in allies:
                    dx, dy = DIRS[self.direction_toward(position(ally), player)]
                    target = [ally['x'] + dx, ally['y'] + dy]
                    if target != player and self.walkable(target):
                        proxy = dict(enemy, last_seen=target)
                        step = self.step_toward(proxy)
                        if step:
                            enemy['intent'] = dict(action='move', label='掩护同伴', cells=[], target=step)
                            break
                if distance == 1:
                    enemy['intent'] = dict(action='melee', label='护卫冲撞 · 1伤', cells=[player])
            elif kind == 'twin':
                if enemy.get('resonance'):
                    cells = self.wave_paths(position(enemy), direction, 'fan', 'balanced')[0]
                    if player not in cells:
                        continue
                    enemy['intent'] = dict(action='special_wave', label='共鸣扇波 · 1伤',
                                           cells=cells, damage=1, direction=direction, weapon='fan')
                elif distance == 1:
                    enemy['intent'] = dict(action='melee', label='双子冲撞 · 1伤', cells=[player])
            elif kind == 'breaker':
                if enemy['phase'] % 3 == 2:
                    enemy['intent'] = dict(action='wait', label='破城后的空档', cells=[])
                else:
                    cells = self.trace(position(enemy), direction, 5, through_rubble=True)
                    if cells:
                        enemy['intent'] = dict(action='siege', label='破城震波 · 2伤 · 拆脆墙',
                                               cells=cells, damage=2, direction=direction)
            elif kind == 'mirrorboss':
                action = 'heavy' if 'heavy' in self.upgrades else 'wave'
                if enemy['energy'] < self.action_cost(action):
                    enemy['intent'] = dict(action='charge', label='镜像攒能量', cells=[])
                    continue
                damage = min(3 if self.depth < 25 else 4, self.wave_damage_before_defense(action, player_bonus=False))
                cells = self.wave_paths(position(enemy), direction, self.weapon, self.mode, self.range_bonus)[0]
                if player not in cells:
                    continue
                enemy['intent'] = dict(action='special_wave', label=f'镜像{WEAPONS[self.weapon][0]} · {damage}伤',
                                       cells=cells, damage=damage, direction=direction, weapon=self.weapon,
                                       cost=self.action_cost(action), pierce=self.wave_pierce())

    def free_enemy_ground(self, enemy, cell):
        """Special movement stays inside the current room and on safe ground."""
        room = self.room_at(position(enemy))
        return (room >= 0 and self.room_at(cell) == room and self.enemy_safe_ground(cell)
                and tuple(cell) not in self._door_cells and not self.unsafe_ground(cell)
                and cell != position(self.player)
                and not any(position(other) == cell for other in self.enemies))

    def enemy_steps(self, enemy):
        x, y = position(enemy)
        return [[x + dx, y + dy] for dx, dy in DIRS.values()
                if self.free_enemy_ground(enemy, [x + dx, y + dy])]

    def plan_regional(self, enemy, player, distance, direction):
        kind = enemy['kind']
        origin = position(enemy)
        phase = enemy['phase']
        line = self.line_to_player(enemy) if kind in ('slipsnake', 'rushcrab') else None
        intent = enemy['intent']

        def idle(label, action='wait', **fields):
            return dict(action=action, label=label, cells=[], **fields)

        def move(label, cell):
            return idle(label, 'move', target=cell)

        def melee(label, damage=1, cells=None, **fields):
            return dict(action='melee', label=f'{label} · {damage}伤', damage=damage,
                        cells=[player] if cells is None else cells, **fields)

        def wave(label, cells, damage=1, **fields):
            return dict(action='special_wave', label=f'{label} · {damage}伤',
                        damage=damage, cells=cells, **fields)

        special = self.side_intent(enemy, player, distance, direction, idle, move, melee, wave)
        if special is not None:
            enemy['intent'] = special
            return

        if kind == 'slipsnake' and phase % 3 == 0 and line:
            targets = [cell for cell in self.enemy_steps(enemy)
                       if cell[0] != player[0] and cell[1] != player[1]]
            if targets:
                enemy['intent'] = move('滑鳞侧闪', targets[0])
                return
        if kind == 'rushcrab' and line and distance >= 2 and phase % 3 != 2:
            dx, dy = DIRS[line]
            dash = []
            for step in range(1, min(2, distance - 1) + 1):
                cell = [origin[0] + dx * step, origin[1] + dy * step]
                if not self.free_enemy_ground(enemy, cell):
                    break
                dash.append(cell)
            if dash:
                enemy['intent'] = move('直冲 · 可侧移避开', dash[-1])
                return
        if kind == 'pulsemate':
            if phase % 3 == 0:
                intent = idle('静拳架势 · 挡1波伤', 'guard')
            elif phase % 3 == 2:
                intent = idle('收拳 · 空档')
            elif distance == 1:
                intent = melee('震拳', 2)
        elif kind in ('leapripper', 'blinkgolem') and 2 <= distance <= 5 and phase % 3 == 0:
            offsets = DIRS.values() if kind == 'leapripper' else ((2, 0), (-2, 0), (0, 2), (0, -2))
            targets = [[player[0] + dx, player[1] + dy] for dx, dy in offsets]
            targets = [cell for cell in targets if self.free_enemy_ground(enemy, cell)
                       and not self.mob_bound(cell) and self.has_sight(origin, cell)]
            if targets and not self.mob_bound(origin):
                target = min(targets, key=lambda cell: sum(abs(a-b) for a, b in zip(origin, cell)))
                intent = move('锁定跃点' if kind == 'leapripper' else '锁定折跃落点', target)
                intent['mob_jump'] = True
        elif kind == 'barbscorp' and distance == 1:
            targets = [cell for cell in self.enemy_steps(enemy)
                       if sum(abs(a-b) for a, b in zip(player, cell)) > distance]
            intent = move('撤向房间内部', targets[0]) if targets else melee('尾针')
        elif kind in ('arcshaman', 'nullmage', 'barbscorp'):
            fan = kind == 'arcshaman'
            shot_range = 6 if kind == 'barbscorp' else 4
            paths = (self.wave_paths(origin, direction, 'fan', 'balanced')[0] if fan else
                     self.trace(origin, direction, shot_range))
            if player in paths:
                labels = {'arcshaman': '棱晶扇波', 'nullmage': '蚀能波', 'barbscorp': '长尾针'}
                intent = (wave(labels[kind], paths, direction=direction, weapon='fan' if fan else 'straight',
                               drains=kind == 'nullmage') if enemy['energy'] else idle('攒力', 'charge'))
            elif distance == 1:
                intent = melee('近身击打')
        elif kind == 'siegeeye':
            path = self.trace(origin, direction, 6)
            if player in path:
                intent = idle('蓄力瞄准 · 下拍射线', 'windup', warning=path, direction=direction)
        elif distance == 1:
            intent = melee('吸血咬击' if kind == 'drainbat' else '近身袭击',
                           heals=kind == 'drainbat')
        # An adjacent golem or ripper still gets a basic attack.
        if distance == 1 and kind in ('blinkgolem', 'leapripper', 'siegeeye') and intent is enemy['intent']:
            intent = melee('近身袭击')
        enemy['intent'] = intent

    def plan_committed_enemies(self):
        for enemy in self.enemies:
            if enemy.get('stunned'):
                continue
            if self.plan_committed_summon(enemy):
                continue
            aim = enemy.get('eye_aim')
            if aim:
                enemy['intent'] = dict(action='special_wave', label='灼瞳长波 · 2伤', damage=2,
                                       cells=aim['warning'], direction=aim['direction'], cost=0)
            elif enemy.get('sweep_aim'):
                aim = enemy['sweep_aim']
                enemy['intent'] = dict(action='area', label=f'{aim["sweep"]} · {aim["damage"]}伤',
                                       cells=aim['warning'], damage=aim['damage'], sweep=aim['sweep'])
            elif enemy.get('recovering'):
                enemy['intent'] = dict(action='wait', label='休整 · 空档', cells=[])
            elif enemy['kind'] == 'leapripper' and enemy.get('landed'):
                x, y = position(enemy)
                cells = [[x + dx, y + dy] for dx, dy in DIRS.values()
                         if self.projectile_cell([x + dx, y + dy])]
                enemy['intent'] = dict(action='melee', label='裂步横扫 · 1伤', damage=1, cells=cells)

    def enemy_attack_intent(self, enemy):
        intent = enemy['intent']
        penalty = enemy.get('range_penalty', 0)
        if not penalty or not (intent['action'] in ('wave', 'special_wave', 'siege') or intent.get('sweep')):
            return intent
        cells = intent['cells']
        if intent.get('sweep') or intent.get('weapon') == 'fan':
            x, y = position(enemy)
            if intent.get('weapon') == 'fan':
                dx, dy = DIRS[intent['direction']]
                reach = [(a - x) * dx + (b - y) * dy for a, b in cells]
            else:
                reach = [abs(a - x) + abs(b - y) for a, b in cells]
            current = max(reach, default=0)
            limit = max(0, current - penalty)
            cells = [cell for cell, distance in zip(cells, reach) if distance <= limit] if limit else []
        else:
            limit = max(0, len(cells) - penalty)
            cells = cells[:limit]
        shortened = dict(intent, cells=cells, range_limit=limit, label=f'{intent["label"]} · 射程 {limit}')
        if 'water' in intent:
            shortened['water'] = self.conducted_water(cells)
        return shortened

    @staticmethod
    def direction_toward(start, end):
        dx, dy = end[0] - start[0], end[1] - start[1]
        if abs(dx) >= abs(dy):
            return 'right' if dx >= 0 else 'left'
        return 'down' if dy >= 0 else 'up'

    def record_status(self, kind, actor, amount=None, source=None):
        hero = actor is self.player
        target = '你' if hero else ('可疑的宝箱' if actor.get('disguised') else actor['name'])
        self.effects.append(dict(kind=kind, cells=[position(actor)], amount=amount, target=target,
                                 targetId=None if hero or actor.get('disguised') else actor['id'], source=source))

    def resolve_combat(self, action, direction, cost):
        """Accumulate simultaneous hits, then apply deaths and linked reactions."""
        self.preview_hits = {}
        self._shot_events = []
        self._wave_landing = None
        self.falls = []
        self._touched_mirrors = set()
        self._walked_this_turn = action == 'move' and position(self.player) != self._positions_before['hero']
        healed = self.player['hp'] - self._hp_before_action
        if healed > 0:
            self.record_status('healed', self.player, healed)
        if self._poison_before_action and not self.poisoned:
            self.record_status('cured', self.player)
        outgoing = {e['id']: 0 for e in self.enemies}
        if action == 'anchor_chain':
            _, _, path = self._anchor_chain_cast
            self.effects.append(dict(kind='anchor_chain', origin=self._positions_before['hero'], cells=path))
        if action == 'stored_charge':
            gained = self.cap - self.player['energy']
            self.player['energy'] = self.cap
            self.record_status('energy_gain', self.player, gained, source='预藏')
            self.note(f'预藏补充 {gained} 点能量。')
        if hasattr(self, '_recall_landing'):
            destination = self._recall_landing
            del self._recall_landing
            self.effects.append(dict(kind='blink', cells=[position(self.player), destination]))
            self.player.update(x=destination[0], y=destination[1])
            self.note('回程卷轴将你送回本层入口。')
        hits = []
        self._trap_hits = hits
        if getattr(self, 'poisoned', False):
            self.poisoned = False
            hits.append((1, None, {'cause': '中毒'}))
            self.effects.append(dict(kind='poison', cells=[position(self.player)]))
        self.terrain = [t for t in self.terrain if t['kind'] != 'ice' or t['expires'] >= self.turn]
        bursts, self.bonebursts = getattr(self, 'bonebursts', []), []
        for burst in bursts:
            cells = [cell for cell in burst if self.projectile_cell(cell)]
            for cell in cells:
                self.flatten_grass(cell)
            if position(self.player) in cells:
                hits.append((1, None, {'cause': '碎骨爆发'}))
            self.effects.append(dict(kind='bones', cells=cells))
        reflected = 0
        reflected_source = None
        self.resolve_fragile()
        if getattr(self, '_pending_fall', None) is not None:
            del self._trap_hits
            return
        for ident, actor in [('hero', self.player), *((e['id'], e) for e in self.enemies)]:
            cell = position(actor)
            if cell != self._positions_before[ident]:
                self.flatten_grass(cell)
                tile = self.tile_at(cell)
                if actor is self.player or not (tile and tile.get('hidden')):
                    self.spring_trap(cell)
                if getattr(self, '_pending_fall', None) is not None:
                    del self._trap_hits
                    return
                self.trample_plant(actor)
        chilled_ground = []
        if action == 'item' and hasattr(self, '_item_target'):
            target = self._item_target
            area = getattr(self, '_thrown_smoke_area', None)
            if area:
                self.effects.append(dict(kind='smoke', cells=area))
                if self._thrown_item == 'frost_smoke':
                    chilled_ground = area
                    frozen_water = self.freeze_water(area)
                    if frozen_water:
                        self.note(f'凝霜封住了 {len(frozen_water)} 格浅水。')
                    chilled = [enemy for enemy in self.enemies if enemy['hp'] > 0 and not enemy.get('disguised') and position(enemy) in area]
                    for enemy in chilled:
                        enemy['frosted'] = True
                    self.effects.append(dict(kind='ice', cells=area))
                    if chilled:
                        self.note(f'凝霜限制了 {len(chilled)} 名敌人的下一次移动。')
            else:
                self.effects.append(dict(kind='sound', cells=[target]))
                self.spring_trap(target)
        self.resolve_ground_fire(outgoing, hits, chilled_ground)
        previous_returns, self.returning = self.returning, []
        for wave in previous_returns:
            if wave['owner'] == 'hero':
                self.player_wave(wave['cells'], wave['damage'], outgoing, wave['pierce'],
                                 returning=True, rune=wave.get('rune'))
            else:
                hit, cells = self.enemy_wave_path(wave['cells'], wave['source'])
                self.effects.append(dict(kind='return', cells=cells))
                if hit and action == 'reflect' and not reflected:
                    reflected = wave['damage']
                    reflected_source = wave['source']
                    self.player_wave(self.trace(position(self.player), direction), reflected, outgoing, 1)
                elif hit:
                    hits.append((wave['damage'], None, {'cause': '敌方回波', 'source': wave['source']}))
        impacts = {}
        if action in ('wave', 'heavy'):
            self.fire_wave(action, direction, cost, outgoing, impacts)
        if action == 'reflect':
            self.player['energy'] -= 1
        if action == 'guard' and self.mode == 'armor':
            self.player['energy'] -= 1
        for enemy in self.enemies:
            if enemy['hp'] <= 0:
                continue
            intent = self.enemy_attack_intent(enemy)
            if intent['action'] == 'stunned':
                enemy.pop('stunned', None)
                if position(enemy) in self.visible:
                    self.note(f'{enemy["name"]}因击晕跳过一拍。')
                continue
            if 'range_limit' in intent:
                enemy.pop('range_penalty', None)
                if position(enemy) in self.visible:
                    self.note(f'{enemy["name"]}释放攻击，中断后射程 {intent["range_limit"]} 格。')
            attack = intent['action']
            self.resolve_side_intent(enemy, intent, hits)
            if attack == 'windup':
                enemy['eye_aim'] = dict(warning=intent['warning'], direction=intent['direction'])
            elif attack == 'sweep_windup':
                enemy['sweep_aim'] = {key: intent[key] for key in ('warning', 'sweep', 'damage')}
            elif enemy.pop('eye_aim', None) or enemy.pop('sweep_aim', None):
                enemy['recovering'] = True
            elif enemy.pop('landed', False):
                enemy['recovering'] = True
            elif not enemy.pop('recovering', False) and intent.get('mob_jump') and position(enemy) != self._positions_before[enemy['id']]:
                enemy['landed' if enemy['kind'] == 'leapripper' else 'recovering'] = True
                self.effects.append(dict(kind='blink', cells=[self._positions_before[enemy['id']], position(enemy)]))
            if attack == 'charge':
                enemy['energy'] = min(3, enemy['energy'] + 1)
            if attack in ('wave', 'special_wave', 'siege'):
                if attack in ('wave', 'special_wave'):
                    enemy['energy'] = max(0, enemy['energy'] - intent.get('cost', 1))
                if attack == 'siege':
                    reachable = []
                    for cell in intent['cells']:
                        if not self.projectile_cell(cell):
                            break
                        reachable.append(cell)
                    destroyed = [t for t in self.terrain if t['kind'] == 'rubble' and position(t) in reachable]
                    for tile in destroyed:
                        self.terrain.remove(tile)
                        self.note('破城震波击碎了脆墙，露出通道与补给。')
                damage = intent.get('damage', 1)
                hit, cells = self.enemy_wave_path(intent['cells'], enemy['id'], intent.get('weapon') == 'fan',
                                                  intent.get('pierce') or intent.get('weapon') == 'lance',
                                                  origin=position(enemy))
                if hit and action == 'reflect' and not reflected and attack != 'siege':
                    reflected = damage
                    reflected_source = enemy['id']
                    previous_damage = outgoing.copy()
                    reflected_path = self.player_wave(self.trace(position(self.player), direction),
                                                      damage, outgoing, 1)
                    if intent.get('electric'):
                        water = self.conducted_water(reflected_path)
                        self.effects.append(dict(kind='electric', cells=water))
                        for target in self.enemies:
                            ident = target['id']
                            if position(target) in water and outgoing[ident] == previous_damage[ident]:
                                outgoing[ident] += damage
                                self.preview_hits[ident] = self.preview_hits.get(ident, 0) + damage
                    self.note('反弹防御将来波转向，抵挡 ' + str(damage) + ' 点伤害。')
                else:
                    water = self.conducted_water(cells) if intent.get('electric') else []
                    if water:
                        self.effects.append(dict(kind='electric', cells=water))
                    if hit or position(self.player) in water:
                        hits.append((damage, enemy, intent))
                self.effects.append(dict(kind='laser' if intent.get('weapon') != 'fan' else 'enemy',
                                         cells=cells, origin=position(enemy)))
                if (intent.get('weapon') == 'return' or intent.get('rune') == 'echo') and cells:
                    self.returning.append(dict(owner='enemy', cells=list(reversed(cells)), damage=damage,
                                               source=enemy['id'], pierce=1))
            elif attack in ('melee', 'area'):
                cells = intent['cells']
                if intent.get('sweep'):
                    origin = position(enemy)
                    cells = [cell for cell in cells if self.projectile_cell(cell)
                             and self.has_sight(origin, cell, ignore_grass=True)]
                for cell in cells:
                    self.flatten_grass(cell)
                if position(self.player) in cells:
                    hits.append((intent.get('damage', 2 if attack == 'area' else 1), enemy, intent))
                self.effects.append(dict(kind='enemy', cells=cells))
            enemy['phase'] += 1
        incoming = sum(damage for damage, _, _ in hits)
        blockable = sum(damage for damage, _, intent in hits if intent.get('rune') != 'shatter')
        blocked = min(self.guard_limit, blockable) if action == 'guard' else 0
        if blocked or reflected:
            self.counter = True
            self.on_block()
            if 'heart' in self.upgrades and self.use_heart():
                # Falling is irreversible, including when an earlier locked wave was reflected.
                if 0 < self.player['hp'] < self.max_hp:
                    self.player['hp'] += 1
                    self.record_status('healed', self.player, 1, source='护心')
                    self.note('护心回复 1 生命。')
        hp_left = self.player['hp']
        self.player['hp'] = max(0, hp_left - incoming + blocked)
        if action == 'reflect':
            self.effects.append(dict(kind='reflect_arc', cells=[position(self.player)], direction=DIRS[direction]))
        elif action == 'guard':
            self.effects.append(dict(kind='guard', cells=[position(self.player)]))
            self.note(f'防御抵挡 {blocked} 点伤害。')
        if blocked:
            self.record_status('blocked', self.player, blocked)
            if 'gate_shield' in self.upgrades and not self.gate_shield_ready:
                self.gate_shield_ready = True
                self.note('守门盾已就绪，下一发主束附带击退。')
        if reflected:
            self.record_status('reflected', self.player, reflected)
        damage_taken = min(hp_left, incoming - blocked)
        if damage_taken:
            self.record_status('damage', self.player, damage_taken)
            self.note(f'受到 {damage_taken} 点伤害。')
        self._reflected_hit = (reflected_source, reflected) if reflected else None
        self._received_hits = []
        block_left = blocked
        for damage, enemy, intent in hits:
            absorbed = 0 if intent.get('rune') == 'shatter' else min(block_left, damage)
            block_left -= absorbed
            if absorbed == damage:
                continue
            loss = damage - absorbed
            self._received_hits.append(dict(amount=loss,
                                            source=enemy['id'] if enemy else intent.get('source'),
                                            cause=intent.get('cause', ''),
                                            cell=position(self.player)))
            hp_left -= loss
            if hp_left <= 0 and not self.defeat_cause:
                self.defeat_cause = intent.get('cause') or (enemy['name'] if enemy else '战斗受伤')
            self.resolve_side_hit(enemy, intent)
            if intent.get('drains') and self.player['energy']:
                self.player['energy'] -= 1
                self.note('蚀能波抽走 1 能量。')
            if intent.get('heals') and 0 < enemy['hp'] < enemy.get('maxHp', enemy['hp']):
                enemy['hp'] += 1
                self.record_status('healed', enemy, 1, source='吸取生命')
                self.note(enemy['name'] + '吸取生命，回复 1 点。')
        shield_shot = (action in ('wave', 'heavy') and 'gate_shield' in self.upgrades
                       and self.gate_shield_ready)
        if shield_shot:
            self.gate_shield_ready = False
        self.resolve_wave_relics(impacts, outgoing, knockback=shield_shot or 'impact' in self.upgrades)
        for enemy in self.enemies:
            damage = outgoing[enemy['id']]
            if damage and enemy['hp'] > 0:
                self.record_status('damage', enemy, min(damage, enemy['hp']))
            enemy['hp'] -= damage
        for enemy in self.enemies:
            if enemy['kind'] == 'twin':
                partners = [e for e in self.enemies if e is not enemy and e.get('pair') == enemy.get('pair')]
                enemy['resonance'] = not partners or any(outgoing[e['id']] > 0 or e['hp'] <= 0 for e in partners)
        dead = [e for e in self.enemies if e['hp'] <= 0]
        self.run_stats['defeated'] += len(dead)
        for enemy in dead:
            self.note('击败' + enemy['name'] + '。')
        pulled = self._anchor_chain_cast[0] if action == 'anchor_chain' else None
        self.reward_sanity_kills(dead, outgoing, impacts, pulled)
        fell = {fall['id'] for fall in self.falls}
        for enemy in dead:
            if enemy['kind'] == 'boneburst' and enemy['id'] not in fell:
                x, y = position(enemy)
                cells = [[x, y]] + [[x + dx, y + dy] for dx, dy in DIRS.values()]
                self.bonebursts.append([cell for cell in cells if self.projectile_cell(cell)])
                self.note('爆骨卫的碎骨将在下一拍爆发。')
        self.enemies = [e for e in self.enemies if e['hp'] > 0]
        self.split_wounded_enemies(outgoing)
        self.finish_side_enemies(outgoing, dead)
        if 'refund' in self.upgrades:
            kills = sum(e['kind'] not in ('bonepuppet', 'broodling') for e in dead)
            self.player['energy'] = min(self.cap, self.player['energy'] + kills)
        for tile in self.terrain:
            if (tile['x'], tile['y']) in self._touched_mirrors:
                tile['slash'] = '\\' if tile['slash'] == '/' else '/'
        self._touched_mirrors.clear()
        del self._trap_hits

    def add_enemy(self, kind, target, home, hp, **fields):
        serial = max(getattr(self, 'enemy_serial', 0), max((e['id'] for e in self.enemies), default=-1) + 1)
        enemy = dict(id=serial, kind=kind, name=PROFILES[kind][0] if kind in PROFILES else NAMES[kind], home=home,
                     x=target[0], y=target[1], hp=hp, maxHp=hp, energy=0, phase=0,
                     intent=dict(action='wait', label='刚出现', cells=[]), **fields)
        self.enemies.append(enemy)
        self.enemy_serial = serial + 1
        self.flatten_grass(target)
        return enemy

    def split_wounded_enemies(self, outgoing):
        for enemy in self.enemies[:]:
            if (enemy['kind'] != 'splitcloud' or enemy.get('split')
                    or enemy['hp'] < 2 or not outgoing[enemy['id']]):
                continue
            cells = self.enemy_steps(enemy)
            if not cells:
                continue
            x, y = cells[0]
            enemy['split'] = True
            enemy['hp'] -= 1
            child = self.add_enemy('splitcloud', [x, y], enemy['home'], 1, split=True)
            child['name'] = '分裂子群'
            self.effects.append(dict(kind='split', cells=[position(enemy), [x, y]]))
            self.note('分裂群分出一个子群。')

    def fire_wave(self, action, direction, cost, outgoing, impacts):
        origin = position(self.player)
        restrained = self.mob_bound(origin) or getattr(self, '_movement_locked', False)
        damage = self.wave_damage_before_defense(action)
        self.player['energy'] -= cost
        self.counter = False
        cells = self.wave_paths(origin, direction, self.weapon, self.mode, self.range_bonus)[0]
        pierce = self.wave_pierce()
        previous_damage = outgoing.copy()
        actual = self.player_wave(cells, damage, outgoing, pierce, rune=self.rune,
                                  impacts=impacts, origin=origin, direction=direction,
                                  ignite='burn' in self.upgrades)
        if 'burn' in self.upgrades:
            melted = []
            for cell in actual:
                tile = self.tile_at(cell)
                if tile and tile.pop('ice_until', None) is not None:
                    melted.append(cell)
            if melted:
                self.effects.append(dict(kind='thaw', cells=melted))
                self.note(f'灼烧主束融化了 {len(melted)} 格冰封浅水。')
        if 'double' in self.upgrades:
            self.player_wave(cells, max(1, damage // 2), outgoing, pierce, rune=self.rune,
                             bypass_defeated=True, origin=origin)
        for side, side_cells in self.parallel_paths(origin, direction):
            self.player_wave(side_cells, max(1, damage - 1), outgoing,
                             1 if self.weapon == 'fan' else pierce, rune=self.rune,
                             bypass_defeated=True, origin=side)
        if 'mirror_chain' in self.upgrades and self.weapon != 'fan':
            self.split_mirror_wave(actual, damage, outgoing)
        if 'drain' in self.talents and sum(outgoing[k] > v for k, v in previous_damage.items()) >= 2:
            self.player['energy'] = min(self.cap, self.player['energy'] + 1)
            self.note('波击回收 · 返还 1 能量。')
        if (self.weapon == 'return' or self.rune == 'echo') and actual:
            self.returning.append(dict(owner='hero', cells=list(reversed(actual)),
                                       damage=self.return_damage(damage),
                                       pierce=pierce, rune=self.rune))
        self.note(f'第 {self.turn} 拍 · {WEAPONS[self.weapon][0]}发射。')
        if 'blink' in self.upgrades and 'pierce' in self.upgrades and self.player['hp'] > 0:
            if restrained:
                self.note('脚下受困，本拍无法使用飞雷神。')
            else:
                self.blink_along_wave(origin, direction, actual)

    def split_mirror_wave(self, actual, damage, outgoing):
        mirrors = {tuple(cell) for cell in actual
                   if (tile := self.tile_at(cell)) and tile['kind'] == 'mirror'}
        if len(mirrors) < 2:
            return
        end, previous = actual[-1], actual[-2]
        dx, dy = end[0] - previous[0], end[1] - previous[1]
        tile = self.tile_at(end)
        if tile and tile['kind'] == 'rubble':
            return
        if tuple(end) in mirrors:
            dx, dy = self.mirror_vector(dx, dy, tile['slash'])
        for side, vector in DIRS.items():
            if dx * vector[0] + dy * vector[1] == 0:
                cells = self.trace(end, side, distance=2)
                if cells:
                    self.player_wave(cells, max(1, damage // 2), outgoing, 1, origin=end,
                                     bypass_defeated=True, effect_kind='mirror_split')

    def blink_along_wave(self, origin, direction, cells):
        dx, dy = DIRS[direction]
        occupied = {tuple(position(enemy)) for enemy in self.enemies if enemy['hp'] > 0}
        for cell in reversed(cells):
            if self.weapon == 'fan' and (cell[0] - origin[0]) * dy != (cell[1] - origin[1]) * dx:
                continue
            if cell == origin or tuple(cell) in occupied or not self.walkable(cell) or self.mob_bound(cell):
                continue
            tile = self.tile_at(cell)
            if tile and tile['kind'] == 'fragile' and tile['stage'] >= 1:
                continue
            self.player['x'], self.player['y'] = cell
            self._wave_landing = cell
            self.resolve_fragile_actor('hero', self.player, origin)
            self.flatten_grass(cell)
            self.spring_trap(cell)
            self.trample_plant(self.player)
            self.effects.append(dict(kind='blink', cells=[origin, cell]))
            self.note('飞雷神 · 沿主束位移。')
            return

    def resolve_wave_relics(self, impacts, outgoing, knockback):
        for enemy in self.enemies:
            ident = enemy['id']
            self.extinguish_in_water(enemy)
            if enemy.get('burning', 0) > 0 and enemy['hp'] > outgoing[ident]:
                enemy['burning'] -= 1
                outgoing[ident] += 1
                self.preview_hits[ident] = self.preview_hits.get(ident, 0) + 1
                self.effects.append(dict(kind='burn', cells=[position(enemy)]))
                self._shot_events.append((ident, f"{enemy['name']}受到灼烧 1 伤"))
            if ident not in impacts or enemy['hp'] <= outgoing[ident]:
                continue
            if 'burn' in self.upgrades:
                enemy['burning'] = 2
                if not self.extinguish_in_water(enemy):
                    self._shot_events.append((ident, f"{enemy['name']}灼烧两拍"))
            if 'freeze' in self.upgrades and not enemy.get('frozen'):
                enemy['frost_stacks'] = enemy.get('frost_stacks', 0) + 1
                if enemy['frost_stacks'] >= 2:
                    enemy['frost_stacks'] = 0
                    enemy['frozen'] = True
                    self._shot_events.append((ident, f"{enemy['name']}冻结下一次移动"))
                else:
                    self._shot_events.append((ident, f"{enemy['name']}叠霜 1 层"))
            if knockback:
                self.push_enemy(enemy, impacts[ident])
                self.extinguish_in_water(enemy)

    def extinguish_in_water(self, enemy):
        if not enemy.get('burning'):
            return False
        tile = self.tile_at(position(enemy))
        if not tile or tile['kind'] != 'water':
            return False
        enemy.pop('burning')
        message = enemy['name'] + '身上的火被浅水熄灭'
        self._shot_events.append((enemy['id'], message))
        self.note(message + '。')
        self.effects.append(dict(kind='steam', cells=[position(enemy)]))
        return True

    def push_enemy(self, enemy, direction):
        if enemy['kind'] == 'canalfish':
            target = [enemy['x'] + direction[0], enemy['y'] + direction[1]]
            tile = self.tile_at(target)
            if not tile or tile['kind'] != 'water':
                return
        old = position(enemy)
        cell = [old[0] + direction[0], old[1] + direction[1]]
        if not self.walkable(cell) or cell == position(self.player) or any(
                position(other) == cell and other['hp'] > 0 for other in self.enemies):
            return
        enemy['x'], enemy['y'] = cell
        self.resolve_fragile_actor(enemy['id'], enemy, old)
        self.flatten_grass(cell)
        if hasattr(self, '_trap_hits'):
            self.spring_trap(cell)
        self.trample_plant(enemy)
        self.effects.append(dict(kind='impact', cells=[cell], direction=direction, targetId=enemy['id']))
        label = '被推入深渊' if enemy['hp'] <= 0 else '被击退一格'
        self._shot_events.append((enemy['id'], enemy['name'] + label))
        self.note(enemy['name'] + label + '。')

    def refract_wave(self, source, damage, outgoing):
        origin = position(source)
        candidates = []
        for enemy in self.enemies:
            if enemy is source or enemy['hp'] <= outgoing[enemy['id']]:
                continue
            target = position(enemy)
            distance = sum((a - b) ** 2 for a, b in zip(origin, target))
            if distance <= 64 and self.walkable(target) and self.has_sight(origin, target, ignore_grass=True):
                candidates.append((distance, enemy['id'], enemy))
        if not candidates:
            return
        _, ident, enemy = min(candidates)
        cells = [list(cell) for cell, _ in self.line_steps(origin, position(enemy))]
        amount = self.wave_damage(max(1, damage // 2), enemy, 0)
        outgoing[ident] += amount
        self.preview_hits[ident] = self.preview_hits.get(ident, 0) + amount
        self.effects.append(dict(kind='refraction', origin=origin, cells=cells))
        self._shot_events.append((ident, f'折射 · {enemy["name"]} {amount} 伤'))

    def conduct_from_hit(self, source, damage, dealt, outgoing):
        origin = position(source)
        water = self.conducted_water([origin])
        connected = set(map(tuple, water))
        amount = dealt if connected else max(1, damage // 2)
        cells = []
        for enemy in self.enemies:
            if enemy is source or enemy['hp'] <= 0:
                continue
            target = position(enemy)
            in_range = (tuple(target) in connected if connected
                        else sum((a - b) ** 2 for a, b in zip(origin, target)) <= 36)
            if in_range:
                ident = enemy['id']
                outgoing[ident] += amount
                self.preview_hits[ident] = self.preview_hits.get(ident, 0) + amount
                self._shot_events.append((ident, f'导电 · {enemy["name"]} {amount} 伤'))
                cells.append(target)
        if cells:
            self.effects.append(dict(kind='conduction', cells=water or cells))

    def player_wave(self, cells, damage, outgoing, pierce, returning=False, rune=None,
                    impacts=None, origin=None, direction=None, bypass_defeated=False, ignite=False,
                    effect_kind=None):
        actual, struck, damaged = [], set(), set()
        conduction_hits = []
        for cell in cells:
            previous = actual[-1] if actual else origin
            if not self.projectile_cell(cell):
                break
            tile = self.tile_at(cell)
            actual.append(cell)
            if not ignite or not self.ignite_grass(cell):
                self.flatten_grass(cell)
            self.spring_trap(cell)
            if tile and tile['kind'] == 'web':
                self.terrain.remove(tile)
                self.effects.append(dict(kind='web', cells=[cell]))
                self.note('能量波割断了蛛网。')
            if tile and tile['kind'] == 'mirror' and tile.get('rotating'):
                self._touched_mirrors.add(tuple(cell))
            if tile and tile['kind'] == 'rubble':
                if pierce == 99:
                    continue
                break
            target = next((e for e in self.enemies if position(e) == cell
                           and e['hp'] > (outgoing[e['id']] if bypass_defeated else 0)), None)
            if not target or target['id'] in struck:
                continue
            struck.add(target['id'])
            # An adjacent escort steps into the impact; the target's armour is not applied twice.
            guard = next((e for e in self.enemies if e['kind'] == 'escort' and e is not target and e['hp'] > 0
                          and e['intent']['action'] != 'stunned'
                          and (not bypass_defeated or e['hp'] > outgoing[e['id']])
                          and e['home'] == target['home'] and abs(e['x'] - target['x']) + abs(e['y'] - target['y']) == 1), None)
            recipient = guard or target
            point_blank = (rune == 'point_blank' and impacts is not None
                           and sum(abs(a - b) for a, b in zip(origin, position(recipient))) == 1)
            impact_damage = (3 * damage + 1) // 2 if point_blank else damage
            if rune == 'shatter':
                amount = impact_damage
            else:
                amount = self.wave_damage(impact_damage, recipient, len(struck) - 1)
            if recipient['id'] not in damaged:
                outgoing[recipient['id']] += amount
                self.preview_hits[recipient['id']] = self.preview_hits.get(recipient['id'], 0) + amount
                damaged.add(recipient['id'])
                if rune == 'refraction' and impacts is not None and len(damaged) == 1:
                    self.refract_wave(recipient, damage, outgoing)
                if rune == 'conduction' and impacts is not None and amount:
                    conduction_hits.append((recipient, amount))
                if impacts is not None and amount:
                    impacts[recipient['id']] = (DIRS[direction] if self.weapon == 'fan'
                                                else (cell[0] - previous[0], cell[1] - previous[1]))
                if rune == 'frost' and amount:
                    recipient['frosted'] = True
                if point_blank and amount:
                    self._shot_events.append((recipient['id'], f'近战 · {recipient["name"]}受到贴身增伤'))
                if rune == 'shield_erosion' and impacts is not None and self.enemy_defense(recipient):
                    recipient['defense_lost'] = recipient.get('defense_lost', 0) + 1
                    self.record_status('defense_loss', recipient, 1, source='蚀盾')
                    self._shot_events.append((recipient['id'], f'蚀盾 · {recipient["name"]}防御 −1'))
                if (rune == 'range_break' and impacts is not None
                        and (recipient['intent']['action'] in ('charge', 'windup', 'sweep_windup')
                             or recipient.get('eye_aim') or recipient.get('sweep_aim'))):
                    recipient['range_penalty'] = recipient.get('range_penalty', 0) + 1
                    self.record_status('range_loss', recipient, 1, source='中断')
                    self._shot_events.append((recipient['id'], f'中断 · {recipient["name"]}下一发射程 −1'))
                if rune == 'stagger' and impacts is not None:
                    if recipient.get('stagger_hit_turn') == self.turn - 1:
                        recipient.pop('stagger_hit_turn')
                        recipient['stunned'] = True
                        self.record_status('stun', recipient, 1, source='击晕')
                        self._shot_events.append((recipient['id'], f'击晕 · {recipient["name"]}跳过下一拍'))
                    else:
                        recipient['stagger_hit_turn'] = self.turn
                        self._shot_events.append((recipient['id'], f'击晕 · {recipient["name"]}已命中 1/2'))
            if guard:
                self.note('护卫替' + target['name'] + '承受来波。')
            if len(struck) >= pierce:
                break
        for source, dealt in conduction_hits:
            self.conduct_from_hit(source, damage, dealt, outgoing)
        self.effects.append(dict(kind=effect_kind or ('return' if returning else 'wave'), cells=actual,
                                 origin=origin, spread=pierce == 99 and not returning))
        return actual

    def freeze_water(self, cells):
        frozen = []
        for cell in cells:
            tile = self.tile_at(cell)
            if tile and tile['kind'] == 'water':
                tile['ice_until'] = self.turn + 2
                frozen.append(cell)
        return frozen

    def conducted_water(self, path):
        water = {(tile['x'], tile['y']) for tile in self.terrain
                 if tile['kind'] == 'water' and 'ice_until' not in tile}
        frontier = {tuple(cell) for cell in path} & water
        reached = set(frontier)
        while frontier:
            frontier = {(x + dx, y + dy) for x, y in frontier for dx, dy in DIRS.values()
                        if (x + dx, y + dy) in water and (x + dx, y + dy) not in reached
                        and self.projectile_cell([x + dx, y + dy])}
            reached.update(frontier)
        return [list(cell) for cell in sorted(reached)]

    def enemy_wave_path(self, path, source, fan=False, pierce=False, origin=None):
        cells, blocked = [], 0
        hit = False
        for cell in path:
            if fan and not self.has_sight(origin, cell, ignore_grass=True):
                continue
            if not self.projectile_cell(cell):
                if fan:
                    continue
                break
            tile = self.tile_at(cell)
            cells.append(cell)
            self.flatten_grass(cell)
            if tile and tile['kind'] == 'rubble':
                if fan:
                    continue
                break
            if tile and tile['kind'] == 'mirror' and tile.get('rotating'):
                self._touched_mirrors.add(tuple(cell))
            if cell == position(self.player):
                hit = True
                if not fan:
                    break
            if any(e['id'] != source and position(e) == cell and e['hp'] > 0 for e in self.enemies):
                blocked += 1
                if not fan and blocked >= (2 if pierce is True else pierce or 1):
                    break
        return hit, cells

    def ignite_grass(self, cell, spread=2):
        tile = self.tile_at(cell)
        if not tile or tile['kind'] != 'high_grass' or not self.projectile_cell(cell):
            return False
        tile['kind'] = 'grass'
        self.ground_fire = getattr(self, 'ground_fire', [])
        self.ground_fire.append(dict(x=cell[0], y=cell[1], spread=spread))
        self.effects.append(dict(kind='burn', cells=[cell]))
        return True

    def resolve_ground_fire(self, outgoing, hits, chilled_ground):
        fire, self.ground_fire = getattr(self, 'ground_fire', []), []
        cells = [position(tile) for tile in fire if position(tile) not in chilled_ground]
        if not cells:
            return
        if position(self.player) in cells:
            hits.append((1, None, {'cause': '地火'}))
        for enemy in self.enemies:
            if position(enemy) in cells:
                outgoing[enemy['id']] += 1
                self.preview_hits[enemy['id']] = self.preview_hits.get(enemy['id'], 0) + 1
        for tile in sorted(fire, key=lambda tile: -tile['spread']):
            if not tile['spread'] or position(tile) in chilled_ground:
                continue
            x, y = position(tile)
            for dx, dy in DIRS.values():
                adjacent = [x + dx, y + dy]
                if adjacent not in chilled_ground:
                    self.ignite_grass(adjacent, spread=tile['spread'] - 1)
        self.effects.append(dict(kind='burn', cells=cells))

    def flatten_grass(self, cell):
        tile = self.tile_at(cell)
        if not tile or tile['kind'] != 'high_grass':
            return
        tile['kind'] = 'grass'
        self.effects.append(dict(kind='grass', cells=[cell]))
        x, y = cell
        # A coordinate-based roll is stable across previews, reloads and replays.
        roll = Random(f'{self.seed}:{self.depth}:{x}:{y}:grass').randrange(30)
        drop = 'grass_seed' if roll == 0 else 'dew' if roll < 3 else None
        if drop:
            self.features.append(dict(id=f'grass-{x}-{y}', kind=drop, x=x, y=y, used=False))

    def resolve_fragile(self):
        actors = [('hero', self.player)] + [(e['id'], e) for e in self.enemies]
        for ident, actor in actors:
            self.resolve_fragile_actor(ident, actor, self._positions_before.get(ident))
            if getattr(self, '_pending_fall', None) is not None:
                return

    def resolve_fragile_actor(self, ident, actor, previous):
        cell = position(actor)
        if cell == previous:
            return
        tile = self.tile_at(cell)
        if not tile or tile['kind'] != 'fragile':
            return
        if not tile['stage']:
            tile['stage'] = 2
            self.note('脆弱地板塌陷，留下破洞。')
            return
        # Stage 1 in older saves was already stepped on and now behaves as an open pit.
        tile['stage'] = 2
        if ident == 'hero':
            self._pending_fall = cell
            return
        actor['hp'] = 0
        self.falls.append(dict(id=ident, kind=actor['kind'], cell=cell))
        self.record_status('fall', actor)
        self.note(actor['name'] + '坠入深渊。')

    def mechanic_state(self, known, visible):
        terrain = [deepcopy(t) for t in self.terrain_memory.values() if (t['x'], t['y']) in known]
        returns = [dict(owner=w['owner'], damage=w['damage'], cells=[c for c in w['cells'] if tuple(c) in visible])
                   for w in self.returning]
        origin = position(self.player)
        aim_paths = {}
        for direction in DIRS:
            paths = self.wave_paths(origin, direction, self.weapon, self.mode, self.range_bonus)
            paths.extend(cells for _, cells in self.parallel_paths(origin, direction))
            aim_paths[direction] = [cell for path in paths for cell in path if tuple(cell) in visible]
        return dict(mechanicsVersion=1, weapon=self.weapon, mode=self.mode,
                    weapons=[dict(id=k, name=v[0], description=v[1]) for k, v in WEAPONS.items()],
                    modes=[dict(id=k, name=v[0], description=v[1]) for k, v in MODES.items()],
                    terrain=terrain, returning=returns,
                    aimPaths=aim_paths,
                    falls=[deepcopy(f) for f in self.falls if tuple(f['cell']) in visible])
