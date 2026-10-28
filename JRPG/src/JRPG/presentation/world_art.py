"""Peintures recalées sur les coordonnées du monde, chargées une seule fois."""

from dataclasses import dataclass
from importlib.resources import files
from io import BytesIO
from itertools import pairwise
from math import isfinite

import pygame


@dataclass(frozen=True, slots=True)
class Registration:
    columns: tuple[tuple[float, float], ...] = ((0, 0), (1, 1))
    rows: tuple[tuple[float, float], ...] = ((0, 0), (1, 1))

    def __post_init__(self) -> None:
        for axis in (self.columns, self.rows):
            if any(not isfinite(value) for point in axis for value in point):
                raise ValueError("Les coordonnées de recalage doivent être finies.")
            if len(axis) < 2 or axis[0] != (0, 0) or axis[-1] != (1, 1):
                raise ValueError("Un recalage doit couvrir l'image entière.")
            if any(a[0] >= b[0] or a[1] >= b[1] for a, b in pairwise(axis)):
                raise ValueError("Un recalage doit rester strictement croissant.")

    def apply(self, image: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        if min(size) <= 0:
            raise ValueError("Dimensions du décor invalides.")
        result = pygame.Surface(size)
        for left, right in pairwise(self.columns):
            for top, bottom in pairwise(self.rows):
                source = pygame.Rect(
                    round(left[0] * image.width),
                    round(top[0] * image.height),
                    round(right[0] * image.width) - round(left[0] * image.width),
                    round(bottom[0] * image.height) - round(top[0] * image.height),
                )
                target = pygame.Rect(
                    round(left[1] * size[0]),
                    round(top[1] * size[1]),
                    round(right[1] * size[0]) - round(left[1] * size[0]),
                    round(bottom[1] * size[1]) - round(top[1] * size[1]),
                )
                if source.width and source.height and target.width and target.height:
                    result.blit(
                        pygame.transform.smoothscale(image.subsurface(source), target.size), target
                    )
        return result


REGISTRATIONS = {
    "village": Registration(
        ((0, 0), (0.105, 0.125), (0.337, 0.34375), (0.625, 0.625), (0.84, 0.8125), (1, 1)),
        (
            (0, 0),
            (0.32, 7 / 22),
            (0.41, 10 / 22),
            (0.50, 12 / 22),
            (0.565, 14 / 22),
            (0.825, 19 / 22),
            (1, 1),
        ),
    ),
    "forest": Registration(
        ((0, 0), (0.415, 19 / 40), (0.59, 21 / 40), (1, 1)),
        ((0, 0), (0.405, 10 / 24), (0.43, 11 / 24), (0.52, 13 / 24), (1, 1)),
    ),
    "ruins": Registration(
        ((0, 0), (0.18, 8 / 32), (0.446, 14 / 32), (0.55, 16 / 32), (0.818, 24 / 32), (1, 1)),
        ((0, 0), (0.14, 5 / 22), (0.214, 6 / 22), (0.69, 15 / 22), (0.765, 16 / 22), (1, 1)),
    ),
}


class WorldArt:
    def __init__(self) -> None:
        self._paintings: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}

    def painting(self, identity: str, size: tuple[int, int]) -> pygame.Surface | None:
        if identity not in REGISTRATIONS:
            return None
        key = identity, size
        if key not in self._paintings:
            data = (
                files("JRPG")
                .joinpath("infrastructure", "content", "art", "maps", f"{identity}-v1.png")
                .read_bytes()
            )
            source = pygame.image.load(BytesIO(data))
            self._paintings[key] = REGISTRATIONS[identity].apply(source, size)
        return self._paintings[key]

    def draw(
        self,
        surface: pygame.Surface,
        identity: str,
        size: tuple[int, int],
        camera: tuple[float, float],
    ) -> bool:
        painting = self.painting(identity, size)
        if painting is None:
            return False
        # Hors des limites : prolonger la texture de bord, même sur écran très large.
        x, y = -round(camera[0]), -round(camera[1])
        for left, right, sx, sw in (
            (0, max(0, x), 0, 1),
            (max(0, x), min(surface.width, x + size[0]), 0, size[0]),
            (min(surface.width, x + size[0]), surface.width, size[0] - 1, 1),
        ):
            for top, bottom, sy, sh in (
                (0, max(0, y), 0, 1),
                (max(0, y), min(surface.height, y + size[1]), 0, size[1]),
                (min(surface.height, y + size[1]), surface.height, size[1] - 1, 1),
            ):
                if right > left and bottom > top and (sw == 1 or sh == 1):
                    source = painting.subsurface((sx, sy, sw, sh))
                    surface.blit(
                        pygame.transform.scale(source, (right - left, bottom - top)), (left, top)
                    )
        surface.blit(painting, (x, y))
        return True
