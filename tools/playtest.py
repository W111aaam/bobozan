"""Headless smoke player: searches legal actions, never edits game state."""
import sys
from pathlib import Path
from collections import deque
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dungeon import Dungeon, DIRS


def path_to(game, target):
    start=(game.player['x'],game.player['y']);queue=deque([(start,[]) ]);seen={start}
    while queue:
        p,route=queue.popleft()
        if p==tuple(target):return route
        for d,(dx,dy) in DIRS.items():
            q=(p[0]+dx,p[1]+dy)
            if q not in seen and game.walkable(q):
                seen.add(q);queue.append((q,route+[d]))
    raise AssertionError('Unreachable goal')


def score(g):
    if g.result=='defeat':return -10000
    if g.cleared or g.result=='victory':return 10000+g.player['hp']*20
    distance=min(abs(e['x']-g.player['x'])+abs(e['y']-g.player['y']) for e in g.enemies)
    return g.player['hp']*30-sum(e['hp'] for e in g.enemies)*16+g.player['energy']*3-distance*.4-g.turn*.07


def next_action(game):
    candidates=[('charge',None),('guard',None)]+[(a,d) for a in ('move','wave','heavy') for d in DIRS]
    beam=[(score(game),game,None)]
    for depth in range(3):
        expanded=[]
        for _,g,first in beam:
            if g.result or g.cleared:
                expanded.append((score(g),g,first));continue
            for action,d in candidates:
                n=Dungeon.restore(g.dump())
                try:n.act(action,d,n.version)
                except ValueError:continue
                expanded.append((score(n),n,first or (action,d)))
        expanded.sort(key=lambda x:x[0],reverse=True)
        beam=expanded[:8]
    return beam[0][2]


def play(seed, limit=240):
    g=Dungeon(seed);actions=[]
    for _ in range(limit):
        if g.result:return g,actions
        if g.choices:
            preference=['heal','echo','refund','heart','heavy','pierce','bag']
            choices=[c['id'] for c in g.choices]
            c=next(k for k in preference if k in choices)
            a,d='choose',None
        elif g.cleared:
            target=[4,4] if g.room==2 and not g.shrine_used else g.exit
            route=path_to(g,target)
            a,d=('move',route[0]) if route else ('exit',None)
            c=None
        else:
            a,d=next_action(g);c=None
        g.act(a,d,g.version,c)
        actions.append(dict(action=a,direction=d,choice=c))
    raise AssertionError(f'Stalled: room {g.room}, hp {g.player["hp"]}')


if __name__=='__main__':
    import json
    for seed in (0,17,483085):
        g,actions=play(seed)
        print(f'seed={seed}: {g.result}, {g.turn} turns, hp={g.player["hp"]}, room={g.room+1}',flush=True)
        assert g.result=='victory'
        if seed==0:
            Path(__file__).with_name('smoke_replay.json').write_text(json.dumps(actions,indent=2))
