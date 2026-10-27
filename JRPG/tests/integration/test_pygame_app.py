"""Tests SDL sans écran réel, avec boucle bornée par des événements."""

from unittest.mock import patch

import pygame
import pytest

from JRPG.bootstrap import main
from JRPG.presentation.pygame_app import PygameApplication, WindowSettings


@pytest.mark.parametrize("field", ["width", "height", "fps"])
def test_settings_reject_nonpositive_values(field: str) -> None:
    with pytest.raises(ValueError):
        WindowSettings(**{field: 0})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "event",
    [pygame.event.Event(pygame.QUIT), pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
)
def test_bootstrap_renders_then_closes(event: pygame.event.Event) -> None:
    # Une vraie frame est rendue avant la demande de fermeture.
    with (
        patch("pygame.display.get_desktop_sizes", return_value=[(1024, 768)]),
        patch("pygame.event.get", side_effect=[[], [event]]),
        patch("pygame.display.flip", wraps=pygame.display.flip) as flip,
        patch("pygame.display.set_mode", wraps=pygame.display.set_mode) as set_mode,
    ):
        main()
    flip.assert_called_once()
    set_mode.assert_called_once_with((921, 518), pygame.RESIZABLE)
    assert not pygame.display.get_init()
    assert not pygame.get_init()


def test_display_is_released_after_render_failure() -> None:
    with (
        patch("pygame.event.get", return_value=[]),
        patch("pygame.display.flip", side_effect=RuntimeError("render failed")),
        pytest.raises(RuntimeError, match="render failed"),
    ):
        PygameApplication(WindowSettings()).run()
    assert not pygame.display.get_init()


def test_display_is_released_after_initialization_failure() -> None:
    with (
        patch("pygame.display.set_mode", side_effect=pygame.error("display unavailable")),
        pytest.raises(pygame.error, match="display unavailable"),
    ):
        main()
    assert not pygame.display.get_init()


@pytest.mark.parametrize("desktop", [(800, 600), (1920, 1080), (3840, 2160)])
def test_initial_window_fits_desktop(desktop: tuple[int, int]) -> None:
    width, height = WindowSettings().initial_size(desktop)
    assert 0 < width <= desktop[0] * 0.9
    assert 0 < height <= desktop[1] * 0.9
    assert abs(width / height - 16 / 9) < 0.01


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        ((1920, 1080), (0, 0, 1920, 1080)),
        ((1536, 864), (0, 0, 1536, 864)),
        ((1000, 800), (-212, 0, 1423, 800)),
        ((1280, 800), (-72, 0, 1423, 800)),
        ((320, 240), (-54, 0, 427, 240)),
        ((360, 640), (-389, 0, 1138, 640)),
    ],
)
def test_viewport_preserves_aspect_ratio(
    window: tuple[int, int], expected: tuple[int, int, int, int]
) -> None:
    assert WindowSettings().viewport(window) == expected


def test_resize_uses_new_surface_size() -> None:
    def resized_events() -> list[pygame.event.Event]:
        pygame.display.set_mode((320, 240), pygame.RESIZABLE)
        return [pygame.event.Event(pygame.VIDEORESIZE, size=(320, 240), w=320, h=240)]

    with (
        patch("pygame.transform.scale", wraps=pygame.transform.scale) as scale,
        patch(
            "pygame.event.get",
            side_effect=lambda: (
                resized_events() if not scale.called else [pygame.event.Event(pygame.QUIT)]
            ),
        ),
    ):
        main()
    assert [call.args[1] for call in scale.call_args_list][-2:] == [(320, 240), (320, 180)]


@pytest.mark.parametrize("window", [(1000, 800), (2560, 1080), (360, 640), (1537, 865)])
def test_viewport_covers_every_window_edge(window: tuple[int, int]) -> None:
    x, y, width, height = WindowSettings().viewport(window)
    assert x <= 0 and y <= 0
    assert x + width >= window[0]
    assert y + height >= window[1]
    assert abs(width / height - 16 / 9) < 0.01


def test_focus_loss_pauses_simulation_and_ignores_commands_until_focus_returns() -> None:
    from unittest.mock import Mock

    scene = Mock()
    scene.draw_background.side_effect = lambda surface: surface.fill((30, 50, 60))
    scene.draw_foreground.side_effect = lambda surface: surface.fill((0, 0, 0, 0))
    with patch(
        "pygame.event.get",
        side_effect=[
            [
                pygame.event.Event(pygame.WINDOWFOCUSLOST),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1),
            ],
            [pygame.event.Event(pygame.WINDOWFOCUSGAINED)],
            [pygame.event.Event(pygame.QUIT)],
        ],
    ):
        PygameApplication(WindowSettings(), scene).run()
    scene.update.assert_called_once()
    scene.handle_event.assert_called_once()
    assert scene.handle_event.call_args.args[0].type == pygame.WINDOWFOCUSLOST
    assert scene.draw_background.call_count == 2
