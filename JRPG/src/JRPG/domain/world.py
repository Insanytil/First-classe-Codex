"""Cartes immuables et monde en mémoire : collisions et invariants sans SDL."""

from dataclasses import dataclass
from enum import StrEnum
from math import ceil, hypot, isfinite

from JRPG.domain.errors import DomainError
from JRPG.domain.items import ItemQuantity
from JRPG.domain.stats import require_integer, require_text

TILE_SIZE = 32


class Tile(StrEnum):
    GRASS = "."
    PATH = ":"
    WATER = "~"
    WALL = "#"
    FLOOR = "_"
    BRIDGE = "="


class ObjectKind(StrEnum):
    NPC = "npc"
    CHEST = "chest"
    ENCOUNTER = "encounter"
    PORTAL = "portal"


class DecorationKind(StrEnum):
    TREE = "tree"
    ROOF = "roof"
    PILLAR = "pillar"


@dataclass(frozen=True, slots=True)
class MapPosition:
    map_id: str
    x: float
    y: float

    def __post_init__(self) -> None:
        require_text(self.map_id)
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            or value < 0
            for value in (self.x, self.y)
        ):
            raise DomainError("Position non finie ou négative.")


@dataclass(frozen=True, slots=True)
class MapObject:
    id: str
    name: str
    kind: ObjectKind
    column: int
    row: int
    solid: bool = True
    message: str = ""
    destination: MapPosition | None = None
    items: tuple[ItemQuantity, ...] = ()
    gold: int = 0
    enemies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        require_integer(self.column)
        require_integer(self.row)
        require_integer(self.gold)
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "enemies", tuple(self.enemies))
        if not isinstance(self.kind, ObjectKind):
            raise DomainError("Type d'interaction inconnu.")
        if (self.kind == ObjectKind.PORTAL) != (self.destination is not None):
            raise DomainError("Seul un passage déclare une destination.")
        if self.kind == ObjectKind.ENCOUNTER and not self.enemies:
            raise DomainError("Rencontre sans ennemi.")
        if self.kind != ObjectKind.ENCOUNTER and self.enemies:
            raise DomainError("Ennemis hors rencontre.")
        if self.kind != ObjectKind.CHEST and (self.items or self.gold):
            raise DomainError("Récompense hors coffre.")
        if self.kind == ObjectKind.PORTAL and self.solid:
            raise DomainError("Un passage ne peut pas être solide.")
        if self.kind == ObjectKind.NPC and not self.message.strip():
            raise DomainError("PNJ sans texte.")

    @property
    def center(self) -> tuple[float, float]:
        return (self.column + 0.5) * TILE_SIZE, (self.row + 0.5) * TILE_SIZE


@dataclass(frozen=True, slots=True)
class Decoration:
    column: int
    row: int
    kind: DecorationKind
    foreground: bool = True

    def __post_init__(self) -> None:
        require_integer(self.column)
        require_integer(self.row)
        if not isinstance(self.kind, DecorationKind):
            raise DomainError("Décoration inconnue.")


