"""Optional encounter behaviors and terrain, resolved on the normal action clock."""
from random import Random

from dungeon import DIRS
from enemy_design import ENEMY_LOOT, FIXED_ENEMY_LOOT


def cell(actor):
    return [actor['x'], actor['y']]


class SideEncounters:
    def init_side_enemy(self, enemy):
        rng = Random(self.seed + self.depth * 49201 + enemy['id'])
        if enemy['kind'] == 'elementcore':
            variants = ('fire', 'frost', 'spark')
            enemy['element'] = variants[(rng.randrange(3) + self.depth) % 3]
            enemy['name'] = dict(fire='火核', frost='霜核', spark='电核')[enemy['element']]
        elif enemy['kind'] == 'armedidol':
            enemy.update(emitter=rng.choice(('straight', 'fan', 'lance', 'return')),
                         inscription=rng.choice(('shatter', 'echo', 'frost')), dormant=True)
        elif enemy['kind'] == 'chestmimic':
            enemy['disguised'] = True

    def plan_side_passive(self, enemy, sees, player):
        kind = enemy['kind']
        origin = cell(enemy)
        if enemy.get('dormant'):
            enemy.pop('last_seen', None)
            enemy['intent'] = dict(action='wait', label='静止 · 受伤后苏醒', cells=[])
            return True
        if kind == 'chestmimic' and enemy.get('disguised'):
            if sees and sum(abs(a-b) for a,b in zip(origin, player)) <= 2:
                self.reveal_mimic(enemy)
                enemy.update(last_seen=player, search=4)
                enemy['intent'] = dict(action='notice', label='宝箱张开 · 本拍不攻击', cells=[])
            else:
                enemy['intent'] = dict(action='wait', label='箱盖微微起伏', cells=[])
            return True
        if kind in ('broodnest', 'canalfish') and not sees:
            enemy.pop('last_seen', None)
            enemy['intent'] = dict(action='wait', label='静伏', cells=[])
            return True
        if kind == 'sparkthief' and enemy.get('stolen') and enemy.get('sound', {}).get('kind') != 'alarm':
            self.plan_thief_escape(enemy, player)
            return True
        return False

    def reveal_mimic(self, enemy):
        enemy['disguised'] = False
        enemy.pop('last_seen', None)
        self.note('拟态宝箱露出了牙齿。')

    def plan_thief_escape(self, enemy, player):
        room = self.rooms_data[enemy['home']]['bounds']
        doors = [p for p in self.doors if room[0] <= p[0] <= room[2] and room[1] <= p[1] <= room[3]]
        origin = cell(enemy)
        goal = enemy.get('escape')
        if goal is None and doors:
            goal = max(doors, key=lambda p: sum(abs(a-b) for a,b in zip(p, player)))
            enemy['escape'] = goal
        if enemy.get('escaped'):
            goal = None
        step = self.step_toward(dict(enemy, last_seen=goal)) if goal and origin != goal else None
        if goal and origin == goal:
            candidates = [[origin[0]+dx, origin[1]+dy] for dx,dy in DIRS.values()]
            step = next((p for p in candidates if self.room_at(p) != enemy['home']
                         and self.enemy_safe_ground(p) and p != player
                         and not any(cell(e) == p for e in self.enemies)), None)
            if step:
                enemy['intent'] = dict(action='move', label='逃出房间', target=step, cells=[], flee=True)
                return
        if step and step != player and not self.unsafe_ground(step):
            enemy['intent'] = dict(action='move', label='携能量逃向门口', target=step, cells=[])
        elif sum(abs(a-b) for a,b in zip(origin, player)) == 1:
            enemy['intent'] = dict(action='melee', label='护住赃物 · 1伤', cells=[player])
        else:
            enemy['intent'] = dict(action='wait', label='藏起偷来的能量', cells=[])

    def side_intent(self, enemy, player, distance, direction, idle, move, melee, wave):
        kind, origin = enemy['kind'], cell(enemy)
        if kind == 'sparkthief':
            return melee('窃能打击', steals=True) if distance == 1 else None
        if kind == 'canalfish':
            if distance == 1:
                return melee('水边扑咬')
            water = [p for p in self.enemy_steps(enemy) if self.tile_at(p)
                     and self.tile_at(p)['kind'] == 'water']
            if water:
                target = min(water, key=lambda p: sum(abs(a-b) for a,b in zip(p,player)))
                if sum(abs(a-b) for a,b in zip(target,player)) < distance:
                    return move('在水中游动', target)
            return idle('潜伏在水里')
        if kind in ('bonesummoner', 'broodnest'):
            if enemy.get('chant_cooldown'):
                return idle('施法中断 · 休整')
            limit = 1 if kind == 'bonesummoner' else 2
            total = sum(e.get('summoner') == enemy['id'] for e in self.enemies)
            targets = self.enemy_steps(enemy)
            if targets and total < limit and not (kind == 'broodnest' and enemy.get('broods', 0) >= 3):
                target = min(targets, key=lambda p: sum(abs(a-b) for a,b in zip(p,player)))
                return idle('标记召唤点' if limit == 1 else '产巢预告孵化', 'chant', warning=[target], target=target)
            if kind == 'broodnest':
                return idle('产巢休眠')
        if kind == 'mirrorwraith' and distance >= 2 and enemy['phase'] % 3 == 0:
            targets = [[player[0]+dx, player[1]+dy] for dx,dy in DIRS.values()]
            targets = [p for p in targets if self.free_enemy_ground(enemy, p)
                       and not self.mob_bound(p) and self.has_sight(origin, p)]
            if len(targets) == 1:
                targets.extend(p for p in self.enemy_steps(enemy) if p not in targets
                               and not self.mob_bound(p))
            if len(targets) >= 2 and not self.mob_bound(origin):
                return dict(move('镜魇 · 锁定真身落点', targets[0]), mob_jump=True, warning=targets[:2])
        if kind == 'webspinner' and not enemy.get('web_laid') and not self.tile_at(player):
            return idle('织网 · 先离开标记格', 'lay_web', warning=[player], target=player)
        if kind == 'elementcore':
            element = enemy['element']
            if element == 'fire' and enemy['phase'] % 3 == 0:
                grass = [cell(t) for t in self.terrain if t['kind'] == 'high_grass'
                         and sum(abs(a-b) for a,b in zip(origin,cell(t))) <= 4
                         and self.has_sight(origin,cell(t))]
                if grass:
                    target = min(grass, key=lambda p: sum(abs(a-b) for a,b in zip(p, player)))
                    return dict(action='ignite', label='点燃高草 · 1伤', cells=[target], damage=1)
            if element == 'frost' and enemy['phase'] % 3 == 0 and not self.tile_at(player):
                return idle('霜印 · 结冰一拍', 'lay_ice', warning=[player], target=player)
        if kind in ('magnetguard', 'webspinner', 'elementcore', 'armedidol', 'bonesummoner'):
            weapon = enemy.get('emitter', 'straight')
            electric = enemy.get('element') == 'spark'
            distance_limit = 6 if electric else 4
            paths = (self.wave_paths(origin, direction, weapon, 'balanced')[0] if weapon == 'fan'
                     else self.trace(origin, direction, distance_limit))
            water = self.conducted_water(paths) if electric else []
            if electric and player not in paths and player not in water:
                for heading in DIRS:
                    if heading == direction:
                        continue
                    candidate = self.trace(origin, heading, distance_limit)
                    flooded = self.conducted_water(candidate)
                    if player in candidate or player in flooded:
                        direction, paths, water = heading, candidate, flooded
                        break
            if player in paths or player in water:
                if not enemy['energy']:
                    return idle('攒力', 'charge')
                label = {'magnetguard':'磁钩拉拽', 'webspinner':'毒针',
                         'elementcore':{'fire':'火花', 'frost':'冷光', 'spark':'折射电波'}.get(enemy.get('element')),
                         'armedidol':'刻印波', 'bonesummoner':'骨灵掩护波'}[kind]
                rune = enemy.get('inscription')
                intent = wave(label, paths, weapon=weapon, direction=direction, pulls=kind=='magnetguard',
                              poison=kind=='webspinner', rune=rune)
                if electric:
                    intent.update(electric=True, water=water)
                    if water:
                        intent['label'] += ' · 浅水导电'
                return intent
        if kind in ('bonesummoner','magnetguard','webspinner','elementcore','armedidol','mirrorwraith',
                    'chestmimic','bonepuppet','broodling') and distance == 1:
            return melee('拟态扑咬' if kind == 'chestmimic' else '近身袭击')
        return None

    def movement_locked(self):
        tile = self.tile_at(cell(self.player))
        return (getattr(self, 'player_snared', False) or getattr(self, 'player_frosted', False)
                or bool(tile and tile['kind'] == 'ice'))

    def mob_bound(self, pos):
        tile = self.tile_at(pos)
        return bool(tile and tile['kind'] == 'web')

    def plan_committed_summon(self, enemy):
        if (target := enemy.get('chant_target')) is not None:
            enemy['intent'] = dict(action='summon', label='召唤即将完成 · 可抢占或打断',
                                   cells=[], warning=[target], target=target)
            return True
        return False

    def resolve_side_intent(self, enemy, intent, hits):
        attack = intent['action']
        if intent.get('flee') and cell(enemy) != self._positions_before[enemy['id']]:
            enemy['escaped'] = True
            enemy.pop('last_seen', None)
        if enemy.get('chant_cooldown') and attack == 'wait':
            enemy.pop('chant_cooldown')
        if attack == 'chant':
            enemy['chant_target'] = intent['target']
        elif attack in ('lay_web', 'lay_ice'):
            target = intent['target']
            if self.projectile_cell(target) and not self.tile_at(target):
                tile = dict(x=target[0], y=target[1], kind='web' if attack=='lay_web' else 'ice')
                if attack == 'lay_ice':
                    tile['expires'] = self.turn
                else:
                    enemy['web_laid'] = True
                self.terrain.append(tile)
                self.effects.append(dict(kind=tile['kind'], cells=[target]))
        elif attack == 'ignite':
            for target in intent['cells']:
                if not self.projectile_cell(target):
                    continue
                if not self.ignite_grass(target):
                    self.effects.append(dict(kind='burn', cells=[target]))
                if cell(self.player) == target:
                    hits.append((1, enemy, {}))

    def resolve_side_hit(self, enemy, intent):
        if intent.get('steals') and self.player['energy'] and not enemy.get('stolen'):
            self.player['energy'] -= 1
            enemy['stolen'] = 1
            self.note('拾能贼偷走 1 能量，正逃向门口。')
        if intent.get('poison'):
            self.poisoned = True
            self.note('毒针命中，下拍中毒 1 伤。')
        if intent.get('pulls') and self.player['hp'] > 0:
            origin = cell(self.player)
            source = cell(enemy)
            if origin[0] == source[0] or origin[1] == source[1]:
                dx,dy = DIRS[self.direction_toward(origin,source)]
                target = [origin[0]+dx, origin[1]+dy]
                if (self.walkable(target) and not self.door_closed(target)
                        and not any(cell(e)==target for e in self.enemies)):
                    self.player.update(x=target[0], y=target[1])
                    self.resolve_fragile_actor('hero', self.player, origin)
                    self.flatten_grass(target)
                    self.trample_plant(self.player)
                    self.effects.append(dict(kind='hook', cells=[origin,target]))
                    self.note('磁钩将你拉近一格。')
        if intent.get('rune') == 'frost':
            self.player_frosted = True
            self.note('凝滞刻印锁住了你的下一次移动。')

    def enemy_loot_chance(self, enemy):
        kind = enemy['kind']
        if not enemy.get('regular_loot') or kind not in ENEMY_LOOT:
            return 0
        count = getattr(self, 'enemy_loot_count', 0)
        if count >= 2:
            return 0
        chance, item = ENEMY_LOOT[kind]
        heal_region = getattr(self, 'enemy_heal_region', None)
        if item == 'kit' and heal_region is not None and heal_region >= (self.depth - 1) // 5:
            return 0
        return chance // 2 if count else chance

    def roll_enemy_loot(self, enemy):
        chance = self.enemy_loot_chance(enemy)
        if not chance:
            return None
        if Random(self.seed + self.depth * 71993 + enemy['id'] * 1103).randrange(100) >= chance:
            return None
        self.enemy_loot_count = getattr(self, 'enemy_loot_count', 0) + 1
        _, item = ENEMY_LOOT[enemy['kind']]
        if item == 'kit':
            self.enemy_heal_region = (self.depth - 1) // 5
        return item

    def finish_side_enemies(self, outgoing, dead):
        fallen = {fall['id'] for fall in self.falls}
        for enemy in dead:
            if enemy['id'] in fallen:
                continue
            drop = ('stolen_energy' if enemy.get('stolen') else
                    FIXED_ENEMY_LOOT.get(enemy['kind']) or self.roll_enemy_loot(enemy))
            if (not drop and enemy['kind'] == 'canalfish' and not getattr(self, 'light_enemy_drop', False)
                    and Random(f'{self.seed}:{self.depth}:{enemy["id"]}:light').randrange(4) == 0):
                self.light_enemy_drop = True
                drop = 'light_wisp'
            if drop:
                x,y = cell(enemy)
                self.features.append(dict(id=f'drop-{enemy["id"]}', kind=drop, x=x, y=y, used=False))
        for enemy in self.enemies[:]:
            damage = outgoing.get(enemy['id'], 0)
            if damage and enemy.pop('dormant', False):
                self.note('武器石像苏醒了。')
            if enemy.get('disguised') and damage:
                self.reveal_mimic(enemy)
            if 'chant_target' not in enemy:
                continue
            if damage:
                del enemy['chant_target']
                enemy['chant_cooldown'] = True
                self.note(enemy['name'] + '的召唤被打断。')
                continue
            if enemy['intent']['action'] != 'summon':
                continue
            target = enemy.pop('chant_target')
            if not self.free_enemy_ground(enemy, target):
                self.note('召唤点被占，召唤失败。')
                continue
            kind = 'bonepuppet' if enemy['kind'] == 'bonesummoner' else 'broodling'
            child = self.add_enemy(kind, target, enemy['home'], 1, summoner=enemy['id'])
            enemy['broods'] = enemy.get('broods', 0) + 1
            self.effects.append(dict(kind='split', cells=[target]))
            self.note(enemy['name'] + '召出了' + child['name'] + '。')
