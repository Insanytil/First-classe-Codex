"""Vrais événements et surfaces SDL dummy ; aucun affichage desktop requis."""

from collections.abc import Iterator
from unittest.mock import patch

import pygame
import pytest

from JRPG.domain.combat.model import Outcome
from JRPG.infrastructure.training_encounter import create_training_encounter
from JRPG.presentation.battle_controller import BattleController, MenuMode
from JRPG.presentation.battle_scene import BattleScene
from JRPG.presentation.pygame_app import WindowSettings


@pytest.fixture
def scene() -> Iterator[BattleScene]:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield BattleScene(lambda: BattleController(create_training_encounter()))
    pygame.quit()


def draw(scene: BattleScene) -> pygame.Surface:
    surface = pygame.Surface((640, 360), pygame.SRCALPHA)
    scene.draw_foreground(surface)
    return surface


def test_keyboard_and_mouse_execute_a_targeted_attack(scene: BattleScene) -> None:
    draw(scene)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
    assert scene.controller.mode == MenuMode.TARGET
    draw(scene)
    target = next(hit for hit in scene.renderer.hits if hit.identity == "wolf-1")
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), target.rect.center)
    assert scene.controller.playback is not None
    before = scene.controller.encounter.battle.journal
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert scene.controller.encounter.battle.journal == before
    scene.update(0.3)
    draw(scene)


def test_arrow_navigation_tab_and_backspace(scene: BattleScene) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    assert scene.controller.selected == 2
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert scene.controller.selected == 1
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    assert scene.controller.selected == 1
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
    assert scene.controller.mode == MenuMode.ACTION


def test_rendering_is_read_only_and_background_has_no_black_corners(scene: BattleScene) -> None:
    battle = scene.controller.encounter.battle
    before = battle.combatants, battle.journal, battle.turn_id
    surface = pygame.Surface((640, 360))
    scene.draw_background(surface)
    for point in ((0, 0), (639, 0), (0, 359), (639, 359)):
        assert surface.get_at(point)[:3] != (0, 0, 0)
    with patch.object(battle, "execute", wraps=battle.execute) as execute:
        for _ in range(3):
            draw(scene)
        execute.assert_not_called()
    assert (battle.combatants, battle.journal, battle.turn_id) == before


def test_finished_battle_renders_rewards_and_restart_creates_fresh_game(scene: BattleScene) -> None:
    for _ in range(300):
        if scene.controller.accepting_input:
            scene.controller.select(0)
            scene.controller.confirm()
        scene.update(1)
        if scene.controller.settlement is not None:
            break
    assert scene.controller.settlement is not None
    assert scene.controller.settlement.outcome == Outcome.VICTORY
    draw(scene)
    original = scene.controller
    button = next(hit for hit in scene.renderer.hits if hit.kind == "restart")
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), button.rect.center)
    assert scene.controller is not original
    assert scene.controller.settlement is None
    assert scene.controller.encounter.battle.turn_id == 1


@pytest.mark.parametrize("window", [(1280, 720), (1280, 800), (2560, 1080), (360, 640)])
def test_click_coordinates_match_visible_ui_after_resize(window: tuple[int, int]) -> None:
    settings = WindowSettings()
    x, y, width, height = settings.ui_viewport(window)
    logical = (80, 283)
    physical = (
        x + int((logical[0] + 0.5) * width / 640),
        y + int((logical[1] + 0.5) * height / 360),
    )
    mapped = settings.logical_position(physical, window)
    assert mapped is not None
    assert abs(mapped[0] - logical[0]) <= 2 and abs(mapped[1] - logical[1]) <= 2
    assert x >= 0 and y >= 0 and x + width <= window[0] and y + height <= window[1]


def test_click_outside_ui_does_not_select_invisible_commands() -> None:
    assert WindowSettings().logical_position((0, 0), (360, 640)) is None


@pytest.mark.parametrize("key, unicode", [(pygame.K_KP1, ""), (pygame.K_UNKNOWN, "&")])
def test_numeric_keypad_and_azerty_shortcuts(scene: BattleScene, key: int, unicode: str) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode))
    assert scene.controller.mode == MenuMode.TARGET


def test_journal_scroll_changes_display_without_advancing_combat(scene: BattleScene) -> None:
    scene.controller.log = tuple(f"Événement {index}" for index in range(12))
    before = draw(scene)
    turn = scene.controller.encounter.battle.turn_id
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP))
    older = draw(scene)
    assert pygame.image.tobytes(before, "RGBA") != pygame.image.tobytes(older, "RGBA")
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN))
    latest = draw(scene)
    assert pygame.image.tobytes(before, "RGBA") == pygame.image.tobytes(latest, "RGBA")
    assert scene.controller.encounter.battle.turn_id == turn
