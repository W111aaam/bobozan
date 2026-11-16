"""Persistent class, weapon, inscription and talent progression."""
from copy import copy
from random import Random

CLASSES = {
    'straight': ('行波者', '#b9de9e', '直线出波。可主动闪避已锁定的攻击并回能。'),
    'fan': ('扇流者', '#f0ac75', '近战波覆盖周围八格，可斜向行走。'),
    'return': ('回旋者', '#bca8ee', '发射能量球，停留一拍后飞回玩家行动后的位置。'),
    'lance': ('穿锋者', '#8bd9e1', '波不限射程并贯穿全部敌人，射程加成转为伤害。'),
}
DODGE_COOLDOWN = 30
CLASS_ABILITIES = {
    'straight': ('闪避', f'移动一格。若避开至少一次原本会命中的已锁定攻击，获得 1 能量。移动成功后冷却 {DODGE_COOLDOWN} 拍。'),
    'fan': ('斜向移动', '可点击斜邻地格或用数字小键盘 7、9、1、3 斜向移动。不能穿过墙角和关门。'),
    'return': ('回旋球', '能量球在目标格或首个命中的敌人处停留，下一拍飞回你行动后的位置。'),
    'lance': ('无限贯穿', '波穿过射线上的所有敌人。每 +1 射程转为 +20% 波伤，合计后向上取整。'),
}
WEAPON_DAMAGE = {'straight': 6, 'fan': 5, 'return': 5, 'lance': 6}
TALENTS = {
    'reach': (1, '延波', '波和重波的基础射程 +1。'),
    'reserve': (1, '深蓄', '能量上限 +1，可与蓄能袋叠加。'),
    'brace': (1, '借势', '反击就绪的伤害加成从 +3 提高至 +5。'),
    'focus': (6, '满蓄出击', '能量全满时发射，波或重波伤害 +2。'),
    'economy': (6, '重波节能', '重波消耗从 3 降至 2 能量。'),
    'guard_mastery': (6, '沉着防御', '普通防与厚盾最多额外抵挡 2 点总伤害。'),
    'through': (11, '贯阵', '直线类波多穿透一个敌人，扇波改为基础射程 +1。'),
    'undertow': (11, '回流强化', '由自己发射的回程波伤害 +2。'),
    'drain': (11, '波击回收', '同一次发射实际伤到至少两个敌人时，返还 1 能量。'),
}
RUNES = {
    'shatter': ('破甲', '发射的波及其回程无视举盾和护卫护甲。'),
    'echo': ('回音', '直线器和穿透器的波下一拍沿去程返回，回程伤害减半，至少 1。'),
    'frost': ('凝滞', '被波实际伤到的敌人，下一拍若要移动则停在原地。'),
    'point_blank': ('近战', '主束命中上下左右相邻的敌人时，伤害乘以 1.5，向上取整后再计算护甲。'),
    'shield_erosion': ('蚀盾', '主束命中后削减目标 1 点防御，最低为 0。本次命中仍按原防御结算，即使伤害被完全抵挡也能蚀盾。'),
    'range_break': ('中断', '主束命中正在蓄力或已经锁定蓄力攻击的敌人，每次使其下一发射程缩短 1 格（最低 0）。敌人仍会出招。'),
    'stagger': ('击晕', '连续两拍以主束命中同一敌人后，该敌人跳过下一拍。触发后重新计数。'),
    'refraction': ('折射', '主束首次命中后，向距离命中点 8 格内最近的另一名可直达敌人发射一条折射光束。伤害为主束的一半，向下取整，最低 1，再计算防御。'),
    'conduction': ('导电', '主束每次造成伤害都会放电。命中未冻结浅水里的敌人时，同片浅水里的其他敌人受到等量伤害。其余情况下，命中点半径 6 格内的其他敌人受到本发主束攻击力一半的伤害，向下取整，最低 1。'),
}
TALENTS_PER_TIER = 1
TALENT_FLOORS = (1, 6, 11)
BAG_RELICS = {5: '旅人的侧袋', 15: '工匠的夹层'}
STRIDE_LAUNCHER = 'stride_launcher'
BARRIER_FAN = 'barrier_fan'
TIDE_LAUNCHER = 'tide_launcher'
SNIPER_LAUNCHER = 'sniper_launcher'
CLOSE_FAN = 'close_fan'
LAUNCHERS = {
    STRIDE_LAUNCHER: ('straight', '踏步枪', '实际行走后，下一发波或重波射程 +1。可以先攒能或防御，发射时消耗效果。'),
    BARRIER_FAN: ('fan', '屏障扇', '成功格挡或反射后，下一发攻击 +2 伤害。'),
    TIDE_LAUNCHER: ('return', '潮折器', '回旋球的回程伤害 +2。'),
    SNIPER_LAUNCHER: ('straight', '狙线器', '主束命中距离 3 格及以上的敌人时伤害 +3；相邻命中伤害 −2，计算防御前最低 1 伤。'),
    CLOSE_FAN: ('fan', '近身扇', '波和重波覆盖角色周围八格，伤害乘以 1.5 并向上取整。石墙和关门会遮挡。'),
}
LEGACY_LAUNCHER_DESCRIPTIONS = {
    BARRIER_FAN: '成功格挡或反射后，下一发扇波在最远一排的两端各多覆盖一格。',
    TIDE_LAUNCHER: '回波在下一拍飞向你行动后的位置。侧移可改变回程，石墙和关门会阻断回波。',
}


