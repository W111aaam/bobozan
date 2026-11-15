"""Exercise a full floor using legal actions only; generates an HTTP replay."""
import json
from copy import copy, deepcopy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from floor import FloorDungeon
from dungeon import DIRS
from test_floor import route, position, feature, center
from layout import LAST_FLOOR


def score(g,room):
    if g.result=='defeat':return -10000
    enemies=[e for e in g.enemies if e['home']==room]
    if not enemies:return 10000+g.player['hp']*40
    distance=min(abs(e['x']-g.player['x'])+abs(e['y']-g.player['y']) for e in enemies)
    return g.player['hp']*16-(30 if g.player['hp']<3 else 0)-sum(e['hp'] for e in enemies)*22+g.player['energy']*3+int(g.counter)*4-distance*.4-g.turn*.05


def choose(g,room):
    beam=[(score(g,room),g,None)]
    commands=[('charge',None),('guard',None)]+[(a,d) for a in ('move','wave','heavy','reflect') for d in DIRS]
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
                n.__dict__ = {k: v if k in shared else deepcopy(v) for k, v in vars(node).items()}
                try:n.act(a,d,n.version)
                except ValueError:continue
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
            pref=['heal','echo','refund','heart','heavy','pierce','bag']
            key=next((k for k in pref if k in [c['id'] for c in g.choices]), None)
            if key:
                act('choose',c=key)
            else:
                act('skip_reward')
    def walk(target):
        for _ in range(200):
            if position(g.player) == tuple(target):
                return
            threat = next((e['home'] for e in g.enemies if e.get('last_seen')), None)
            if threat is not None:
                fight(threat)
                continue
            act('move', route(g, target)[0])
        raise AssertionError(f'Route stalled: {target}')

    def charge():
        while g.player['energy'] < g.cap:
            act('charge')

    def fight(room):
        for _ in range(120):
            if g.player['hp'] <= 2 and 'heal' in g.inventory and not g.has_threat():
                act('item', c='heal')
            if not any(e['home']==room for e in g.enemies):
                return
            a,d=choose(g,room)
            act(a,d)
        raise AssertionError(f'Fight stalled on floor {g.depth}, room {room}: {g.player}, {g.enemies}')

    for depth in range(1, last_depth + 1):
        if depth < LAST_FLOOR:
            if g.forge_cores and g.weapon_level < 3:
                act('forge')
            if g.player['hp'] <= g.max_hp - 2 and 'heal' in g.inventory:
                act('item', c='heal')
            if depth in (1, 3, 8, 13, 18, 23):
                walk(position(feature(g, 'kit' if depth == 1 else 'chest')))
                if g.forge_cores and g.weapon_level < 3:
                    act('forge')
            charge()
            spring = feature(g, 'spring')
            if spring['kind'] == 'shrine' and g.player['hp'] < g.max_hp:
                walk(position(spring))
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
