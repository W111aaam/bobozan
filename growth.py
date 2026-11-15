"""Persistent class, weapon, inscription and talent progression."""
from copy import copy

CLASSES = {
    'straight': ('行波者', '#b9de9e', '直线出波，射程 4 格。'),
    'fan': ('扇流者', '#f0ac75', '短程扇波，可同时命中多个敌人。'),
    'return': ('回旋者', '#bca8ee', '沿去程返波，适合移动后再次命中。'),
    'lance': ('穿锋者', '#8bd9e1', '沿直线穿过至多两个敌人。'),
}
TALENTS = {
    'reach': (1, '延波', '波和重波的基础射程 +1。'),
    'reserve': (1, '深蓄', '能量上限 +1，可与蓄能袋叠加。'),
    'brace': (1, '借势', '反击就绪的伤害加成从 +1 提高至 +2。'),
    'focus': (6, '满蓄出击', '能量全满时发射，波或重波伤害 +1。'),
    'economy': (6, '重波节能', '重波消耗从 3 降至 2 能量，仍需先解锁重波。'),
    'guard_mastery': (6, '沉着防御', '普通防与厚盾最多额外抵挡 1 点总伤害。'),
    'through': (11, '贯阵', '直线类波多穿透一个敌人，扇波改为基础射程 +1。'),
    'undertow': (11, '回流强化', '由自己发射的回程波伤害 +1。'),
    'drain': (11, '波击回收', '同一次发射实际伤到至少两个敌人时，返还 1 能量。'),
}
RUNES = {
    'shatter': ('破甲', '发射的波及其回程无视举盾和护卫护甲。'),
    'echo': ('回音', '直线器和穿透器的波下一拍沿去程返回，回程伤害减半，至少 1。'),
    'frost': ('凝滞', '被波实际伤到的敌人，下一拍若要移动则停在原地。'),
}
TALENTS_PER_TIER = 1
GROWTH_ACTIONS = ('forge', 'etch')
TALENT_FLOORS = (1, 6, 11)
BAG_RELICS = {5: '旅人的侧袋', 15: '工匠的夹层'}


