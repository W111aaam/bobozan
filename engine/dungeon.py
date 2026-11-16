"""Deterministic, action-driven dungeon simulation. No wall-clock combat."""
from copy import deepcopy
from random import Random
from secrets import randbelow

DIRS = {'up': (0, -1), 'right': (1, 0), 'down': (0, 1), 'left': (-1, 0)}
UPGRADES = {
    'echo': ('回响', '每场战斗第一次攒，额外获得 1 能量。'),
    'refund': ('余势', '波每击败一个敌人，返还 1 能量。'),
    'heart': ('护心', '每场首次成功防御时，回复 1 生命。'),
    'pierce': ('穿透', '波可穿过第一个敌人；仍会被墙阻挡。'),
    'bag': ('蓄能袋', '能量上限从 3 增加到 4。'),
    'heavy': ('重波', '解锁消耗 3 能量、造成 2 伤害的重波。'),
}
ROOMS = ['初醒石室', '回声长廊', '苔光泉庭', '双影回廊', '守关者之庭']
NAMES = {'charger': '蓄波怪', 'ram': '冲撞怪', 'shield': '守盾怪', 'boss': '守关者'}
LAYOUTS = [ [(3,3),(5,3),(3,5),(5,5)], [(3,2),(3,3),(5,5),(5,6)],
            [(2,4),(3,4),(5,4),(6,4)], [(4,2),(4,3),(4,5),(4,6)] ]


