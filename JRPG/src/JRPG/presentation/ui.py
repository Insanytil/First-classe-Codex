"""Primitives partagées de présentation : textes, palette et panneaux."""

import pygame

Color = tuple[int, int, int]
INK: Color = (227, 231, 213)
MUTED: Color = (151, 175, 167)
GOLD: Color = (230, 192, 115)
JADE: Color = (110, 211, 175)


class UiPainter:
    def __init__(self) -> None:
        self._fonts: dict[int, pygame.font.Font] = {}

    def font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def text(
        self,
        surface: pygame.Surface,
        value: str,
        position: tuple[int, int],
        size: int = 14,
        color: Color = INK,
        width: int | None = None,
    ) -> None:
        font = self.font(size)
        if width is not None and font.size(value)[0] > width:
            while value and font.size(value + "…")[0] > width:
                value = value[:-1]
            value += "…"
        surface.blit(font.render(value, True, color), position)

    @staticmethod
    def panel(surface: pygame.Surface, rect: pygame.Rect, border: Color = (62, 91, 90)) -> None:
        pygame.draw.rect(surface, (15, 32, 43, 238), rect, border_radius=5)
        pygame.draw.rect(surface, border, rect, 1, border_radius=5)
