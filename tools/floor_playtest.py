"""Exercise a full floor using legal actions only; generates an HTTP replay."""
import json
from copy import copy, deepcopy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from floor import FloorDungeon
from dungeon import DIRS
from test_floor import position, feature, center
from layout import LAST_FLOOR, LIGHT_VALUES


def score(g,room):
    if g.result=='defeat':return -10000
    enemies=[e for e in g.enemies if e['home']==room]
    if not enemies:return 10000+g.player['hp']*40
    distance=min(abs(e['x']-g.player['x'])+abs(e['y']-g.player['y']) for e in enemies)
    lined_up = any(e['x'] == g.player['x'] or e['y'] == g.player['y'] for e in enemies)
    return g.player['hp']*16-(30 if g.player['hp']<3 else 0)-sum(e['hp'] for e in enemies)*22+g.player['energy']*3+int(g.counter)*4-distance*.6+lined_up*.4-g.turn*.05


def choose(g,room):
    beam=[(score(g,room),g,None)]
    commands=[('charge',None),('guard',None),('stored_charge',None)]+[(a,d) for a in ('move','wave','heavy','reflect') for d in DIRS]
    for _ in range(3):
        options=[]
        for _,node,first in beam:
            if node.result or node.choices or not any(e['home']==room for e in node.enemies):
                options.append((score(node,room),node,first));continue
            for a,d in commands:
                # Combat branches never regenerate geometry. Share immutable
                # map data and clone only state that an action can change.
                n = copy(node)
                shared = {'walls', '_wall_cells', 'doors', '_door_cells'}
                n.__dict__ = {k: v if k in shared else deepcopy(v) for k, v in vars(node).items()
                              if k != 'floor_snapshots'}
                n.floor_snapshots = {}
                try:n.act(a,d,n.version)
                except ValueError:continue
                if n.depth != g.depth:
                    continue
                options.append((score(n,room),n,first or (a,d)))
        options.sort(key=lambda x:x[0],reverse=True);beam=options[:6]
    return beam[0][2]


def play(seed, last_depth=LAST_FLOOR):
    g=FloorDungeon(seed);commands=[]
    def act(a,d=None,c=None):
        g.act(a,d,g.version,c);commands.append(dict(action=a,direction=d,choice=c))
        if g.result=='defeat':raise AssertionError(f'Defeat on floor {g.depth} in room {g.room}: {g.log[:5]}')
        if g.talent_choice:
            act('choose_talents', c=[])
        if g.choices:
            pref=['heal','echo','refund','heart','reflect','pierce','bag']
            key=next((k for k in pref if k in [c['id'] for c in g.choices]), None)
            if key:
                act('choose',c=key)
            else:
                act('skip_reward')

    def nearby_threat():
        px, py = position(g.player)
        candidates = [enemy for enemy in g.enemies if enemy.get('last_seen')
                      or (enemy.get('sound') and enemy['kind'] not in ('canalfish', 'broodnest')
                          and abs(enemy['x'] - px) + abs(enemy['y'] - py) <= 5)]
        return min(candidates, key=lambda enemy: abs(enemy['x'] - px) + abs(enemy['y'] - py), default=None)

    def safe_step(targets):
        source = position(g.player)
        queue = [(source, None)]
        seen = {source}
        hazards = {position(tile) for tile in g.terrain if tile['kind'] == 'fragile'
                   or (tile['kind'] == 'trap' and tile['armed'])}
        hazards.update(position(enemy) for enemy in g.enemies)
        for cell, step in queue:
            if cell in targets:
                return step
            for direction, (dx, dy) in DIRS.items():
                neighbor = cell[0] + dx, cell[1] + dy
                if neighbor not in seen and neighbor not in hazards and g.walkable(neighbor):
                    seen.add(neighbor)
                    queue.append((neighbor, step or direction))
        return None

    def walk(target):
        for _ in range(200):
            if position(g.player) == tuple(target):
                return
            threat = nearby_threat()
            if threat is not None:
                fight(threat['home'])
                continue
            step = safe_step({tuple(target)})
            if step:
                act('move', step)
            else:
                if any(position(enemy) == tuple(target) for enemy in g.enemies):
                    fight(next(enemy['home'] for enemy in g.enemies if position(enemy) == tuple(target)))
                    continue
                raise AssertionError(f'No safe route to {target} on floor {g.depth}')
        raise AssertionError(f'Route stalled: {target}')

    def charge():
        while g.player['energy'] < g.cap:
            act('charge')

    def fight(room):
        for _ in range(120):
            if g.player['hp'] <= 2 and 'heal' in g.inventory and not g.has_threat():
                act('item', c='heal')
            enemies = [e for e in g.enemies if e['home'] == room]
            if not enemies:
                return
            if not g.movement_locked() and not any(e.get('last_seen') for e in enemies):
                rays = {(x, y) for direction in DIRS for x, y in g.trace(position(g.player), direction)}
                if not any(position(e) in rays for e in enemies):
                    goals = {(e['x'] + dx, e['y'] + dy) for e in enemies for dx, dy in DIRS.values()}
                    step = safe_step(goals)
                    if step:
                        act('move', step)
                        continue
            a,d=choose(g,room)
            act(a,d)
        raise AssertionError(f'Fight stalled on floor {g.depth}, room {room}: {g.player}, {g.enemies}')

    for depth in range(1, last_depth + 1):
        if depth < LAST_FLOOR:
            threat = nearby_threat()
            if threat:
                fight(threat['home'])
            if g.forge_cores and g.weapon_level < 3 and g.can_upgrade_weapon():
                act('forge')
            if g.player['hp'] <= g.max_hp - 2 and 'heal' in g.inventory:
                act('item', c='heal')
            if depth in (1, 3, 8, 13, 18, 23):
                walk(position(feature(g, 'kit' if depth == 1 else 'chest')))
                if g.forge_cores and g.weapon_level < 3 and g.can_upgrade_weapon():
                    act('forge')
            charge()
            spring = next((feature for feature in g.features if feature['kind'] == 'shrine'), None)
            if spring and g.player['hp'] < g.max_hp:
                walk(position(spring))
            for light in g.features[:]:
                if (not light['used'] and light['kind'] in LIGHT_VALUES and g.sanity <= 355
                        and safe_step({position(light)})):
                    walk(position(light))
            charge()
            if depth % 5 in (0, 4):
                walk(center(g, 1))
                fight(1)
        walk(g.exit)
        act('exit')
        print(f'floor {depth}: hp={g.player["hp"]}, turns={g.turn}', flush=True)
    return g,commands

if __name__=='__main__':
    for seed in (0,):
        g,commands=play(seed)
        print(f'seed={seed}: {g.result}, hp={g.player["hp"]}, turns={g.turn}',flush=True)
        if seed==0:Path(__file__).with_name('floor_replay.json').write_text(json.dumps(commands,indent=2))