class Growth:
    def init_growth(self, hero_class=None):
        self.hero_class = hero_class
        self.talents = []
        self.weapon_levels = {}
        self.inscriptions = {}
        self.forge_cores = 0
        self.dropped_runes = []
        self.launcher_upgrades = {}
        self.owned_launchers = []
        self.stride_ready = False
        self.barrier_ready = False
        self.dodge_ready_turn = 0
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
        if self.depth in BAG_RELICS and self.depth not in self.bag_relics:
            self.bag_relics.append(self.depth)
            self.note(f'获得遗物「{BAG_RELICS[self.depth]}」，背包容量 +2。')

    def forge_weapon(self):
        if not self.can_upgrade_weapon():
            raise ValueError('请先脱战，再强化武器。')
        blocked = self.forge_block()
        if blocked:
            raise ValueError(blocked)
        self.weapon_levels[self.weapon] = self.weapon_level + 1
        self.forge_cores -= 1
        self.note(f'当前发射器强化至 +{self.weapon_level}。')

    def assign_rune_drop(self, feature):
        order = list(RUNES)
        Random(f'{self.seed}:rune-drops').shuffle(order)
        rune = next((rune for rune in order if rune not in self.dropped_runes), None)
        if rune is None:
            return False
        self.dropped_runes.append(rune)
        feature.update(kind='rune', rune=rune)
        return True

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
        return (3 + 2 * ('brace' in self.talents)) if self.counter else 0

    @property
    def launcher(self):
        return self.launcher_upgrades.get(self.weapon)

    @property
    def launcher_details(self):
        return self.launcher_info(self.launcher) if self.launcher in LAUNCHERS else None

    def launcher_info(self, launcher):
        family, name, description = LAUNCHERS[launcher]
        if not self.hero_class:
            description = LEGACY_LAUNCHER_DESCRIPTIONS.get(launcher, description)
        return family, name, description

    @property
    def barrier_wide(self):
        return self.launcher == BARRIER_FAN and self.barrier_ready

    @property
    def close_fan(self):
        return self.launcher == CLOSE_FAN

    @property
    def radial_wave(self):
        return self.close_fan or self.hero_class == 'fan'

    @property
    def unlimited_wave(self):
        return self.hero_class == 'lance'

    @property
    def orb_wave(self):
        return self.hero_class == 'return'

    @property
    def dodge_cooldown(self):
        return max(0, self.dodge_ready_turn - self.turn)

    @property
    def stride_range(self):
        return int(self.launcher == STRIDE_LAUNCHER and self.stride_ready)

    @property
    def range_bonus(self):
        through_range = 'through' in self.talents and (self.unlimited_wave or self.weapon == 'fan')
        return int(self.weapon_level >= 2) + int('reach' in self.talents) + int(through_range)

    @property
    def shot_range_bonus(self):
        # The emitter extends the final range by one, including in power mode.
        return self.range_bonus + self.stride_range * (2 if self.mode == 'power' else 1)

    def player_wave_range(self, *, include_ready=True):
        bonus = self.shot_range_bonus if include_ready else self.range_bonus
        if self.unlimited_wave:
            return None
        return 1 if self.radial_wave else self.wave_range(self.weapon, self.mode, bonus)

    def wave_damage_before_defense(self, action, *, player_bonus=True):
        damage = (WEAPON_DAMAGE[self.weapon] + 5 * (action == 'heavy') + self.hero_rank + self.counter_bonus
                  + 3 * ((self.mode == 'power') + (self.weapon_level >= 1) + (self.weapon_level >= 3))
                  + 2 * ('focus' in self.talents and self.player['energy'] == self.cap)
                  + int(player_bonus and 'light_wisp' in self.light_blessings))
        if self.unlimited_wave:
            damage = (damage * (5 + self.shot_range_bonus) + 4) // 5
        if self.hero_class == 'fan':
            damage += self.range_bonus + 2 * (player_bonus and self.barrier_wide)
        return (3 * damage + 1) // 2 if player_bonus and self.close_fan else damage

    def main_impact_damage(self, damage, distance):
        if self.launcher == SNIPER_LAUNCHER and distance is not None:
            return max(1, damage + 3 * (distance >= 3) - 2 * (distance == 1))
        return damage

    def launcher_preview(self, launcher):
        candidate = copy(self)
        candidate.launcher_upgrades = {**self.launcher_upgrades, self.weapon: launcher}

        def coverage(game):
            distance = game.player_wave_range(include_ready=False)
            if game.launcher == STRIDE_LAUNCHER:
                return f'{distance} 格 · 行走后 {distance + 1} 格'
            if game.launcher == BARRIER_FAN:
                return f'{distance} 格 · 格挡后加宽'
            return '周围八格' if game.radial_wave else '不限' if distance is None else f'{distance} 格'

        def damage(game, action):
            base = game.wave_damage_before_defense(action)
            if game.launcher != SNIPER_LAUNCHER:
                return str(base)
            labels = ('1 格', '2 格', '3 格以上')
            distance = game.player_wave_range(include_ready=False)
            return ' · '.join(f'{label} {game.main_impact_damage(base, step)} 伤'
                              for step, label in enumerate(labels, 1) if step <= distance)

        stats = [dict(label='覆盖', before=coverage(self), after=coverage(candidate))]
        if self.weapon == 'return':
            routes = {TIDE_LAUNCHER: '飞向行动后的位置'}
            route = '飞向行动后的位置' if self.orb_wave else '沿去程'
            stats.append(dict(label='回程', before=routes.get(self.launcher, route),
                              after=routes.get(launcher, route)))
            if self.orb_wave:
                stats.append(dict(label='回程波伤害', before=self.return_damage(self.wave_damage_before_defense('wave')),
                                  after=candidate.return_damage(candidate.wave_damage_before_defense('wave'))))
        actions = [('wave', '波伤害'), ('heavy', '重波伤害')]
        stats.extend(dict(label=label, before=damage(self, action), after=damage(candidate, action))
                     for action, label in actions)
        return stats

    def action_cost(self, action):
        if action == 'heavy':
            return 3 - int('economy' in self.talents)
        return 1 + int(action == 'wave' and self.mode == 'power')

    def wave_pierce(self):
        if self.unlimited_wave:
            return None
        if self.weapon == 'fan':
            return 99
        return 1 + int(self.weapon == 'lance' or 'pierce' in self.upgrades) + int('through' in self.talents)

    @property
    def guard_limit(self):
        return 4 + 4 * (self.mode == 'armor') + 2 * ('guard_mastery' in self.talents)

    def return_damage(self, damage):
        base = damage if self.weapon == 'return' else max(1, damage // 2)
        return base + 2 * ('undertow' in self.talents) + 2 * (self.orb_wave and self.launcher == TIDE_LAUNCHER)

    def talent_preview(self, talent):
        upgraded = copy(self)
        upgraded.talents = [*self.talents, talent]

        def change(label, before, after, note=None):
            return dict(label=label, before=before, after=after, note=note)

        if talent == 'reach' and self.unlimited_wave:
            return change('普通波伤害', self.wave_damage_before_defense('wave'), upgraded.wave_damage_before_defense('wave'),
                          '无限贯穿 · 每 1 格射程转为 +20% 波伤。')
        if talent in ('reach', 'through') and self.hero_class == 'fan':
            return change('普通波伤害', self.wave_damage_before_defense('wave'), upgraded.wave_damage_before_defense('wave'),
                          '近战范围固定。延波与贯阵各提供 +1 波伤。')
        if talent == 'reach' or (talent == 'through' and self.weapon == 'fan'):
            return change('当前射程',
                          self.player_wave_range(include_ready=False), upgraded.player_wave_range(include_ready=False),
                          '近身扇固定覆盖身边八格，其他同系发射器可获得射程加成。' if self.close_fan else None)
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
            return change('重波耗能', self.action_cost('heavy'), upgraded.action_cost('heavy'))
        if talent == 'guard_mastery':
            return change('最多抵挡伤害', self.guard_limit, upgraded.guard_limit)
        if talent == 'through' and self.unlimited_wave:
            return change('普通波伤害', self.wave_damage_before_defense('wave'), upgraded.wave_damage_before_defense('wave'),
                          '无限贯穿 · 贯阵额外提供 +1 格等效射程。')
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
            distance = 2
            cells = [[x, y] for x in range(3) for y in range(3) if [x, y] != [1, 1]]
            targets = [[2, 0], [2, 2]]
        elif weapon == 'lance':
            cells = [[x, 1] for x in range(1, distance + 1)]
            targets = [[2, 1], [distance, 1]]
        else:
            cells = [[x, 1] for x in range(1, distance + 1)]
            targets = [[distance, 1]]
        return dict(range=distance, damage=WEAPON_DAMAGE[weapon], cells=cells, targets=targets, returns=weapon == 'return',
                    origin=[1 if weapon == 'fan' else 0, 1])

    def can_upgrade_weapon(self):
        return not (self.result or self.choices or self.talent_choice or self.returning or self.has_threat()
                    or any([e['x'], e['y']] in self.visible and not e.get('dormant') for e in self.enemies))

    def forge_preview(self):
        blocked = self.forge_block()
        if self.weapon_level >= 3:
            return dict(level=self.weapon_level, blocked=blocked, stats=[])
        upgraded = copy(self)
        upgraded.weapon_levels = {**self.weapon_levels, self.weapon: self.weapon_level + 1}
        if upgraded.weapon_level == 2 and not (self.unlimited_wave or self.hero_class == 'fan'):
            before = self.player_wave_range(include_ready=False)
            after = upgraded.player_wave_range(include_ready=False)
            stats = [dict(label='当前射程', before=before, after=after, unit=' 格')]
            note = '基础射程 +1。短距强波将射程减半取整，当前射程保持不变。' if before == after else None
            if self.close_fan:
                note = '近身扇固定覆盖身边八格，其他同系发射器可获得射程加成。'
        else:
            actions = [('wave', '普通波伤害'), ('heavy', '重波伤害')]
            stats = [dict(label=label, before=self.wave_damage_before_defense(action),
                          after=upgraded.wave_damage_before_defense(action), unit='')
                     for action, label in actions]
            note = None
        return dict(level=upgraded.weapon_level, blocked=blocked, stats=stats, note=note)

    def growth_state(self):
        safe = self.can_upgrade_weapon()
        launcher = self.launcher_details
        launchers = [dict(id=key, name=name, description=self.launcher_info(key)[2], active=key == self.launcher)
                     for key, (family, name, _) in LAUNCHERS.items()
                     if family == self.weapon and key in self.owned_launchers]
        return dict(growthVersion=7, heroClass=self.hero_class, talentChoice=self.talent_choice,
                    bagCapacity=self.bag_capacity,
                    bagRelics=[dict(name=BAG_RELICS[depth], description='背包容量 +2，同类种子每 5 颗放一槽' if depth == 5 else '背包容量 +2')
                               for depth in self.bag_relics],
                    heroColor=CLASSES[self.hero_class or 'straight'][1],
                    classes=[dict(id=k, name=name, color=color, description=description, preview=self.class_preview(k))
                             for k, (name, color, description) in CLASSES.items()],
                    classAbility=(dict(name=CLASS_ABILITIES[self.hero_class][0], description=CLASS_ABILITIES[self.hero_class][1],
                                       cooldown=self.dodge_cooldown, active=self.hero_class == 'straight')
                                  if self.hero_class else None),
                    canReflect='reflect' in self.upgrades,
                    growth=dict(safe=safe, cores=self.forge_cores,
                                level=self.weapon_level, runeName=RUNES[self.rune][0] if self.rune else None,
                                runeDescription=RUNES[self.rune][1] if self.rune else None,
                                emitterName=launcher[1] if launcher else None,
                                emitterDescription=launcher[2] if launcher else None,
                                launchers=launchers,
                                strideReady=bool(self.stride_range),
                                barrierReady=self.barrier_wide,
                                closeFan=self.radial_wave, orbWave=self.orb_wave,
                                forge=self.forge_preview(),
                                talents=[dict(id=k, depth=depth, name=name, description=description,
                                              learned=k in self.talents)
                                         for k, (depth, name, description) in TALENTS.items()]),
                    waveStats=dict(damage=self.wave_damage_before_defense('wave'),
                                   heavyDamage=self.wave_damage_before_defense('heavy'),
                                   waveCost=self.action_cost('wave'), heavyCost=self.action_cost('heavy'),
                                   range=self.player_wave_range(),
                                   pierce=self.wave_pierce(), counterBonus=self.counter_bonus,
                                   guardLimit=self.guard_limit))
