"""Boucle SDL et cadrage séparé du décor et de l’interface."""

from dataclasses import dataclass
from math import ceil
from typing import Protocol

import pygame


@dataclass(frozen=True, slots=True)
class WindowSettings:
    """Configuration de présentation injectée, sans état global mutable."""

    width: int = 640
    height: int = 360
    fps: int = 60
    title: str = "JRPG — Exploration"

    def __post_init__(self) -> None:
        if min(self.width, self.height, self.fps) <= 0:
            raise ValueError("Dimensions et fréquence doivent être strictement positives.")

    def initial_size(self, desktop_size: tuple[int, int]) -> tuple[int, int]:
        """Occuper 90 % du bureau en laissant de la place aux bordures système."""
        available = tuple(max(1, int(value * 0.9)) for value in desktop_size)
        ratio = min(available[0] / self.width, available[1] / self.height)
        return max(1, int(self.width * ratio)), max(1, int(self.height * ratio))

    def viewport(
        self, window_size: tuple[int, int], source_size: tuple[int, int] | None = None
    ) -> tuple[int, int, int, int]:
        """Couvrir toute la fenêtre sans déformation, avec recadrage centré."""
        width, height = window_size
        source_width, source_height = (
            source_size if source_size is not None else (self.width, self.height)
        )
        ratio = max(width / source_width, height / source_height)
        target_width = max(1, ceil(source_width * ratio))
        target_height = max(1, ceil(source_height * ratio))
        return (
            (width - target_width) // 2,
            (height - target_height) // 2,
            target_width,
            target_height,
        )

    def background_size(self, window_size: tuple[int, int]) -> tuple[int, int]:
        """Champ de caméra au ratio de la fenêtre, avec densité logique constante."""
        width, height = window_size
        width, height = max(1, width), max(1, height)
        ratio = min(max(self.width / width, self.height / height), 2048 / max(width, height))
        return max(1, ceil(width * ratio)), max(1, ceil(height * ratio))

    def ui_viewport(self, window_size: tuple[int, int]) -> tuple[int, int, int, int]:
        """Interface entièrement visible ; les marges montrent le décor plein écran."""
        width, height = window_size
        ratio = min(width / self.width, height / self.height)
        target_width = max(1, int(self.width * ratio))
        target_height = max(1, int(self.height * ratio))
        return (
            (width - target_width) // 2,
            (height - target_height) // 2,
            target_width,
            target_height,
        )

    def logical_position(
        self, position: tuple[int, int], window_size: tuple[int, int]
    ) -> tuple[int, int] | None:
        x, y, width, height = self.ui_viewport(window_size)
        px, py = position
        if not x <= px < x + width or not y <= py < y + height:
            return None
        return int((px - x) * self.width / width), int((py - y) * self.height / height)


class Scene(Protocol):
    def handle_event(
        self, event: pygame.event.Event, position: tuple[int, int] | None = None
    ) -> None: ...
    def update(self, elapsed: float) -> None: ...
    def draw_background(self, surface: pygame.Surface) -> None: ...
    def draw_foreground(self, surface: pygame.Surface) -> None: ...


class PygameApplication:
    """Possède le cycle de vie SDL et injecte événements/temps dans une scène."""

    def __init__(self, settings: WindowSettings, scene: Scene | None = None) -> None:
        self._settings = settings
        self._scene = scene

    def run(self) -> None:
        settings = self._settings
        try:
            pygame.display.init()
            pygame.font.init()
            desktop_size = pygame.display.get_desktop_sizes()[0]
            screen = pygame.display.set_mode(settings.initial_size(desktop_size), pygame.RESIZABLE)
            pygame.display.set_caption(settings.title)
            canvas = pygame.Surface((settings.width, settings.height))
            overlay = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
            pause_font = pygame.font.Font(None, 26)
            clock = pygame.time.Clock()
            running, paused = True, False
            while running:
                elapsed = min(0.1, clock.tick(settings.fps) / 1000)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (
                        event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    ):
                        running = False
                    elif event.type == pygame.WINDOWFOCUSLOST:
                        paused = True
                        if self._scene is not None:
                            self._scene.handle_event(event)
                    elif event.type == pygame.WINDOWFOCUSGAINED:
                        paused = False
                    elif self._scene is not None and not paused:
                        position = (
                            settings.logical_position(event.pos, screen.get_size())
                            if hasattr(event, "pos")
                            else None
                        )
                        self._scene.handle_event(event, position)
                if not running:
                    break
                background_size = settings.background_size(screen.get_size())
                if canvas.get_size() != background_size:
                    canvas = pygame.Surface(background_size)
                if self._scene is None:
                    canvas.fill((18, 24, 38))
                else:
                    if not paused:
                        self._scene.update(elapsed)
                    self._scene.draw_background(canvas)
                viewport = pygame.Rect(settings.viewport(screen.get_size(), canvas.get_size()))
                screen.blit(pygame.transform.scale(canvas, viewport.size), viewport)
                if self._scene is not None:
                    self._scene.draw_foreground(overlay)
                    ui_viewport = pygame.Rect(settings.ui_viewport(screen.get_size()))
                    screen.blit(pygame.transform.scale(overlay, ui_viewport.size), ui_viewport)
                if paused:
                    notice = pause_font.render(
                        "En pause — revenez à la fenêtre pour continuer", True, (255, 231, 176)
                    )
                    rect = notice.get_rect(center=screen.get_rect().center)
                    pygame.draw.rect(screen, (14, 29, 39), rect.inflate(28, 22), border_radius=5)
                    screen.blit(notice, rect)
                pygame.display.flip()
        finally:
            pygame.quit()