class Growth:
    def init_growth(self, hero_class=None):
        self.hero_class = hero_class
        self.talents = []
        self.weapon_levels = {}
        self.inscriptions = {}
        self.forge_cores = 0
        self.rune_shards = 0
        self.talent_milestones = [] if hero_class else [1]
        self.bag_relics = []
        if hero_class:
            self.weapon = hero_class

    @property
    def bag_capacity(self):
        return 8 + 2 * len(self.bag_relics)

    @property
    def talent_choice(self):
        if self.result or self.depth not in TALENT_FLOORS or self.depth in self.talent_milestones:
            return None
        options = [dict(id=key, name=name, description=description, preview=self.talent_preview(key))
                   for key, (depth, name, description) in TALENTS.items()
                   if depth == self.depth and key not in self.talents]
        limit = min(len(options), max(0, TALENTS_PER_TIER - self.talents_in_tier(self.depth)))
        return dict(depth=self.depth, limit=limit, options=options) if limit else None

    def resolve_talent_choice(self, choices):
        offer = self.talent_choice
        if not offer:
            raise ValueError('只有首次进入指定楼层时才能选择天赋。')
        offered = {item['id'] for item in offer['options']}
        if (not isinstance(choices, list) or len(choices) not in (0, offer['limit'])
                or any(not isinstance(key, str) or key not in offered for key in choices)
                or len(set(choices)) != len(choices)):
            raise ValueError(f"请选择 {offer['limit']} 项不同天赋，或跳过。")
        self.talents.extend(choices)
        self.talent_milestones.append(self.depth)
        self.note('学会天赋：' + '、'.join(TALENTS[key][1] for key in choices) + '。'
                  if choices else '已跳过本层天赋选择。')

    def award_boss_growth(self):
        self.rune_shards += 1
        self.note('守关战奖励：刻印碎片 1 枚。')
        if self.depth in BAG_RELICS and self.depth not in self.bag_relics:
            self.bag_relics.append(self.depth)
            self.note(f'获得遗物「{BAG_RELICS[self.depth]}」，背包容量 +2。')

    def apply_growth(self, action, choice):
        if not self.can_upgrade_weapon():
            raise ValueError('请先脱战，再强化武器。')
        blocked = self.forge_block() if action == 'forge' else self.etch_block(choice)
        if blocked:
            raise ValueError(blocked)
        if action == 'forge':
            self.weapon_levels[self.weapon] = self.weapon_level + 1
            self.forge_cores -= 1
            self.note(f'当前发射器强化至 +{self.weapon_level}。')
        elif action == 'etch':
            self.inscriptions[self.weapon] = choice
            self.rune_shards -= 1
            self.note('当前发射器获得刻印：' + RUNES[choice][0] + '。')

    def forge_block(self):
        if self.weapon_level >= 3:
            return '当前发射器已达到 +3。'
        if self.forge_cores < 1:
            return '缺少锻造核心。'
        return None

    def rune_incompatibility(self, rune):
        if rune == 'echo' and self.weapon == 'fan':
            return '扇形器无法使用回音刻印。'
        if rune == 'echo' and self.weapon == 'return':
            return '回旋器已经自带回程。'
        return None

    def etch_block(self, rune):
        if not isinstance(rune, str) or rune not in RUNES:
            return '请选择有效的刻印。'
        if rune == self.rune:
            return '当前已装备。'
        incompatible = self.rune_incompatibility(rune)
        if incompatible:
            return incompatible
        if self.rune_shards < 1:
            return '缺少刻印碎片。'
        return None

    def talents_in_tier(self, depth):
        return sum(TALENTS[key][0] == depth for key in self.talents)

    @property
    def weapon_level(self):
        return self.weapon_levels.get(self.weapon, 0)

    @property
    def rune(self):
        return self.inscriptions.get(self.weapon)

    @property
    def counter_bonus(self):
        return (1 + int('brace' in self.talents)) if self.counter else 0

    @property
    def range_bonus(self):
        return int(self.weapon_level >= 2) + int('reach' in self.talents) + int(
            self.weapon == 'fan' and 'through' in self.talents)

    def wave_damage_before_defense(self, action, *, player_bonus=True):
        return ((2 if action == 'heavy' else 1) + int(self.hero_rank >= 3) + self.counter_bonus
                + int(self.mode == 'power') + int(self.weapon_level >= 1)
                + int(self.weapon_level >= 3)
                + int('focus' in self.talents and self.player['energy'] == self.cap)
                + int(player_bonus and 'light_wisp' in self.light_blessings))

    def action_cost(self, action):
        if action == 'heavy':
            return 3 - int('economy' in self.talents)
        return 1 + int(action == 'wave' and self.mode == 'power')

    def wave_pierce(self):
        if self.weapon == 'fan':
            return 99
        return 1 + int(self.weapon == 'lance' or 'pierce' in self.upgrades) + int('through' in self.talents)

    @property
    def guard_limit(self):
        return 1 + int(self.mode == 'armor') + int('guard_mastery' in self.talents)

    def return_damage(self, damage):
        base = damage if self.weapon == 'return' else max(1, damage // 2)
        return base + int('undertow' in self.talents)

    def talent_preview(self, talent):
        upgraded = copy(self)
        upgraded.talents = [*self.talents, talent]

        def change(label, before, after, note=None):
            return dict(label=label, before=before, after=after, note=note)

        if talent == 'reach' or (talent == 'through' and self.weapon == 'fan'):
            return change('当前射程',
                          self.wave_range(self.weapon, self.mode, self.range_bonus),
                          self.wave_range(self.weapon, self.mode, upgraded.range_bonus))
        if talent == 'reserve':
            return change('能量上限', self.cap, upgraded.cap)
        if talent == 'brace':
            # Show the bonus after a successful block, regardless of the current stance.
            current = copy(self)
            current.counter = upgraded.counter = True
            return change('反击加伤', current.counter_bonus, upgraded.counter_bonus)
        if talent == 'focus':
            current = copy(self)
            current.player = upgraded.player = dict(self.player, energy=self.cap)
            return change('满能量普通波伤害', current.wave_damage_before_defense('wave'),
                          upgraded.wave_damage_before_defense('wave'))
        if talent == 'economy':
            locked = None if 'heavy' in self.upgrades else '取得重波遗物后生效。'
            return change('重波耗能', self.action_cost('heavy'), upgraded.action_cost('heavy'), locked)
        if talent == 'guard_mastery':
            return change('最多抵挡伤害', self.guard_limit, upgraded.guard_limit)
        if talent == 'through':
            return change('单束最多命中', self.wave_pierce(), upgraded.wave_pierce())
        if talent == 'undertow':
            if self.weapon != 'return' and self.rune != 'echo':
                note = ('当前扇形器无法装回音刻印。' if self.weapon == 'fan'
                        else '当前没有回程波，装备回音刻印后生效。')
                return dict(note=note)
            damage = self.wave_damage_before_defense('wave')
            return change('普通波回程伤害', self.return_damage(damage), upgraded.return_damage(damage))
        if talent == 'drain' and self.wave_pierce() == 1 and not {'parallel', 'double'} & set(self.upgrades):
            return dict(note='当前单次发射通常只能伤到一名敌人。获得额外弹道或穿透后更容易触发。')
        return None

    def class_preview(self, weapon):
        distance = self.wave_range(weapon, 'balanced')
        if weapon == 'fan':
            cells = self.fan_cells([0, 1], 'right', distance)
            targets = [[2, 0], [2, 2]]
        elif weapon == 'lance':
            cells = [[x, 1] for x in range(1, distance + 1)]
            targets = [[2, 1], [distance, 1]]
        else:
            cells = [[x, 1] for x in range(1, distance + 1)]
            targets = [[distance, 1]]
        return dict(range=distance, cells=cells, targets=targets, returns=weapon == 'return')

    def can_upgrade_weapon(self):
        return not (self.result or self.choices or self.talent_choice or self.returning or self.has_threat()
                    or any([e['x'], e['y']] in self.visible and not e.get('dormant') for e in self.enemies))

    def forge_preview(self):
        blocked = self.forge_block()
        if self.weapon_level >= 3:
            return dict(level=self.weapon_level, blocked=blocked, stats=[])
        upgraded = copy(self)
        upgraded.weapon_levels = {**self.weapon_levels, self.weapon: self.weapon_level + 1}
        if upgraded.weapon_level == 2:
            before = self.wave_range(self.weapon, self.mode, self.range_bonus)
            after = upgraded.wave_range(self.weapon, self.mode, upgraded.range_bonus)
            stats = [dict(label='当前射程', before=before, after=after, unit=' 格')]
            note = '基础射程 +1。短距强波将射程减半取整，当前射程保持不变。' if before == after else None
        else:
            actions = [('wave', '普通波伤害')]
            if 'heavy' in self.upgrades:
                actions.append(('heavy', '重波伤害'))
            stats = [dict(label=label, before=self.wave_damage_before_defense(action),
                          after=upgraded.wave_damage_before_defense(action), unit='')
                     for action, label in actions]
            note = None
        return dict(level=upgraded.weapon_level, blocked=blocked, stats=stats, note=note)

    def growth_state(self):
        safe = self.can_upgrade_weapon()
        return dict(growthVersion=5, heroClass=self.hero_class, talentChoice=self.talent_choice,
                    bagCapacity=self.bag_capacity,
                    bagRelics=[dict(name=BAG_RELICS[depth], description='背包容量 +2，同类种子每 5 颗放一槽' if depth == 5 else '背包容量 +2')
                               for depth in self.bag_relics],
                    heroColor=CLASSES[self.hero_class or 'straight'][1],
                    classes=[dict(id=k, name=name, color=color, description=description, preview=self.class_preview(k))
                             for k, (name, color, description) in CLASSES.items()],
                    growth=dict(safe=safe, cores=self.forge_cores,
                                shards=self.rune_shards, level=self.weapon_level, rune=self.rune,
                                forge=self.forge_preview(),
                                talents=[dict(id=k, depth=depth, name=name, description=description,
                                              learned=k in self.talents)
                                         for k, (depth, name, description) in TALENTS.items()],
                                runes=[dict(id=k, name=name, description=description,
                                            compatible=not self.rune_incompatibility(k),
                                            blocked=self.etch_block(k))
                                       for k, (name, description) in RUNES.items()]),
                    waveStats=dict(damage=self.wave_damage_before_defense('wave'),
                                   heavyDamage=self.wave_damage_before_defense('heavy'),
                                   waveCost=self.action_cost('wave'), heavyCost=self.action_cost('heavy'), range=self.wave_range(
                                       self.weapon, self.mode, self.range_bonus),
                                   pierce=self.wave_pierce(), counterBonus=self.counter_bonus,
                                   guardLimit=self.guard_limit))
