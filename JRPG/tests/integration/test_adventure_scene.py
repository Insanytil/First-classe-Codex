"""Exploration réelle via événements SDL, caméra et retour de la scène de combat."""

from collections.abc import Iterator

import pygame
import pytest

from JRPG.domain.combat.model import Outcome
from JRPG.domain.world import MapPosition
from JRPG.infrastructure.world_content import create_exploration_session
from JRPG.presentation.adventure_scene import AdventureScene
from JRPG.presentation.exploration_controller import Camera
from JRPG.presentation.pygame_app import WindowSettings


@pytest.fixture(autouse=True)
def sdl() -> Iterator[None]:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.quit()


def key(scene: AdventureScene, value: int, pressed: bool = True) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN if pressed else pygame.KEYUP, key=value))


def forest_scene() -> AdventureScene:
    return AdventureScene(
        create_exploration_session(position=MapPosition("forest", 13.5 * 32, 11.5 * 32))
    )


def test_continuous_movement_retains_other_physical_key_and_stops_on_focus_loss() -> None:
    scene = AdventureScene(create_exploration_session())
    origin = scene.controller.session.world.position
    key(scene, pygame.K_d)
    key(scene, pygame.K_RIGHT)
    scene.update(0.2)
    first = scene.controller.session.world.position
    assert first.x > origin.x
    key(scene, pygame.K_d, False)
    scene.update(0.2)
    second = scene.controller.session.world.position
    assert second.x > first.x
    scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    scene.update(0.2)
    assert scene.controller.session.world.position == second
    key(scene, pygame.K_UP)
    key(scene, pygame.K_UP, False)
    scene.update(0.2)
    assert scene.controller.session.world.position == second


def test_dialogue_blocks_movement_and_closes_without_retriggering_interaction() -> None:
    scene = AdventureScene(
        create_exploration_session(position=MapPosition("village", 8.5 * 32, 8.5 * 32))
    )
    before = scene.controller.session.world.position
    key(scene, pygame.K_e)
    assert scene.controller.dialogue and scene.controller.speaker == "Éline"
    key(scene, pygame.K_d)
    scene.update(1)
    assert scene.controller.session.world.position == before
    scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    hit, _ = scene.renderer.dialogue_hits[-1]
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), hit.center)
    assert not scene.controller.dialogue
    scene.update(1)
    assert scene.controller.session.world.position == before


def test_exploration_battle_and_victory_return_keep_group_and_stop_held_keys() -> None:
    scene = forest_scene()
    session = scene.controller.session
    before = session.world.position
    original_party = session.party
    key(scene, pygame.K_d)
    key(scene, pygame.K_e)
    battle_scene = scene.battle
    assert battle_scene is not None
    for _ in range(300):
        if battle_scene.controller.accepting_input:
            battle_scene.controller.select(0)
            battle_scene.controller.confirm()
        scene.update(1)
        if battle_scene.controller.settlement is not None:
            break
    assert battle_scene.controller.settlement is not None
    assert battle_scene.controller.settlement.outcome == Outcome.VICTORY
    scene.draw_background(pygame.Surface((640, 360)))
    scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    assert any(hit.kind == "continue" for hit in battle_scene.renderer.hits)
    key(scene, pygame.K_r)
    assert scene.battle is battle_scene
    key(scene, pygame.K_RETURN)
    assert scene.battle is None and session.active_encounter is None
    assert session.party is original_party
    assert session.world.position == before
    assert "forest_wolves" in session.world.state.cleared_encounters
    assert session.wallet.gold == 30
    scene.update(1)
    assert session.world.position == before


def test_flee_returns_to_same_place_and_requires_new_interaction_to_retry() -> None:
    scene = forest_scene()
    origin = scene.controller.session.world.position
    key(scene, pygame.K_e)
    battle = scene.battle
    assert battle is not None
    for _ in range(100):
        if battle.controller.accepting_input:
            battle.controller.select(4)
        scene.update(1)
        if battle.controller.settlement is not None:
            break
    assert battle.controller.settlement is not None
    assert battle.controller.settlement.outcome == Outcome.FLED
    scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    hit = next(entry for entry in battle.renderer.hits if entry.kind == "continue")
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), hit.rect.center)
    assert scene.battle is None
    scene.update(1)
    assert scene.battle is None and scene.controller.session.world.position == origin
    key(scene, pygame.K_e)
    assert scene.battle is not None and scene.battle is not battle


@pytest.mark.parametrize("size", [(640, 360), (640, 400), (854, 360), (640, 1138)])
def test_rendering_at_different_aspect_ratios_keeps_player_visible_without_mutation(
    size: tuple[int, int],
) -> None:
    scene = AdventureScene(create_exploration_session())
    session = scene.controller.session
    before = session.world.position, session.world.state.events, session.inventory.stacks
    surface = pygame.Surface(size)
    scene.draw_background(surface)
    camera = Camera.follow(session.world.position, session.world.current_map.pixel_size, size)
    x, y = camera.project(session.world.position.x, session.world.position.y)
    assert 0 <= x < size[0] and 0 <= y < size[1]
    for point in ((0, 0), (size[0] - 1, 0), (0, size[1] - 1), (size[0] - 1, size[1] - 1)):
        assert surface.get_at(point)[:3] != (0, 0, 0)
    scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    assert (session.world.position, session.world.state.events, session.inventory.stacks) == before


@pytest.mark.parametrize("window", [(1280, 720), (1280, 800), (2560, 1080), (360, 640)])
def test_background_camera_has_window_aspect_and_ui_stays_inside(window: tuple[int, int]) -> None:
    settings = WindowSettings()
    width, height = settings.background_size(window)
    assert width >= 640 and height >= 360
    assert abs(width / height - window[0] / window[1]) < 0.005
    x, y, w, h = settings.ui_viewport(window)
    assert x >= 0 and y >= 0 and x + w <= window[0] and y + h <= window[1]


@pytest.mark.parametrize("window", [(1, 2000), (4000, 1), (0, 0)])
def test_extreme_resize_does_not_allocate_unbounded_background(window: tuple[int, int]) -> None:
    width, height = WindowSettings().background_size(window)
    assert 1 <= width <= 2048 and 1 <= height <= 2048