@dataclass(frozen=True, slots=True)
class MapDefinition:
    id: str
    name: str
    ground: tuple[tuple[Tile, ...], ...]
    blocked: frozenset[tuple[int, int]]
    objects: tuple[MapObject, ...] = ()
    decorations: tuple[Decoration, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        object.__setattr__(self, "ground", tuple(tuple(row) for row in self.ground))
        object.__setattr__(self, "blocked", frozenset(self.blocked))
        object.__setattr__(self, "objects", tuple(self.objects))
        object.__setattr__(self, "decorations", tuple(self.decorations))
        if not self.ground or not self.ground[0]:
            raise DomainError("Carte vide.")
        if any(
            len(row) != self.columns or any(not isinstance(tile, Tile) for tile in row)
            for row in self.ground
        ):
            raise DomainError("Grille de tuiles invalide.")
        if any(not self.contains_cell(x, y) for x, y in self.blocked):
            raise DomainError("Collision hors carte.")
        if len({entry.id for entry in self.objects}) != len(self.objects):
            raise DomainError("Interaction dupliquée.")
        cells: set[tuple[int, int]] = set()
        for entry in self.objects:
            cell = entry.column, entry.row
            if not self.contains_cell(*cell) or cell in self.blocked or cell in cells:
                raise DomainError("Interaction hors sol accessible ou superposée.")
            cells.add(cell)
        if any(not self.contains_cell(entry.column, entry.row) for entry in self.decorations):
            raise DomainError("Décoration hors carte.")

    @property
    def columns(self) -> int:
        return len(self.ground[0])

    @property
    def rows(self) -> int:
        return len(self.ground)

    @property
    def pixel_size(self) -> tuple[int, int]:
        return self.columns * TILE_SIZE, self.rows * TILE_SIZE

    def contains_cell(self, column: int, row: int) -> bool:
        return (
            type(column) is int
            and type(row) is int
            and 0 <= column < self.columns
            and 0 <= row < self.rows
        )


class WorldEventKind(StrEnum):
    MAP_ENTERED = "map_entered"
    NPC_SPOKEN = "npc_spoken"
    FLAG_SET = "flag_set"
    CHEST_OPENED = "chest_opened"
    ENCOUNTER_CLEARED = "encounter_cleared"


@dataclass(frozen=True, slots=True)
class WorldEvent:
    kind: WorldEventKind
    subject_id: str


class WorldState:
    def __init__(
        self,
        opened_chests: frozenset[str] = frozenset(),
        cleared_encounters: frozenset[str] = frozenset(),
        *,
        visited_maps: frozenset[str] = frozenset(),
        talked_to: frozenset[str] = frozenset(),
        flags: frozenset[str] = frozenset(),
    ) -> None:
        self._opened = frozenset(opened_chests)
        self._cleared = frozenset(cleared_encounters)
        self._visited = frozenset(visited_maps)
        self._talked = frozenset(talked_to)
        self._flags = frozenset(flags)
        for identity in (
            *self._opened,
            *self._cleared,
            *self._visited,
            *self._talked,
            *self._flags,
        ):
            require_text(identity)
        self._events: tuple[WorldEvent, ...] = ()

    @property
    def opened_chests(self) -> frozenset[str]:
        return self._opened

    @property
    def cleared_encounters(self) -> frozenset[str]:
        return self._cleared

    @property
    def visited_maps(self) -> frozenset[str]:
        return self._visited

    @property
    def talked_to(self) -> frozenset[str]:
        return self._talked

    @property
    def flags(self) -> frozenset[str]:
        return self._flags

    @property
    def events(self) -> tuple[WorldEvent, ...]:
        return self._events

    def record(self, kind: WorldEventKind, identity: str) -> None:
        require_text(identity)
        if kind == WorldEventKind.CHEST_OPENED:
            if identity in self._opened:
                raise DomainError("Coffre déjà ouvert.")
            self._opened = self._opened | {identity}
        elif kind == WorldEventKind.ENCOUNTER_CLEARED:
            if identity in self._cleared:
                raise DomainError("Rencontre déjà résolue.")
            self._cleared = self._cleared | {identity}
        elif kind == WorldEventKind.MAP_ENTERED:
            self._visited = self._visited | {identity}
        elif kind == WorldEventKind.NPC_SPOKEN:
            self._talked = self._talked | {identity}
        elif kind == WorldEventKind.FLAG_SET:
            if identity in self._flags:
                return
            self._flags = self._flags | {identity}
        else:
            raise DomainError("Événement de monde inconnu.")
        self._events += (WorldEvent(kind, identity),)


class World:
    SPEED = 96.0
    FOOT_RADIUS = 7.0
    INTERACTION_RANGE = 48.0

    def __init__(
        self,
        maps: tuple[MapDefinition, ...],
        position: MapPosition,
        state: WorldState | None = None,
    ) -> None:
        self._maps = {entry.id: entry for entry in maps}
        if len(self._maps) != len(maps):
            raise DomainError("Identifiant de carte dupliqué.")
        self._state = state if state is not None else WorldState()
        all_objects = [entry for area in maps for entry in area.objects]
        if len({entry.id for entry in all_objects}) != len(all_objects):
            raise DomainError("Identifiant d'interaction global dupliqué.")
        for ids, kind in (
            (self.state.opened_chests, ObjectKind.CHEST),
            (self.state.cleared_encounters, ObjectKind.ENCOUNTER),
        ):
            if not ids <= {entry.id for entry in all_objects if entry.kind == kind}:
                raise DomainError("État du monde incompatible avec le contenu.")
        if not self.walkable(position):
            raise DomainError("Point d'apparition inaccessible.")
        for entry in all_objects:
            if entry.destination is not None and not self.walkable(entry.destination):
                raise DomainError(f"Passage {entry.id} : destination inaccessible.")
        if not self.state.visited_maps <= set(self._maps) or not self.state.talked_to <= {
            entry.id for entry in all_objects if entry.kind == ObjectKind.NPC
        }:
            raise DomainError("Visites ou PNJ inconnus dans l'état du monde.")
        self._position = position
        self._origin = position
        self.state.record(WorldEventKind.MAP_ENTERED, position.map_id)

    @property
    def state(self) -> WorldState:
        return self._state

    @property
    def origin(self) -> MapPosition:
        return self._origin

    def set_origin(self, position: MapPosition) -> None:
        if not self.walkable(position):
            raise DomainError("Point de reprise inaccessible.")
        self._origin = position

    @property
    def position(self) -> MapPosition:
        return self._position

    @property
    def maps(self) -> tuple[MapDefinition, ...]:
        return tuple(self._maps.values())

    @property
    def current_map(self) -> MapDefinition:
        return self._maps[self._position.map_id]

    def visible_objects(self, area: MapDefinition | None = None) -> tuple[MapObject, ...]:
        area = area if area is not None else self.current_map
        return tuple(
            entry for entry in area.objects if entry.id not in self.state.cleared_encounters
        )

    def walkable(self, position: MapPosition) -> bool:
        area = self._maps.get(position.map_id)
        if area is None:
            return False
        radius = self.FOOT_RADIUS
        for x in (position.x - radius, position.x + radius):
            for y in (position.y - radius, position.y + radius):
                cell = int(x // TILE_SIZE), int(y // TILE_SIZE)
                if not area.contains_cell(*cell) or cell in area.blocked:
                    return False
                if any(
                    entry.solid and (entry.column, entry.row) == cell
                    for entry in self.visible_objects(area)
                ):
                    return False
        return True

    def move(self, dx: float, dy: float, elapsed: float) -> MapPosition:
        if any(not isfinite(value) for value in (dx, dy, elapsed)) or elapsed < 0:
            raise DomainError("Mouvement non fini ou temps négatif.")
        length = hypot(dx, dy)
        if not length or not elapsed:
            return self.position
        distance = self.SPEED * elapsed
        steps = max(1, ceil(distance / (TILE_SIZE / 4)))
        vx, vy = dx / length * distance / steps, dy / length * distance / steps
        x, y = self.position.x, self.position.y
        for _ in range(steps):
            if x + vx >= 0 and self.walkable(MapPosition(self.position.map_id, x + vx, y)):
                x += vx
            if y + vy >= 0 and self.walkable(MapPosition(self.position.map_id, x, y + vy)):
                y += vy
        self._position = MapPosition(self.position.map_id, x, y)
        return self.position

    def nearby(self) -> MapObject | None:
        candidates = sorted(
            self.visible_objects(),
            key=lambda entry: (
                hypot(entry.center[0] - self.position.x, entry.center[1] - self.position.y),
                entry.id,
            ),
        )
        if (
            candidates
            and hypot(
                candidates[0].center[0] - self.position.x, candidates[0].center[1] - self.position.y
            )
            <= self.INTERACTION_RANGE
        ):
            return candidates[0]
        return None

    def travel(self, portal: MapObject) -> None:
        if self.nearby() != portal or portal.destination is None:
            raise DomainError("Passage hors de portée.")
        if not self.walkable(portal.destination):
            raise DomainError("Destination inaccessible.")
        self._position = portal.destination
        self.state.record(WorldEventKind.MAP_ENTERED, self.position.map_id)

    def return_to_origin(self) -> None:
        self._position = self._origin
        self.state.record(WorldEventKind.MAP_ENTERED, self.position.map_id)
