"""Cartes et collisions en coordonnées continues, sans dépendance à Pygame."""
from dataclasses import dataclass
import math

TILE = 48
COLS, ROWS = 19, 12
WIDTH, HEIGHT = COLS * TILE, ROWS * TILE


@dataclass(frozen=True)
class Exit:
    direction: str
    destination: str
    x: int
    y: int


@dataclass(frozen=True)
class Object:
    kind: str
    x: int
    y: int
    label: str = ''
    solid: bool = False
    width: int = 1
    height: int = 1


@dataclass(frozen=True)
class Region:
    name: str
    subtitle: str
    terrain: tuple[str, ...]
    objects: tuple[Object, ...]
    exits: tuple[Exit, ...]
    spawn: tuple[float, float]
    walkways: tuple[tuple[float, float, float, float], ...] = ()
    blockers: tuple[tuple[float, float, float, float], ...] = ()


def terrain(kind: str) -> tuple[str, ...]:
    grid = [['g' for _ in range(COLS)] for _ in range(ROWS)]
    for y in range(ROWS):
        for x in range(COLS):
            if x in (0, COLS - 1) or y in (0, ROWS - 1):
                grid[y][x] = 't'
            if y in (5, 6, 7):
                grid[y][x] = 'd'
    if kind == 'bridge':
        for y in range(ROWS):
            for x in range(6, 12):
                grid[y][x] = 'b' if y in (5, 6) else 'w'
        for y in range(0, 6):
            grid[y][15] = 'd'
        grid[0][15] = 'd'
    if kind in ('ruins', 'gate'):
        for y in range(2, 10):
            for x in range(3, 16):
                grid[y][x] = 's'
    if kind == 'ruins':
        for y in range(6, ROWS):
            grid[y][9] = 's'
    if kind == 'camp':
        for y in range(5, 10):
            for x in range(4, 16):
                grid[y][x] = 'd'
    return tuple(''.join(row) for row in grid)


REGIONS = {
    'camp': Region('Le camp des voyageurs', 'Un refuge au bord des plaines de Dalmasca.', terrain('camp'),
                   (Object('house', 3, 2, solid=True, width=4, height=3),
                    Object('tent', 11, 3, solid=True, width=3, height=2),
                    Object('fire', 8, 7, 'Se reposer'), Object('mira', 6, 7, 'Parler à Mira'),
                    Object('merchant', 12, 7, 'Marchand'), Object('crate', 14, 8, solid=True),
                    Object('tree', 16, 2, solid=True), Object('tree', 2, 9, solid=True)),
                   (Exit('east', 'road', 18, 6),), (9.5 * TILE, 9 * TILE)),
    'road': Region('La route des caravanes', 'Un appel à l’aide traverse les hautes herbes.', terrain('road'),
                   (Object('wagon', 11, 3, solid=True, width=3, height=2),
                    Object('wolf', 10, 7, 'Secourir la caravane'),
                    Object('traveler', 13, 6, 'Le voyageur'),
                    Object('tree', 3, 2, solid=True), Object('tree', 5, 9, solid=True),
                    Object('tree', 15, 9, solid=True), Object('stone', 8, 2, solid=True)),
                   (Exit('west', 'camp', 0, 6), Exit('east', 'bridge', 18, 6)), (2 * TILE, 6.5 * TILE)),
    'bridge': Region('Le pont des murmures', 'L’eau emporte les derniers reflets du jour.', terrain('bridge'),
                     (Object('tree', 3, 3, solid=True), Object('tree', 15, 9, solid=True),
                      Object('sign', 13, 4, 'Lire la stèle'), Object('stone', 4, 9, solid=True)),
                     (Exit('west', 'road', 0, 6), Exit('east', 'gate', 18, 6),
                      Exit('north', 'ruins', 15, 0)), (2 * TILE, 6.5 * TILE),
                     walkways=((228, 232, 456, 72),),
                     blockers=((288, 0, 288, HEIGHT), (228, 304, 456, 32))),
    'ruins': Region('Les ruines du levant', 'Sous la mousse, un ancien pouvoir s’éveille.', terrain('ruins'),
                    (Object('pillar', 4, 3, solid=True), Object('pillar', 14, 3, solid=True),
                     Object('pillar', 4, 8, solid=True), Object('pillar', 14, 8, solid=True),
                     Object('altar', 9, 2, 'Examiner le sceau'),
                     Object('flan', 8, 6), Object('flan', 11, 6), Object('tree', 1, 3, solid=True)),
                    (Exit('south', 'bridge', 9, 11),), (9.5 * TILE, 10 * TILE)),
    'gate': Region('La porte de l’Est', 'Une sentinelle veille sous les remparts.', terrain('gate'),
                   (Object('gate', 7, 1, solid=True, width=5, height=3),
                    Object('boss', 9, 6, 'Défier la Sentinelle'),
                    Object('pillar', 6, 5, solid=True), Object('pillar', 13, 5, solid=True),
                    Object('tree', 2, 8, solid=True)),
                   (Exit('west', 'bridge', 0, 6),), (2 * TILE, 6.5 * TILE)),
}


def passable(region: Region, x: float, y: float) -> bool:
    # Le point correspond aux pieds ; la tête n'entre pas dans les collisions.
    for px, py in ((x - 9, y - 5), (x + 9, y - 5), (x - 9, y + 5), (x + 9, y + 5)):
        tx, ty = int(px // TILE), int(py // TILE)
        if not (0 <= tx < COLS and 0 <= ty < ROWS):
            return False
        on_walkway = any(rx <= px < rx + rw and ry <= py < ry + rh
                         for rx, ry, rw, rh in region.walkways)
        if region.terrain[ty][tx] in ('w', 't') and not on_walkway:
            return False
        if not on_walkway and any(rx <= px < rx + rw and ry <= py < ry + rh
                                  for rx, ry, rw, rh in region.blockers):
            return False
        for obj in region.objects:
            if obj.solid and obj.x * TILE <= px < (obj.x + obj.width) * TILE and obj.y * TILE <= py < (obj.y + obj.height) * TILE:
                return False
    return True


def move(region: Region, x: float, y: float, dx: float, dy: float) -> tuple[float, float]:
    count = max(1, math.ceil(max(abs(dx), abs(dy)) / 5))
    for _ in range(count):
        if passable(region, x + dx / count, y):
            x += dx / count
        if passable(region, x, y + dy / count):
            y += dy / count
    return x, y


def nearby(region: Region, x: float, y: float) -> Object | None:
    candidates = [obj for obj in region.objects if obj.label and
                  math.hypot((obj.x + .5) * TILE - x, (obj.y + .7) * TILE - y) < 86]
    return min(candidates, key=lambda obj: math.hypot((obj.x + .5) * TILE - x, (obj.y + .7) * TILE - y), default=None)
