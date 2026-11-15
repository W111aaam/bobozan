"""Place rooms by role on a loop, then carve entrances and optional branches."""
from random import Random

from enemy_design import REINFORCEMENTS, SIDE_ENCOUNTERS, regional_roster

LAST_FLOOR = 26
REGIONS = ('下水道', '监狱', '洞穴', '矮人都市', '恶魔大厅')
ROOM_LABELS = {
    'entry': '入口', 'combat': '战斗区域', 'shrine': '侧厅',
    'treasure': '补给区域', 'boss': '守关区域', 'branch': '支路',
    'store': '战术库房', 'garden': '封闭花圃', 'alarm_store': '警戒库房', 'dart_vault': '刺针库房',
    'exit': '下层阶梯', 'relic': '终点祭坛', 'standard': '探索区域',
}


def chapter(depth):
    return min(len(REGIONS) - 1, (depth - 1) // 5)


# One optional relic chest, one healing potion and one small spring per region.
RELIC_FLOORS = (3, 8, 13, 18, 23)
HEAL_FLOORS = (1, 7, 12, 17, 22)
SPRING_FLOORS = (2, 9, 14, 19, 24)
LIGHT_VALUES = {'light_wisp': 65, 'light_soul': 105, 'light_radiant': 155}


def generate_layout(seed, depth):
    if depth == LAST_FLOOR or depth % 5 == 0:
        return landmark_layout(depth)
    rng = Random(seed + depth * 7919)
    region = chapter(depth)
    standard = (4, 5, 6, 6, 8)[region] + rng.randrange(3 if region in (0, 3) else 2)
    special = (1, 1, 2, 2, 2)[region] + rng.randrange(3 if region == 1 else 2)
    roles = ['entry', 'combat', 'shrine', 'treasure', 'combat', 'exit']
    roles += ['standard'] * (standard - 2) + ['branch'] * (special - 1)
    ring_width = rng.randint(2, min(4, 1 + standard // 2))
    slots = [(x, 0) for x in range(ring_width)] + [(x, 1) for x in reversed(range(ring_width))]
    if rng.randrange(2):
        slots = [(y, x) for x, y in slots]
    shift = rng.randrange(len(slots))
    slots = slots[shift:] + slots[:shift]
    ring = [0, 1, 4, 5] + rng.sample(list(range(6, 6 + standard - 2)), len(slots) - 4)
    rng.shuffle(ring)
    # Guarantee that the exit is separated from the entrance along the ring.
    ring.remove(5)
    ring.insert((ring.index(0) + len(slots) // 2) % len(slots), 5)
    placements = dict(zip(ring, slots))
    edges = list(zip(ring, ring[1:] + ring[:1]))
    cross_links = [(i, j) for i in ring for j in ring if i < j
                   and sum(abs(a - b) for a, b in zip(placements[i], placements[j])) == 1
                   and (i, j) not in edges and (j, i) not in edges]
    if cross_links and rng.randrange(2):
        edges.append(rng.choice(cross_links))
    reserved_slot = None
    for room_id in [3] + [i for i in range(len(roles)) if i not in ring and i != 3]:
        occupied = set(placements.values())
        candidates = [(parent, (x + dx, y + dy)) for parent, (x, y) in placements.items()
                      for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))
                      if (x + dx, y + dy) not in occupied and (x + dx, y + dy) != reserved_slot]
        parent, slot = rng.choice(candidates)
        placements[room_id] = slot
        if room_id == 3:
            x, y = slot
            reserved_slot = next((x + dx, y + dy) for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))
                                 if (x + dx, y + dy) not in occupied)
        edges.append((parent, room_id))
    min_x = min(x for x, _ in placements.values())
    min_y = min(y for _, y in placements.values())
    rooms = [None] * len(roles)
    centers, entries = {}, {i: [] for i in placements}
    tiles, doors = set(), []
    shape_rng = Random(seed + depth * 19301)

    for room_id, (column, row) in placements.items():
        x, y = 12 + 14 * (column - min_x), 12 + 14 * (row - min_y)
        west, north, east, south = [rng.randint(4, 5) for _ in range(4)]
        kind = roles[room_id]
        shape = 'rectangle'
        if kind in ('combat', 'standard', 'branch'):
            west, north, east, south = [shape_rng.randint(4, 5) for _ in range(4)]
            shape = shape_rng.choice(('compact', 'hall', 'chamfered', 'cross', 'alcove'))
            if shape == 'compact':
                west = east = north = south = 4
            if shape == 'hall':
                if shape_rng.randrange(2):
                    west = east = 5
                    north = south = 4
                else:
                    north = south = 5
                    west = east = 4
        left, top, right, bottom = x - west, y - north, x + east, y + south
        rooms[room_id] = dict(id=room_id, name=ROOM_LABELS[kind], kind=kind,
                              bounds=[left, top, right, bottom], anchor=[x, y], shape=shape,
                              cleared=kind != 'combat', rewarded=False)
        centers[room_id] = (x, y)
        for a in range(left + 1, right):
            for b in range(top + 1, bottom):
                if shape == 'chamfered':
                    edge_x = min(a-left, right-a)
                    edge_y = min(b-top, bottom-b)
                    if edge_x + edge_y <= 3:
                        continue
                if shape == 'cross' and abs(a - x) >= 2 and abs(b - y) >= 2:
                    continue
                if shape == 'alcove' and a > x + 1 and b > y + 1:
                    continue
                tiles.add((a, b))

    def boundary(room_id, dx, dy):
        x, y = centers[room_id]
        left, top, right, bottom = rooms[room_id]['bounds']
        return (right if dx > 0 else left if dx < 0 else x,
                bottom if dy > 0 else top if dy < 0 else y)

    def connect(first, second):
        x, y = centers[first]
        u, v = centers[second]
        dx, dy = (u > x) - (u < x), (v > y) - (v < y)
        start, end = boundary(first, dx, dy), boundary(second, -dx, -dy)
        entries[first].append((start, (dx, dy)))
        entries[second].append((end, (-dx, -dy)))
        doors.extend((list(start), list(end)))
        tiles.update((start, end))
        cx, cy = start[0] + dx, start[1] + dy
        while (cx, cy) != end:
            # A three-wide landing on each side of the door gives a retreating
            # player a sidestep even when the connection itself is short.
            tiles.update((cx - dy * n, cy + dx * n) for n in (-1, 0, 1))
            cx, cy = cx + dx, cy + dy

    for first, second in edges:
        connect(first, second)

    def outward_branch(room_id):
        x, y = placements[room_id]
        dx, dy = next((dx, dy) for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1))
                      if (x + dx, y + dy) not in placements.values())
        gate = boundary(room_id, dx, dy)
        tiles.add(gate)
        for forward in range(1, 5):
            for side in range(-2, 3):
                tiles.add((gate[0] + dx * forward - dy * side,
                           gate[1] + dy * forward + dx * side))
        return gate, (dx, dy)

    # Treasure is a branch endpoint, so at least one exterior face is free.
    lock, (dx, dy) = outward_branch(3)
    cache = (lock[0] + 3 * dx, lock[1] + 3 * dy)
    chest_kind = 'chest' if depth in RELIC_FLOORS else None
    if depth % 5 == (2 if (seed + region) % 2 == 0 else 4):
        chest_kind = 'supply_choice'
    features = [
        dict(id=ident, kind=kind, x=x, y=y, used=False)
        for ident, kind, (x, y) in (
            ('spring', 'shrine' if depth in SPRING_FLOORS else None, centers[2]), ('key', 'key', (centers[2][0] + 1, centers[2][1])),
            ('chest', chest_kind, centers[3]), ('kit', 'kit' if depth in HEAL_FLOORS else None, (centers[3][0] + 1, centers[3][1])),
            ('cache', 'cache', cache),
        )
        if kind is not None
    ]
    next(f for f in features if f['id'] == 'cache')['remaining_items'] = ['smoke' if depth % 2 else 'lure']
    if depth == 2:
        x, y = centers[2]
        features.append(dict(id='seed-supply', kind='grass_seed', x=x-1, y=y, used=False))
    if depth in (6, 16):
        x, y = centers[2]
        features.append(dict(id='sun-seed', kind='sun_seed', x=x-1, y=y, used=False))
    if depth in (7, 17):
        x, y = centers[3]
        features.append(dict(id='terror', kind='terror', x=x-1, y=y, used=False))
    if depth % 5 == 3:
        x, y = centers[2]
        features.append(dict(id='chart', kind='chart', x=x-1, y=y, used=False))
    if depth % 5 == 4:
        x, y = centers[2]
        features.append(dict(id='recall', kind='recall', x=x, y=y+1, used=False))
    # One light ration along the loop, with occasional richer reserves in side rooms.
    light_rng = Random(seed + depth * 23719)
    light_room = light_rng.choice([ident for ident in ring if roles[ident] in ('combat', 'standard')])
    lx, ly = centers[light_room]
    features.append(dict(id='light', kind='light_soul', x=lx, y=ly, used=False))
    if depth % 5 == 4:
        lx, ly = centers[2]
        features.append(dict(id='extra-light', kind=light_rng.choice(('light_wisp', 'light_radiant')),
                             x=lx, y=ly, used=False))
    terrain = []
    rare_room = Random(seed + depth * 7309).randrange(10) == 0
    annex = 'store'
    if not rare_room and depth % 5 in (2, 4):
        annex = ('garden', 'alarm_store')[(seed + region + int(depth % 5 == 4)) % 2]
    elif not rare_room and depth % 5 == 3 and Random(seed + depth * 70001).randrange(3) == 0:
        annex = 'dart_vault'
    if annex == 'garden':
        features.remove(next(f for f in features if f['id'] == 'cache'))
        x, y = cache
        terrain.extend([dict(x=x, y=y, kind='sun_plant'),
                        dict(x=x-dy, y=y+dx, kind='root_plant'),
                        dict(x=x+dy, y=y-dx, kind='high_grass')])
    elif annex == 'alarm_store':
        next(f for f in features if f['id'] == 'cache')['kind'] = 'echo_smoke'
        next(f for f in features if f['id'] == 'cache').pop('remaining_items')
        terrain.append(dict(x=lock[0]+dx, y=lock[1]+dy, kind='trap',
                            mechanism='alarm', armed=True))
    elif annex == 'dart_vault':
        next(f for f in features if f['id'] == 'cache')['kind'] = 'rune_shard'
        next(f for f in features if f['id'] == 'cache').pop('remaining_items')
        for side in range(-2, 3):
            x = lock[0] + 2 * dx - side * dy
            y = lock[1] + 2 * dy + side * dx
            terrain.append(dict(x=x, y=y, kind='trap', mechanism='dart', armed=True))
    if rare_room:
        x, y = cache
        features.append(dict(id='wonder', kind='wonder', x=x + dx, y=y + dy, used=False))
        terrain.extend([dict(x=x - dy, y=y + dx, kind='mirror', slash='/', rotating=True),
                        dict(x=x + dy, y=y - dx, kind='fragile', stage=0)])
    elif annex == 'store':
        # Two parallel mirrors at the sides of the cache leave the entry lane open.
        x, y = cache
        slash = chr(92) if dx else '/'
        terrain.extend(dict(x=x - dy * side, y=y + dx * side, kind='mirror', slash=slash, rotating=False)
                       for side in (-1, 1))

    # Retain this wing's direction before room generation reuses dx and dy.
    gate_x, gate_y = lock
    guard_cells = [(gate_x - 2 * dx - side * dy, gate_y - 2 * dy + side * dx)
                   for side in (2, -2, 1, -1, 0)]
    end_x, end_y = gate_x + 5 * dx, gate_y + 5 * dy
    annex_bounds = [min(gate_x, end_x) - 3 * abs(dy), min(gate_y, end_y) - 3 * abs(dx),
                    max(gate_x, end_x) + 3 * abs(dy), max(gate_y, end_y) + 3 * abs(dx)]
    bx, by = centers[5]
    exit_cell = [bx + 1, by + 1]
    reserved = {tuple(exit_cell), *centers.values()}
    reserved.update((f['x'], f['y']) for f in features)
    for doorway, (dx, dy) in (entry for room in entries.values() for entry in room):
        for forward in range(1, 3):
            for side in (-1, 0, 1):
                reserved.add((doorway[0] - dx * forward - dy * side,
                              doorway[1] - dy * forward + dx * side))

    def interior_candidates(room_id):
        left, top, right, bottom = rooms[room_id]['bounds']
        return [(x, y) for x in range(left + 2, right - 1) for y in range(top + 2, bottom - 1)
                if (x, y) in tiles and (x, y) not in reserved]

    enemies = []
    roster = regional_roster(seed, depth, region)
    for room_id, kind in roster:
        candidates = interior_candidates(room_id)
        off_axis = [p for p in candidates if all(
            p[1] != door[1] if dx else p[0] != door[0] for door, (dx, _) in entries[room_id])]
        cell = rng.choice(off_axis or candidates)
        reserved.add(cell)
        enemies.append((room_id, kind, *cell))

    decorations = [(0, 'mirror'), (1, 'mirror'), (3, 'fragile'), (4, 'fragile')]
    decorations.extend((i, 'mirror' if (i + region) % 3 == 0 else 'fragile')
                       for i, kind in enumerate(roles) if kind == 'standard')
    for room_id, kind in decorations:
        candidates = interior_candidates(room_id)
        if not candidates:
            continue
        x, y = rng.choice(candidates)
        tile = dict(x=x, y=y, kind=kind)
        if kind == 'mirror':
            tile.update(slash=rng.choice(('/', chr(92))), rotating=room_id == 1)
        else:
            tile['stage'] = 0
        terrain.append(tile)

    # Use a separate stream so adding vegetation does not reshuffle rooms or spawns.
    grass_rng = Random(seed + depth * 13007)
    reserved.update((tile['x'], tile['y']) for tile in terrain)
    for room_id, kind in enumerate(roles):
        if kind in ('entry', 'exit'):
            continue
        candidates = set(interior_candidates(room_id))
        if not candidates:
            continue
        for _ in range(2 if kind in ('combat', 'standard') else 1):
            if not candidates:
                break
            x, y = grass_rng.choice(sorted(candidates))
            patch = {(x+a, y+b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                     if (a == b == 0 or grass_rng.random() < 0.64)} & candidates
            for a, b in sorted(patch):
                terrain.append(dict(x=a, y=b, kind='high_grass' if grass_rng.random() < .82 else 'grass'))
            reserved.update(patch)
            candidates.difference_update(patch)

    # Optional encounters get their own room and random stream.
    kind = SIDE_ENCOUNTERS[region][(depth - 1) % 5]
    side_rng = Random(seed + depth * 23117)
    degree = {i: sum(i in edge for edge in edges) for i in range(len(rooms))}
    side_rooms = [i for i in range(6, len(rooms)) if degree[i] == 1] or list(range(6, len(rooms)))
    if kind == 'broodnest':
        side_rooms = [i for i in side_rooms if roles[i] == 'branch'] or side_rooms
    room_id = side_rng.choice(side_rooms)
    x, y = centers[room_id]
    if kind == 'canalfish':
        # A side pool, with walkable banks on both sides.
        pool = [(a, b) for a in (x-1, x, x+1) for b in (y-1, y, y+1)
                if (a, b) in tiles and not any((t['x'], t['y']) == (a, b) for t in terrain)]
        x, y = min(pool, key=lambda p: abs(p[0]-x) + abs(p[1]-y))
        terrain.extend(dict(x=a, y=b, kind='water') for a,b in pool)
    elif (x, y) in {(f['x'], f['y']) for f in features}:
        x, y = side_rng.choice(interior_candidates(room_id) or [(x+1, y)])
    enemies.append((room_id, kind, x, y))
    rooms[room_id]['cleared'] = False

    if depth >= 1:
        trap_rng = Random(seed + depth * 61169)
        reserved.add((x, y))
        occupied_terrain = {(t['x'], t['y']) for t in terrain}
        trap_rooms = [room_id, *[i for i, role in enumerate(roles)
                                  if role in ('combat', 'standard') and i != room_id]]
        for index, ident in enumerate(trap_rooms):
            trap_cells = [cell for cell in interior_candidates(ident) if cell not in occupied_terrain]
            if not trap_cells:
                continue
            tx, ty = trap_rng.choice(trap_cells)
            mechanism = ('alarm' if depth % 2 else 'dart') if index == 0 else trap_rng.choice(('dart', 'grip', 'alarm', 'fall'))
            if index == 0 and depth in (12, 17, 22):
                mechanism = 'grip'
            terrain.append(dict(x=tx, y=ty, kind='trap', mechanism=mechanism, armed=True,
                                hidden=depth >= 3 and trap_rng.randrange(3) != 0))
            occupied_terrain.add((tx, ty))

    if kind == 'elementcore':
        occupied = {(tile['x'], tile['y']) for tile in terrain + features}
        # Paint a shallow pool around the core, with ordinary floor along the banks.
        for a in range(x - 1, x + 2):
            for b in range(y - 1, y + 2):
                if (a, b) in tiles and (a, b) not in occupied:
                    terrain.append(dict(x=a, y=b, kind='water'))

    # Carve an optional pocket only where the rock fully isolates it from other rooms.
    secrets = []
    secret_rng = Random(seed + depth * 38711)
    if depth == 2 or secret_rng.randrange(3) == 0:
        candidates = []
        for ident in (3, 2, *range(6, len(rooms))):
            left, top, right, bottom = rooms[ident]['bounds']
            faces = [(x, y, 0, dy) for x in range(left + 2, right - 1)
                     for y, dy in ((top, -1), (bottom, 1))]
            faces += [(x, y, dx, 0) for y in range(top + 2, bottom - 1)
                      for x, dx in ((left, -1), (right, 1))]
            for x, y, dx, dy in faces:
                if (x-dx, y-dy) not in tiles:
                    continue
                pocket = {(x + dx * n - dy * side, y + dy * n + dx * side)
                          for n in (2, 3) for side in (-1, 0, 1)}
                pocket.add((x + dx, y + dy))
                if min(min(cell) for cell in pocket) < 1 or (x, y) in tiles:
                    continue
                fringe = {(a+u, b+v) for a,b in pocket
                          for u,v in ((0,0),(1,0),(-1,0),(0,1),(0,-1))}
                if not fringe & tiles:
                    candidates.append(((x, y), pocket, (x+3*dx, y+3*dy)))
        if candidates:
            gate, pocket, reward = secret_rng.choice(candidates)
            tiles.update(pocket)
            secrets.append(list(gate))
            features.append(dict(id='secret-reward', kind='rune_shard', x=reward[0], y=reward[1], used=False))

    # Scale population with progress and size, while keeping combat away from entrances.
    population_rng = Random(seed + depth * 84181)
    step = (depth - 1) % 5
    population = (4, 5, 6, 7)[step] + int(region >= 2 and standard >= 7)
    occupied = {(t['x'], t['y']) for t in terrain + features}
    occupied.update((x, y) for _, _, x, y in enemies)
    candidates_by_room = {}
    for ident, role in enumerate(roles):
        if role != 'standard' or ident == room_id:
            continue
        cells = [(a, b) for a, b in interior_candidates(ident)
                 if (a, b) not in occupied
                 and abs(a - centers[0][0]) + abs(b - centers[0][1]) > 8
                 and all(b != door[1] if dx else a != door[0] for door, (dx, _) in entries[ident])]
        if cells:
            candidates_by_room[ident] = cells
    spawn_rooms = list(candidates_by_room)
    population_rng.shuffle(spawn_rooms)
    pool = REINFORCEMENTS[region][:(3 if step < 2 else 5)]
    for ident in (spawn_rooms * 2)[:max(0, population - len(enemies))]:
        cells = candidates_by_room[ident]
        if not cells:
            continue
        a, b = cells.pop(population_rng.randrange(len(cells)))
        enemies.append((ident, population_rng.choice(pool), a, b))
        rooms[ident]['cleared'] = False

    rooms.append(dict(id=len(rooms), name=ROOM_LABELS[annex], kind=annex, bounds=annex_bounds,
                      anchor=list(cache), shape='rectangle', cleared=True, rewarded=False,
                      parent=3))
    if annex == 'alarm_store':
        occupied = {(t['x'], t['y']) for t in terrain + features}
        guard_cell = next(cell for cell in guard_cells if cell not in occupied)
        enemies.append((3, 'ram', *guard_cell))
        rooms[3]['cleared'] = False
    theme_rng = Random(seed + depth * 90731)
    theme = theme_rng.choice((None, None, None, 'water', 'grass')) if depth > 1 else None
    if theme:
        covered = {(t['x'], t['y']) for t in terrain + features}
        covered.update((x, y) for _, _, x, y in enemies)
        for ident, role in enumerate(roles):
            if role not in ('combat', 'standard'):
                continue
            free = set(interior_candidates(ident)) - covered
            patches = []
            for x, y in sorted(free):
                patch = [(a, b) for a in (x, x+1) for b in (y, y+1) if (a, b) in free]
                if len(patch) >= 3:
                    patches.append(patch)
            if patches:
                terrain.extend(dict(x=x, y=y, kind='water' if theme == 'water' else 'high_grass')
                               for x, y in theme_rng.choice(patches))
    # An unused shared face can close a second loop once its hidden door is found.
    shortcuts = []
    if depth >= 6:
        shortcut_rng = Random(seed + depth * 61819)
        candidates = []
        for i in range(1, len(roles)):
            for j in range(i + 1, len(roles)):
                if 5 in (i, j) or (i, j) in edges or (j, i) in edges:
                    continue
                dx = placements[j][0] - placements[i][0]
                dy = placements[j][1] - placements[i][1]
                if abs(dx) + abs(dy) != 1:
                    continue
                start, end = boundary(i, dx, dy), boundary(j, -dx, -dy)
                length = abs(start[0] - end[0]) + abs(start[1] - end[1])
                if length < 2:
                    continue
                passage = [(start[0] + dx * n, start[1] + dy * n) for n in range(length + 1)]
                if any(cell in tiles or (cell[0] - dy, cell[1] + dx) in tiles
                       or (cell[0] + dy, cell[1] - dx) in tiles for cell in passage):
                    continue
                if (start[0] - dx, start[1] - dy) in tiles and (end[0] + dx, end[1] + dy) in tiles:
                    candidates.append(passage)
        if candidates and shortcut_rng.randrange(3) == 0:
            passage = shortcut_rng.choice(candidates)
            if shortcut_rng.randrange(2):
                passage.reverse()
            shortcuts.append(list(passage[0]))
            secrets.extend(shortcuts)
            tiles.update(passage[1:])
            doors.append(list(passage[-1]))
    width = max(x for x, _ in tiles) + 2
    height = max(y for _, y in tiles) + 2
    walls = [[x, y] for y in range(height) for x in range(width) if (x, y) not in tiles]
    return dict(width=width, height=height, walls=walls, doors=doors, rooms_data=rooms,
                lock=list(lock), lock_style=annex, floor_theme=theme, secret_doors=secrets, shortcut_doors=shortcuts, features=features, terrain=terrain, rare_room=rare_room,
                exit=exit_cell, start=list(centers[0]), spawn=enemies)


def landmark_layout(depth):
    """Dedicated arenas every five floors, and a quiet bridge to the relic."""
    tiles, doors, features, terrain = set(), [], [], []
    rooms = []

    def rectangle(left, top, right, bottom):
        tiles.update((x, y) for y in range(top, bottom + 1) for x in range(left, right + 1))

    def area(kind, bounds, anchor, cleared=True):
        rooms.append(dict(id=len(rooms), kind=kind, name=ROOM_LABELS[kind],
                          bounds=bounds, anchor=list(anchor), cleared=cleared, rewarded=False))

    if depth == LAST_FLOOR:
        rectangle(8, 4, 14, 8)
        rectangle(10, 9, 12, 22)
        rectangle(8, 23, 14, 28)
        start, goal = [11, 26], [11, 6]
        area('entry', [7, 22, 15, 29], start)
        area('relic', [7, 3, 15, 9], goal)
        return pack_landmark(tiles, doors, features, terrain, rooms, start, goal, [])

    start, goal = [12, 27], [12, 4]
    rectangle(9, 24, 15, 29)
    rectangle(11, 20, 13, 23)
    rectangle(9, 2, 15, 7)
    rectangle(11, 8, 13, 9)
    doors.extend(([12, 23], [12, 8]))
    for x in (11, 13):
        tiles.discard((x, 23))
        tiles.discard((x, 8))
    arena = depth // 5
    if arena == 1:
        rectangle(5, 10, 19, 20)
        for x, y in ((9, 13), (15, 13), (9, 17), (15, 17)):
            terrain.append(dict(x=x, y=y, kind='mirror', slash='/', rotating=False))
    elif arena == 2:
        rectangle(4, 10, 20, 20)
        for x in (7, 17):
            for y in (11, 12, 18, 19):
                tiles.discard((x, y))
            terrain.append(dict(x=x, y=15, kind='mirror', slash='/', rotating=True))
    elif arena == 3:
        for y in range(10, 21):
            margin = max(0, abs(y - 15) - 2)
            rectangle(4 + margin, y, 20 - margin, y)
        terrain.append(dict(x=18, y=15, kind='rubble'))
        rectangle(19, 14, 22, 16)
        for y in (14, 16):
            tiles.discard((18, y))
        for y in (13, 17):
            for x in range(19, 23):
                tiles.discard((x, y))
        features.append(dict(id='siege-cache', kind='kit', x=21, y=15, used=False))
    elif arena == 4:
        rectangle(4, 10, 20, 20)
        for x in (7, 17):
            for y in (12, 15, 18):
                tiles.discard((x, y))
    else:
        rectangle(8, 9, 16, 20)
        rectangle(3, 12, 21, 18)
        for x in (5, 19):
            for y in (13, 17):
                terrain.append(dict(x=x, y=y, kind='fragile', stage=0))
    area('entry', [8, 23, 16, 30], start)
    area('boss', [2, 9, 23, 22], (12, 15), False)
    area('exit', [8, 1, 16, 8], goal)
    boss = ('boss', 'mirrorboss', 'breaker', 'boss', 'mirrorboss')[arena - 1]
    spawn = [(1, boss, 15 if arena == 3 else 12, 15)]
    if arena >= 4:
        spawn.append((1, 'ram', 15, 16))
    features.append(dict(id='spring', kind='shrine', x=10, y=26, used=False))
    if depth == 15:
        features.append(dict(id='ankh', kind='ankh', x=21, y=16, used=False))
    return pack_landmark(tiles, doors, features, terrain, rooms, start, goal, spawn)


def pack_landmark(tiles, doors, features, terrain, rooms, start, goal, spawn):
    width = max(x for x, _ in tiles) + 2
    height = max(y for _, y in tiles) + 2
    walls = [[x, y] for y in range(height) for x in range(width) if (x, y) not in tiles]
    return dict(width=width, height=height, walls=walls, doors=doors, rooms_data=rooms,
                lock=None, secret_doors=[], features=features, terrain=terrain, rare_room=False,
                exit=goal, start=start, spawn=spawn)
