"""Sprites historiques embarqués ; aucune dépendance d'exécution au projet poo."""

from dataclasses import dataclass
from importlib.resources import files
from io import BytesIO

import pygame


@dataclass(frozen=True, slots=True)
class AtlasSpec:
    cell: tuple[int, int]
    count: int = 1
    anchor: tuple[int, int] | None = None
    folder: str = "legacy"


SHEETS = {
    "wisp": AtlasSpec((256, 192), 12, (128, 184), "creatures"),
    "briar": AtlasSpec((256, 192), 12, (128, 184), "creatures"),
    "raven": AtlasSpec((256, 192), 12, (128, 184), "creatures"),
    "wolf": AtlasSpec((224, 256), 4),
    "flan": AtlasSpec((224, 256), 4),
    "boss": AtlasSpec((768, 512), 4, (384, 502)),
    "wolf_claw": AtlasSpec((384, 256), 8, (192, 248)),
    "slime_jump": AtlasSpec((256, 256), 8, (128, 248)),
    "sentinel_strike": AtlasSpec((768, 512), 8, (384, 502)),
    "mira": AtlasSpec((256, 320), 4),
    "merchant": AtlasSpec((256, 320), 4),
    "traveler": AtlasSpec((256, 320), 4),
    "tree": AtlasSpec((128, 192)),
    "pillar": AtlasSpec((96, 128)),
    "house": AtlasSpec((384, 288)),
    "fire": AtlasSpec((96, 128)),
    "altar": AtlasSpec((96, 128)),
    "stone": AtlasSpec((96, 128)),
    "sign": AtlasSpec((96, 128)),
    "crate": AtlasSpec((96, 128)),
}
ENEMY_SHEETS = {
    "wisp": ("wisp", "wisp"),
    "briar": ("briar", "briar"),
    "raven": ("raven", "raven"),
    "wolf": ("wolf", "wolf_claw"),
    "slime": ("flan", "slime_jump"),
    "boss": ("boss", "sentinel_strike"),
}
NPC_SHEETS = {
    "village_herbalist": "traveler",
    "mira_village": "mira",
    "village_guard": "merchant",
    "forest_traveler": "traveler",
    "ruins_scholar": "merchant",
}


def enemy_kind(identity: str) -> str | None:
    """Les instances du moteur portent l'identifiant de définition puis leur numéro."""
    kind = identity.rsplit("-", 1)[0]
    return kind if kind in ENEMY_SHEETS else None


class PaintedSprites:
    def __init__(self) -> None:
        self._atlases: dict[str, pygame.Surface] = {}
        self._frames: dict[tuple[str, int, int, bool], pygame.Surface] = {}

    def draw(
        self,
        surface: pygame.Surface,
        name: str,
        feet: tuple[int, int],
        frame: int = 0,
        height: int = 64,
        flip: bool = False,
    ) -> None:
        specification = SHEETS[name]
        if height <= 0 or not 0 <= frame < specification.count:
            raise ValueError("Pose ou hauteur du sprite invalide.")
        key = name, frame, height, flip
        if key not in self._frames:
            if name not in self._atlases:
                data = (
                    files("JRPG")
                    .joinpath(
                        "infrastructure", "content", "art", specification.folder, f"{name}.png"
                    )
                    .read_bytes()
                )
                atlas = pygame.image.load(BytesIO(data))
                width, cell_height = specification.cell
                if atlas.get_size() != (width * specification.count, cell_height):
                    raise ValueError(f"Dimensions incorrectes pour l'atlas {name}.")
                self._atlases[name] = atlas
            width, cell_height = specification.cell
            image = self._atlases[name].subsurface((frame * width, 0, width, cell_height))
            scaled = pygame.transform.smoothscale(
                image, (round(width * height / cell_height), height)
            )
            self._frames[key] = pygame.transform.flip(scaled, True, False) if flip else scaled
        sprite = self._frames[key]
        ax, ay = specification.anchor or (
            specification.cell[0] // 2,
            round(specification.cell[1] * 0.95),
        )
        if flip:
            ax = specification.cell[0] - ax
        scale = height / specification.cell[1]
        surface.blit(sprite, (feet[0] - round(ax * scale), feet[1] - round(ay * scale)))
