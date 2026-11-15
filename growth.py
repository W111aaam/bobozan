"""Persistent class, weapon, inscription and talent progression."""

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
        return 5 + len(self.bag_relics)

    @property
    def talent_choice(self):
        if self.result or self.depth not in TALENT_FLOORS or self.depth in self.talent_milestones:
            return None
        options = [dict(id=key, name=name, description=description)
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
            self.note(f'获得遗物「{BAG_RELICS[self.depth]}」，背包容量 +1。')

    def apply_growth(self, action, choice):
        if not self.can_upgrade_weapon():
            raise ValueError('请先脱战，再强化武器。')
        if action == 'forge':
            if self.forge_cores < 1 or self.weapon_level >= 3:
                raise ValueError('锻造核心不足，或当前发射器已达到 +3。')
            self.weapon_levels[self.weapon] = self.weapon_level + 1
            self.forge_cores -= 1
            self.note(f'当前发射器强化至 +{self.weapon_level}。')
        elif action == 'etch':
            if choice not in RUNES or choice == self.rune or self.rune_shards < 1:
                raise ValueError('刻印碎片不足，或请选择不同的刻印。')
            if choice == 'echo' and self.weapon == 'fan':
                raise ValueError('扇形器无法使用回音刻印。')
            if choice == 'echo' and self.weapon == 'return':
                raise ValueError('回旋器已经自带回程。')
            self.inscriptions[self.weapon] = choice
            self.rune_shards -= 1
            self.note('当前发射器获得刻印：' + RUNES[choice][0] + '。')

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

    def wave_damage_before_defense(self, action):
        return ((2 if action == 'heavy' else 1) + int(self.hero_rank >= 3) + self.counter_bonus
                + int(self.mode == 'power') + int(self.weapon_level >= 1)
                + int(self.weapon_level >= 3)
                + int('focus' in self.talents and self.player['energy'] == self.cap))

    def action_cost(self, action):
        if action == 'heavy':
            return 3 - int('economy' in self.talents)
        return 1 + int(action == 'wave' and self.mode == 'power')

    def wave_pierce(self):
        if self.weapon == 'fan':
            return 99
        return 1 + int(self.weapon == 'lance' or 'pierce' in self.upgrades) + int('through' in self.talents)

    def can_upgrade_weapon(self):
        return not (self.result or self.choices or self.talent_choice or self.returning or self.has_threat()
                    or any([e['x'], e['y']] in self.visible and not e.get('dormant') for e in self.enemies))

    def growth_state(self):
        safe = self.can_upgrade_weapon()
        return dict(growthVersion=2, heroClass=self.hero_class, talentChoice=self.talent_choice,
                    bagCapacity=self.bag_capacity,
                    bagRelics=[dict(name=BAG_RELICS[depth], description='背包容量 +1，可将同类种子每 3 颗放一槽' if depth == 5 else '背包容量 +1')
                               for depth in self.bag_relics],
                    heroColor=CLASSES[self.hero_class or 'straight'][1],
                    classes=[dict(id=k, name=name, color=color, description=description)
                             for k, (name, color, description) in CLASSES.items()],
                    growth=dict(safe=safe, cores=self.forge_cores,
                                shards=self.rune_shards, level=self.weapon_level, rune=self.rune,
                                talents=[dict(id=k, depth=depth, name=name, description=description,
                                              learned=k in self.talents)
                                         for k, (depth, name, description) in TALENTS.items()],
                                runes=[dict(id=k, name=name, description=description,
                                            compatible=k != 'echo' or self.weapon in ('straight', 'lance'))
                                       for k, (name, description) in RUNES.items()]),
                    waveStats=dict(damage=self.wave_damage_before_defense('wave'),
                                   heavyDamage=self.wave_damage_before_defense('heavy'),
                                   waveCost=self.action_cost('wave'), heavyCost=self.action_cost('heavy'), range=self.wave_range(
                                       self.weapon, self.mode, self.range_bonus),
                                   pierce=self.wave_pierce(), counterBonus=self.counter_bonus,
                                   guardLimit=1 + int(self.mode == 'armor') + int('guard_mastery' in self.talents)))
