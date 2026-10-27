"""Adaptateur d'événements clavier/souris ; le contrôleur reste indépendant de SDL."""

from collections.abc import Callable

import pygame

from JRPG.application.battle_session import SettlementResult
from JRPG.presentation.battle_controller import BattleController, MenuMode
from JRPG.presentation.battle_renderer import BattleRenderer


class BattleScene:
    def __init__(
        self,
        controller_factory: Callable[[], BattleController],
        on_exit: Callable[[SettlementResult], None] | None = None,
    ) -> None:
        self._factory = controller_factory
        self._on_exit = on_exit
        self.controller = controller_factory()
        self.renderer = BattleRenderer(continuation=on_exit is not None)
        self._log_offset = 0
        self._last_log = self.controller.log

    def handle_event(
        self, event: pygame.event.Event, position: tuple[int, int] | None = None
    ) -> None:
        if event.type == pygame.KEYDOWN:
            if (
                self._on_exit is not None
                and self.controller.settlement is not None
                and event.key in {pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER}
            ):
                self._on_exit(self.controller.settlement)
            elif event.key == pygame.K_r and self.controller.settlement is not None:
                if self._on_exit is None:
                    self._restart()
            elif event.key in {pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER}:
                self.controller.confirm()
            elif event.key in {pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB}:
                step = (
                    2
                    if event.key == pygame.K_DOWN and self.controller.mode == MenuMode.ACTION
                    else 1
                )
                self.controller.move(step)
            elif event.key in {pygame.K_UP, pygame.K_LEFT}:
                step = (
                    -2
                    if event.key == pygame.K_UP and self.controller.mode == MenuMode.ACTION
                    else -1
                )
                self.controller.move(step)
            elif event.key == pygame.K_BACKSPACE:
                self.controller.back()
            elif event.key in {pygame.K_PAGEUP, pygame.K_PAGEDOWN}:
                self._log_offset = max(
                    0,
                    min(
                        max(0, len(self.controller.log) - 4),
                        self._log_offset + (3 if event.key == pygame.K_PAGEUP else -3),
                    ),
                )
            elif self.controller.mode == MenuMode.ACTION:
                keys = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6)
                keypad = (
                    pygame.K_KP1,
                    pygame.K_KP2,
                    pygame.K_KP3,
                    pygame.K_KP4,
                    pygame.K_KP5,
                    pygame.K_KP6,
                )
                azerty = {"&": 0, "é": 1, '"': 2, "'": 3, "(": 4, "-": 5}
                if event.key in keys:
                    self.controller.select(keys.index(event.key))
                elif event.key in keypad:
                    self.controller.select(keypad.index(event.key))
                elif getattr(event, "unicode", "") in azerty:
                    self.controller.select(azerty[event.unicode])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and position is not None:
            for hit in reversed(self.renderer.hits):
                if hit.rect.collidepoint(position):
                    if hit.kind == "continue":
                        if self._on_exit is not None and self.controller.settlement is not None:
                            self._on_exit(self.controller.settlement)
                    elif hit.kind == "restart":
                        self._restart()
                    elif hit.kind == "menu":
                        self.controller.select(hit.index)
                    else:
                        self.controller.click_target(hit.identity)
                    break

    def _restart(self) -> None:
        self.controller = self._factory()
        self.renderer.hits = ()
        self._log_offset = 0
        self._last_log = self.controller.log

    def update(self, elapsed: float) -> None:
        self.controller.update(elapsed)
        self.renderer.update(elapsed)
        if self._on_exit is not None and self.controller.settlement is not None:
            self.controller.message = "Appuyez sur Entrée pour revenir à la carte."
        if self.controller.log != self._last_log:
            self._log_offset = 0
            self._last_log = self.controller.log

    def draw_background(self, surface: pygame.Surface) -> None:
        self.renderer.background(surface)

    def draw_foreground(self, surface: pygame.Surface) -> None:
        self.renderer.draw(surface, self.controller, self._log_offset)