class Dungeon:
    upgrade_catalog = UPGRADES
    movement_actions = ('move',)
    movement_directions = DIRS

    def can_step(self, start, destination):
        return self.walkable(destination)

    @property
    def heavy_available(self):
        return 'heavy' in self.upgrades

    def __init__(self, seed=None):
        self.seed = randbelow(1_000_000) if seed is None else seed
        self.version = 1
        self.room = 0
        self.turn = 0
        self.player = dict(x=1, y=7, hp=self.max_hp, energy=0)
        self.upgrades = []
        self.log = []
        self.result = None
        self.choices = []
        self.effects = []
        self.enter_room()

    @property
    def max_hp(self):
        return 6

    @property
    def cap(self):
        return 4 if 'bag' in self.upgrades else 3

    def note(self, text):
        self.log.insert(0, text)
        self.log = self.log[:35]

    def enter_room(self):
        self.player.update(x=1, y=7, energy=0)
        self.echo_used = self.heart_used = False
        self.counter = False
        self.effects = []
        self.choices = []
        self.shrine_used = False
        self.exit = [7, 1]
        rng = Random(self.seed + self.room * 97)
        pillars = LAYOUTS[0] if self.room == 0 else rng.choice(LAYOUTS)
        if self.room == 2:
            pillars = [(3,3),(5,3)]
        self.walls = [[x,y] for y in range(9) for x in range(9)
                      if x in (0,8) or y in (0,8) or (x,y) in pillars]
        kinds = [['charger'], ['charger','ram'], [], ['shield','ram'], ['boss']][self.room]
        if self.room == 3 and rng.choice([False, True]):
            kinds = ['shield', 'charger']
        spots = [(5,7),(6,2),(2,2)] if self.room == 0 else [(6,2),(2,2),(6,6)]
        self.enemies = [dict(id=i, kind=k, name=NAMES[k], x=spots[i][0], y=spots[i][1],
                             hp=6 if k=='boss' else 3 if k=='shield' else 2,
                             energy=0, phase=0) for i,k in enumerate(kinds)]
        self.cleared = not self.enemies
        self.plan()
        self.note(f'进入「{ROOMS[self.room]}」。' + ('泉水在房间中央，移动到泉水上可选择祝福。' if self.room==2 else '敌人已锁定意图；观察后再行动。'))

    def walkable(self, pos):
        return 0 < pos[0] < 8 and 0 < pos[1] < 8 and list(pos) not in self.walls

    def ray(self, pos, direction):
        dx,dy = DIRS[direction]
        cells = []
        for n in range(1,5):
            p = [pos[0]+dx*n, pos[1]+dy*n]
            if not self.walkable(p):
                break
            cells.append(p)
        return cells

    def line_to_player(self, enemy):
        for d in DIRS:
            if [self.player['x'],self.player['y']] in self.ray((enemy['x'],enemy['y']),d):
                return d
        return None

    def step_toward(self, enemy, avoid=()):
        start = (enemy['x'],enemy['y'])
        goal = tuple(enemy.get('last_seen') or (self.player['x'], self.player['y']))
        occupied = {(e['x'],e['y']) for e in self.enemies if e is not enemy}
        queue = [(start, None)]
        visited = {start}
        for pos, first in queue:
            if pos == goal or (goal in avoid and abs(pos[0] - goal[0]) + abs(pos[1] - goal[1]) == 1):
                return first
            for dx,dy in DIRS.values():
                p = (pos[0]+dx,pos[1]+dy)
                if p not in visited and p not in occupied and p not in avoid and self.walkable(p):
                    visited.add(p)
                    queue.append((p, first or list(p)))
        return None

    def plan(self, enemies=None):
        for e in self.enemies if enemies is None else enemies:
            p = [self.player['x'],self.player['y']]
            d = self.line_to_player(e)
            distance = abs(e['x']-p[0])+abs(e['y']-p[1])
            intent = dict(action='wait', label='休整', cells=[])
            boss_intent = self.plan_boss(e, p, distance) if e['kind'] == 'boss' else None
            if boss_intent:
                intent = boss_intent
            elif e['kind']=='shield' and e['phase'] % 3 == 0:
                intent = dict(action='guard', label='举盾 · 挡1伤', cells=[])
            elif e['kind']=='shield' and e['phase'] % 3 == 1:
                intent = dict(action='wait', label='卸盾空档', cells=[])
            elif e['kind'] in ('ram','shield') and distance == 1:
                intent = dict(action='melee', label='冲撞 · 1伤', cells=[p])
            elif e['kind'] in ('charger','boss') and d and e['energy']:
                intent = dict(action='wave', label='出波 · 1伤', direction=d,
                              cells=self.ray((e['x'],e['y']),d))
            elif e['kind'] in ('charger','boss') and e['energy']==0:
                intent = dict(action='charge', label='攒能量', cells=[])
            else:
                step = self.step_toward(e)
                if step:
                    intent = dict(action='move', label='接近', target=step, cells=[])
            e['intent'] = intent

    def plan_boss(self, enemy, player, distance):
        if enemy['phase'] % 4 == 2:
            cells = [[player[0] + dx, player[1]] for dx in (-1, 0, 1)]
            return dict(action='area', label='震荡 · 2伤', cells=[cell for cell in cells if self.walkable(cell)])
        if enemy['phase'] % 4 == 3:
            return dict(action='wait', label='恢复空档', cells=[])
        return None

    def state(self):
        return deepcopy(dict(seed=self.seed, version=self.version, room=self.room,
            roomName=ROOMS[self.room], rooms=ROOMS, turn=self.turn, player=self.player,
            energyCap=self.cap, counter=self.counter, walls=self.walls, exit=self.exit, enemies=self.enemies,
            cleared=self.cleared, result=self.result, choices=self.choices,
            upgrades=[dict(id=k,name=UPGRADES[k][0],description=UPGRADES[k][1]) for k in self.upgrades],
            log=self.log, effects=self.effects, shrine=self.room==2 and not self.shrine_used))

    def reward(self):
        available = [k for k in UPGRADES if k not in self.upgrades]
        picks = Random(self.seed + self.room * 113).sample(available,min(3,len(available)))
        self.choices = [dict(id=k,name=UPGRADES[k][0],description=UPGRADES[k][1]) for k in picks]
        if self.room==2:
            self.choices = [dict(id='heal',name='泉水疗愈',description='立即回复 2 生命（上限 6）。')] + self.choices[:2]

    def act(self, action, direction, version, choice=None):
        if version != self.version:
            raise ValueError('局面已更新，请重新选择。')
        if self.result:
            raise ValueError('本次冒险已结束，请开始新冒险。')
        if self.choices:
            if action != 'choose' or choice not in [c['id'] for c in self.choices]:
                raise ValueError('请先选择一项强化。')
            if choice == 'heal':
                healed = min(2, self.max_hp - self.player['hp'])
                self.player['hp'] += healed
                self.note(f'泉水恢复了 {healed} 生命。')
            else:
                self.upgrades.append(choice)
                self.note('获得强化：'+self.upgrade_catalog[choice][0])
            self.choices=[]
            self.version+=1
            return
        if action == 'exit':
            if not self.cleared or [self.player['x'],self.player['y']] != self.exit:
                raise ValueError('清场后走到右上角出口，才能进入下一间。')
            if self.room >= 4:
                raise ValueError('已经到达最后一间。')
            self.room+=1
            self.enter_room()
            self.version+=1
            return
        if action not in ('move','charge','wave','guard','heavy',*self.extra_actions):
            raise ValueError('未知动作。')
        if ((action in self.movement_actions and direction not in self.movement_directions)
                or (action in ('wave', 'heavy') and direction not in DIRS)):
            raise ValueError('请先选择方向。')
        if self.restrict_safe_actions() and self.cleared and action != 'move':
            raise ValueError('这里很安全，请探索房间或走向出口。')
        cost = self.action_cost(action)
        if action=='heavy' and not self.heavy_available:
            raise ValueError('尚未获得重波。')
        if action in ('wave','heavy') and self.player['energy'] < cost:
            raise ValueError('能量不足，先攒一下。')
        if action=='charge' and self.player['energy']>=self.cap:
            raise ValueError('能量已满。')
        destination = [self.player['x'],self.player['y']]
        if action in self.movement_actions:
            dx,dy=self.movement_directions[direction]
            destination=[destination[0]+dx,destination[1]+dy]
            if not self.can_step((self.player['x'], self.player['y']), destination) or any(
                    [e['x'],e['y']]==destination for e in self.enemies):
                raise ValueError('这格被阻挡了，不消耗行动。')
        self.prepare_action(action, choice)
        self.effects=[]
        self.turn+=1
        # All destinations are locked before moving; occupied-at-start and contested cells block movement.
        occupied = {(e['x'],e['y']) for e in self.enemies} | {(self.player['x'],self.player['y'])}
        targets = [e['intent']['target'] for e in self.enemies if e['intent']['action']=='move']
        if action in self.movement_actions:
            self.note(f'第 {self.turn} 拍 · 调整站位。')
            targets.append(destination)
            if targets.count(destination)==1:
                self.player['x'],self.player['y']=destination
            else:
                self.note('双方争抢同一格，均留在原位。')
        for e in self.enemies:
            it=e['intent']
            if it['action']=='move' and targets.count(it['target'])==1 and tuple(it['target']) not in occupied:
                e['x'],e['y']=it['target']
        if action=='charge':
            amount=self.charge_amount()
            self.player['energy']=min(self.cap,self.player['energy']+amount)
            self.echo_used=True
            self.note(f'第 {self.turn} 拍 · 攒能量。')
        self.resolve_combat(action, direction, cost)
        self.finish_action()
        self.plan()
        self.version+=1

    def action_cost(self, action):
        return 3 if action == 'heavy' else 1

    def resolve_combat(self, action, direction, cost):
        # Calculate every attack before applying deaths, including attacks by lethally hit enemies.
        self.preview_hits = {}
        outgoing={e['id']:0 for e in self.enemies}
        incoming=0
        if action in ('wave','heavy'):
            self.player['energy']-=cost
            bonus = int(self.counter)
            self.counter = False
            if bonus:
                self.note('反击就绪已消耗：本次波伤害 +1。')
            hits=0
            cells=[]
            for cell in self.ray((self.player['x'],self.player['y']),direction):
                cells.append(cell)
                target=next((e for e in self.enemies if [e['x'],e['y']]==cell),None)
                if target:
                    damage=(2 if action=='heavy' else 1) + bonus
                    outgoing[target['id']]=self.wave_damage(damage, target, hits)
                    self.preview_hits[target['id']] = outgoing[target['id']]
                    hits+=1
                    if hits >= (2 if 'pierce' in self.upgrades else 1):
                        break
            self.effects.append(dict(kind='wave',cells=cells))
            self.note(f'第 {self.turn} 拍 · '+('重波' if action=='heavy' else '波')+f'命中 {hits} 个敌人。')
        for e in self.enemies:
            it=e['intent']
            if it['action']=='charge':
                e['energy']=min(3,e['energy']+1)
            if it['action']=='wave':
                e['energy']-=1
                # Enemy rays stop at the first character, without friendly fire.
                cells=[]
                for cell in it['cells']:
                    cells.append(cell)
                    if cell==[self.player['x'],self.player['y']]:
                        incoming+=1
                        break
                    if any(other is not e and [other['x'],other['y']]==cell for other in self.enemies):
                        break
                self.effects.append(dict(kind='enemy',cells=cells))
            elif it['action'] in ('area','melee'):
                if [self.player['x'],self.player['y']] in it['cells']:
                    amount = 2 if it['action']=='area' else 1
                    incoming += amount
                self.effects.append(dict(kind='enemy',cells=it['cells']))
            e['phase']+=1
        blocked=min(1,incoming) if action=='guard' else 0
        if blocked:
            self.counter = True
            self.on_block()
        if blocked and 'heart' in self.upgrades and self.use_heart():
            self.player['hp']=min(6,self.player['hp']+1)
            self.heart_used=True
        self.player['hp']=max(0,self.player['hp']-incoming+blocked)
        if action=='guard':
            self.effects.append(dict(kind='guard',cells=[[self.player['x'],self.player['y']]]))
            self.note(f'第 {self.turn} 拍 · 防御抵挡 {blocked} 点伤害。' + ('反击就绪：下一次波伤害 +1（不叠加）。' if blocked else '未挡到攻击，不获得反击。'))
        if incoming-blocked:
            self.note(f'受到 {incoming-blocked} 点伤害。注意红色危险格。')
        kills=0
        for e in self.enemies:
            e['hp']-=outgoing[e['id']]
            if e['hp']<=0:
                kills+=1
                self.note('击败'+e['name']+'。')
        self.enemies=[e for e in self.enemies if e['hp']>0]
        if 'refund' in self.upgrades:
            self.player['energy']=min(self.cap,self.player['energy']+kills)

    extra_actions = ()

    def prepare_action(self, action, choice):
        pass

    def wave_damage(self, damage, target, hits):
        return max(0, damage - (target['intent']['action'] == 'guard'))

    def on_block(self):
        pass

    def charge_amount(self):
        return 2 if 'echo' in self.upgrades and not self.echo_used else 1

    def use_heart(self):
        return not self.heart_used

    def restrict_safe_actions(self):
        return True

    def finish_action(self):
        if self.player['hp']==0:
            self.result='defeat'
            self.note('冒险结束。记住这次教训，再来一次。')
        elif not self.enemies and not self.cleared:
            self.cleared=True
            self.counter=False
            self.player['energy']=0
            if self.room==4:
                self.result='victory'
                self.note('守关者倒下了。你完成了地牢试炼！')
            else:
                self.reward()
                self.note('房间已清空，选择强化后前往右上角出口。')
        if self.room==2 and not self.shrine_used and [self.player['x'],self.player['y']]==[4,4]:
            self.shrine_used=True
            self.reward()
            self.note('泉水回应了你。选择恢复生命，或获得新的强化。')
    def dump(self):
        return deepcopy(self.__dict__)

    @classmethod
    def restore(cls, data):
        game=cls.__new__(cls)
        game.__dict__.update(deepcopy(data))
        game.__dict__.setdefault('counter', False)
        return game
