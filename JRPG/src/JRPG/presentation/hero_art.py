"""Atlas peints embarqués et cache graphique, exclusivement en présentation."""

from importlib.resources import files
from io import BytesIO

import pygame

from JRPG.presentation.attack_animation import contact_frame

HERO_IDS = frozenset({"ari", "lyra", "mira", "nox"})
CELL = (192, 128)
ANCHOR = (96, 120)


def action_frame(elapsed: float, impact: float, duration: float) -> int:
    """La cinquième pose (contact) commence exactement à l'impact métier."""
    return 16 + contact_frame(elapsed, impact, duration)


class HeroArt:
    """Charge une fois chaque atlas ; redimensionne une fois par taille utilisée.

    Aucun chargement ni accès SDL à l'import ou à la construction. Les identités
    étrangères au catalogue restent utilisables par les scènes de test/extensions.
    """

    def __init__(self) -> None:
        self._atlases: dict[str, pygame.Surface] = {}
        self._frames: dict[tuple[str, int, int], pygame.Surface] = {}

    def draw(
        self,
        surface: pygame.Surface,
        identity: str,
        feet: tuple[int, int],
        frame: int = 16,
        height: int = 60,
    ) -> bool:
        if identity not in HERO_IDS:
            return False
        if not 0 <= frame < 24 or height < 1:
            raise ValueError("Pose ou hauteur d'atlas invalide.")
        key = (identity, frame, height)
        if key not in self._frames:
            if identity not in self._atlases:
                data = (
                    files("JRPG")
                    .joinpath("infrastructure", "content", "art", f"{identity}-v1.png")
                    .read_bytes()
                )
                self._atlases[identity] = pygame.image.load(BytesIO(data))
            rect = pygame.Rect(frame % 4 * CELL[0], frame // 4 * CELL[1], *CELL)
            self._frames[key] = pygame.transform.smoothscale(
                self._atlases[identity].subsurface(rect),
                (round(CELL[0] * height / CELL[1]), height),
            )
        sprite = self._frames[key]
        surface.blit(
            sprite,
            (
                feet[0] - round(ANCHOR[0] * height / CELL[1]),
                feet[1] - round(ANCHOR[1] * height / CELL[1]),
            ),
        )
        return True


def walk_frame(facing: tuple[float, float], phase: float) -> int:
    x, y = facing
    row = (3 if x > 0 else 1) if abs(x) > abs(y) else (2 if y < 0 else 0)
    return row * 4 + int(max(0.0, phase) * 8) % 4
