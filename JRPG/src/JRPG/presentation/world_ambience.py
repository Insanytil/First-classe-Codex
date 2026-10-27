"""Ambiance analytique bornée : eau, vent, fumée, lucioles et poussière."""

from math import isfinite, pi, sin

import pygame

from JRPG.domain.world import MapDefinition, Tile
from JRPG.presentation.exploration_controller import Camera
from JRPG.presentation.painted_sprites import PaintedSprites


class WorldAmbience:
    def __init__(self) -> None:
        self.time = 0.0
        self._water: dict[str, tuple[tuple[int, int], ...]] = {}
        self._overlay: pygame.Surface | None = None
        self._sprites = PaintedSprites()

    def update(self, elapsed: float) -> None:
        if not isfinite(elapsed) or elapsed < 0:
            raise ValueError("Temps d'ambiance invalide.")
        self.time = (self.time + elapsed) % 120

    def draw(self, surface: pygame.Surface, area: MapDefinition, camera: Camera) -> None:
        if self._overlay is None or self._overlay.get_size() != surface.get_size():
            self._overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay = self._overlay
        overlay.fill((0, 0, 0, 0))
        if area.id not in self._water:
            self._water[area.id] = tuple(
                (column, row)
                for row, line in enumerate(area.ground)
                for column, tile in enumerate(line)
                if tile == Tile.WATER
            )
        cells = self._water[area.id]
        for index in range(min(48, len(cells) * 2)):
            column, row = cells[index * 13 % len(cells)]
            phase = (self.time * 0.32 + index * 0.173) % 1
            x, y = camera.project(column * 32 + 7 + index * 7 % 15, row * 32 + 6 + phase * 19)
            alpha = round(sin(phase * pi) * 92)
            pygame.draw.arc(overlay, (173, 226, 216, alpha), (x - 4, y - 2, 9, 4), 0.1, 2.9, 1)
        width, height = area.pixel_size
        for index in range(24):
            speed = 4 if area.id == "ruins" else 8
            wx = (index * 173 + self.time * speed) % width
            wy = (index * 97 - self.time * 3 + sin(self.time + index) * 8) % height
            x, y = camera.project(wx, wy)
            pulse = 0.5 + 0.5 * sin(self.time * 1.7 + index)
            if area.id == "ruins":
                color = (120, 219, 219, round(40 + pulse * 100))
                pygame.draw.circle(overlay, color, (x, y), 1)
                pygame.draw.circle(overlay, (91, 190, 199, 12), (x, y), 5)
            else:
                pygame.draw.line(
                    overlay,
                    (214, 190, 119, round(40 + pulse * 80)),
                    (x, y),
                    (x + 3, y + round(sin(self.time * 2 + index) * 2)),
                    1,
                )
        if area.id == "village":
            for index in range(5):
                phase = (self.time * 0.22 + index / 5) % 1
                x, y = camera.project(7.5 * 32 + sin(phase * 5) * 8, 3 * 32 - phase * 52)
                pygame.draw.circle(
                    overlay, (193, 194, 181, round((1 - phase) * 35)), (x, y), round(3 + phase * 10)
                )
        if area.id == "ruins":
            for column, row in ((9, 5), (22, 5), (9, 15), (22, 15)):
                x, y = camera.project((column + 0.5) * 32, (row + 0.5) * 32)
                pulse = sin(self.time * 8 + column)
                pygame.draw.ellipse(
                    overlay, (239, 166, 69, round(25 + pulse * 8)), (x - 22, y - 29, 44, 37)
                )
                self._sprites.draw(surface, "fire", (x, y), height=34 + round(pulse))
        surface.blit(overlay, (0, 0))
