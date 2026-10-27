"""Guides de composition imagegen issus des cartes réelles, sans changer le monde."""

import json
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    colors = {
        ".": (84, 114, 72),
        ":": (189, 164, 113),
        "~": (45, 128, 149),
        "#": (76, 81, 74),
        "_": (139, 145, 132),
        "=": (136, 94, 56),
    }
    folder = ROOT / "docs" / "art" / "layouts"
    folder.mkdir(parents=True, exist_ok=True)
    for identity in ("village", "forest", "ruins"):
        data = json.loads(
            (ROOT / "src/JRPG/infrastructure/content/maps" / f"{identity}.json").read_text(
                encoding="utf-8"
            )
        )
        ground = data["ground"]
        canvas = pygame.Surface((len(ground[0]) * 32, len(ground) * 32))
        for row, line in enumerate(ground):
            for column, tile in enumerate(line):
                pygame.draw.rect(canvas, colors[tile], (column * 32, row * 32, 32, 32))
        pygame.image.save(canvas, str(folder / f"{identity}-layout.png"))
        print(folder / f"{identity}-layout.png")


if __name__ == "__main__":
    main()
