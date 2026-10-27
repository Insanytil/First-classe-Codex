"""Règles d'exploration sans SDL : corps, grille, liens et état du monde."""

from collections.abc import Callable
from dataclasses import replace
from math import hypot

import pytest

from JRPG.domain.errors import DomainError
from JRPG.domain.world import (
    Decoration,
    DecorationKind,
    MapDefinition,
    MapObject,
    MapPosition,
    ObjectKind,
    Tile,
    World,
    WorldEventKind,
    WorldState,
)
from JRPG.presentation.exploration_controller import Camera


def area(
    identity: str = "field",
    objects: tuple[MapObject, ...] = (),
    blocked: frozenset[tuple[int, int]] = frozenset(),
) -> MapDefinition:
    return MapDefinition(
        identity, identity.title(), tuple((Tile.GRASS,) * 20 for _ in range(20)), blocked, objects
    )


def position(x: float = 176, y: float = 176, identity: str = "field") -> MapPosition:
    return MapPosition(identity, x, y)


def test_movement_is_time_based_and_diagonal_speed_is_normalized() -> None:
    first, second = World((area(),), position()), World((area(),), position())
    first.move(1, 0, 0.5)
    second.move(1, 1, 0.5)
    assert first.position.x == 224
    assert hypot(second.position.x - 176, second.position.y - 176) == pytest.approx(48)
    before = first.position
    assert first.move(0, 0, 100) == before
    assert first.move(1, 0, 0) == before


def test_substeps_prevent_tunneling_and_slide_along_walls() -> None:
    wall = frozenset((8, row) for row in range(20))
    world = World((area(blocked=wall),), position())
    world.move(1, 0, 5)
    assert 240 <= world.position.x <= 256 - World.FOOT_RADIUS
    before = world.position
    world.move(1, 1, 1)
    assert world.position.x <= 256 - World.FOOT_RADIUS
    assert world.position.y > before.y
    world.move(-1, -1, 10)
    assert world.position.x >= World.FOOT_RADIUS and world.position.y >= World.FOOT_RADIUS


def test_solid_objects_collide_and_cleared_encounters_stop_blocking() -> None:
    enemy = MapObject("wolves", "Loups", ObjectKind.ENCOUNTER, 7, 5, enemies=("wolf",))
    world = World((area(objects=(enemy,)),), position())
    world.move(1, 0, 2)
    assert world.position.x < 7 * 32
    world.state.record(WorldEventKind.ENCOUNTER_CLEARED, enemy.id)
    world.move(1, 0, 1)
    assert world.position.x > 8 * 32
    assert world.visible_objects() == ()


@pytest.mark.parametrize("dx,dy,elapsed", [(float("nan"), 0, 1), (1, float("inf"), 1), (1, 0, -1)])
def test_invalid_movement_preserves_position(dx: float, dy: float, elapsed: float) -> None:
    world = World((area(),), position())
    before = world.position
    with pytest.raises(DomainError):
        world.move(dx, dy, elapsed)
    assert world.position == before


def test_portals_validate_proximity_and_destination_then_keep_same_state() -> None:
    portal = MapObject(
        "gate", "Passage", ObjectKind.PORTAL, 6, 5, False, destination=position(identity="other")
    )
    world = World((area(objects=(portal,)), area("other")), position())
    state = world.state
    world.travel(portal)
    assert world.position.map_id == "other" and world.state is state
    assert world.state.visited_maps == frozenset({"field", "other"})
    with pytest.raises(DomainError):
        world.travel(portal)
    world.return_to_origin()
    assert world.position == position()
    with pytest.raises(DomainError):
        World(
            (area(objects=(replace(portal, destination=position(identity="missing")),)),),
            position(),
        )


def test_opened_chest_state_can_be_reused_when_world_is_reconstructed() -> None:
    chest = MapObject("chest", "Coffre", ObjectKind.CHEST, 7, 5)
    state = WorldState()
    world = World((area(objects=(chest,)),), position(), state)
    state.record(WorldEventKind.CHEST_OPENED, chest.id)
    restored = World(world.maps, position(), state)
    assert restored.state.opened_chests == frozenset({chest.id})
    with pytest.raises(DomainError):
        state.record(WorldEventKind.CHEST_OPENED, chest.id)
    with pytest.raises(DomainError):
        World((area(),), position(), state)


def test_nearest_interaction_and_global_ids_are_deterministic() -> None:
    first = MapObject("a", "Éline", ObjectKind.NPC, 6, 5, message="Bonjour.")
    second = replace(first, id="b", column=4)
    world = World((area(objects=(second, first)),), position())
    assert world.nearby() == first
    world.move(0, 1, 3)
    assert world.nearby() is None
    with pytest.raises(DomainError):
        World((area(objects=(first,)), area("other", objects=(first,))), position())


@pytest.mark.parametrize(
    "invalid",
    [
        lambda: MapPosition("field", -1, 0),
        lambda: MapPosition("field", float("nan"), 0),
        lambda: replace(area(), ground=()),
        lambda: replace(area(), ground=((Tile.GRASS,), (Tile.GRASS, Tile.GRASS))),
        lambda: replace(area(), blocked=frozenset({(99, 0)})),
        lambda: MapObject("npc", "PNJ", ObjectKind.NPC, 0, 0),
        lambda: MapObject("enemy", "Ennemi", ObjectKind.ENCOUNTER, 0, 0),
        lambda: MapObject("portal", "Passage", ObjectKind.PORTAL, 0, 0),
        lambda: Decoration(0, -1, DecorationKind.TREE),
    ],
)
def test_invalid_definitions_are_rejected(invalid: Callable[[], object]) -> None:
    with pytest.raises(DomainError):
        invalid()


def test_camera_clamps_to_map_bounds_and_centers_small_maps() -> None:
    assert Camera.follow(position(16, 16), (1024, 768), (640, 360)) == Camera(0, 0)
    assert Camera.follow(position(1000, 740), (1024, 768), (640, 360)) == Camera(384, 408)
    assert Camera.follow(position(16, 16), (320, 240), (640, 360)) == Camera(-160, -60)
    assert Camera(32, 64).project(48, 80) == (16, 16)
