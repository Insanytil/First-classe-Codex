"""Découpage déterministe des originaux imagegen avec Pygame déjà installé.

Les composantes opaques identifient les silhouettes, sans supposer que le
générateur respecte une grille. Aucun appel réseau ni installation.
"""

import hashlib
import json
from pathlib import Path
from statistics import median

import pygame

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "src" / "JRPG" / "infrastructure" / "content" / "art"
HEROES = ("ari", "lyra", "mira", "nox")


def main() -> None:
    entries: dict[str, object] = {}
    pygame.font.init()
    preview = pygame.Surface((1152, 624))
    preview.fill((20, 35, 42))
    font = pygame.font.Font(None, 30)
    for identity in HEROES:
        source = ART / "sources" / f"{identity}-v1.png"
        image = pygame.image.load(str(source))
        silhouettes = pygame.mask.from_surface(image, 127).connected_components(1500)
        masks = {tuple(mask.get_bounding_rects()[0]): mask for mask in silhouettes}
        components = sorted(
            (
                rect
                for rect in pygame.mask.from_surface(image, 127).get_bounding_rects()
                if rect.width * rect.height > 1500
            ),
            key=lambda rect: rect.y,
        )
        expected = 32 if identity == "nox" else 24
        if len(components) != expected:
            raise ValueError(f"{identity}: {len(components)} silhouettes, attendu {expected}")
        walks = components[:16]
        attacks = components[-8:]
        frames: list[pygame.Rect] = []
        for offset in range(0, 16, 4):
            frames.extend(sorted(walks[offset : offset + 4], key=lambda rect: rect.x))
        attack_columns = 8 if identity == "nox" else 4
        for offset in range(0, 8, attack_columns):
            frames.extend(sorted(attacks[offset : offset + attack_columns], key=lambda r: r.x))
        atlas = pygame.Surface((192 * 4, 128 * 6), pygame.SRCALPHA)
        scale = 96 / median(rect.height for rect in walks)
        for index, bounds in enumerate(frames):
            crop = bounds.inflate(4, 4).clip(image.get_rect())
            sprite = image.subsurface(crop).copy()
            isolated = masks[tuple(bounds)].to_surface(
                setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)
            )
            sprite.blit(isolated, (0, 0), crop, special_flags=pygame.BLEND_RGBA_MULT)
            sprite = pygame.transform.smoothscale(
                sprite, (round(crop.width * scale), round(crop.height * scale))
            )
            if identity in {"mira", "nox"} and 4 <= index < 8:
                sprite = pygame.transform.flip(sprite, True, False)
            if sprite.width > 184 or sprite.height > 120:
                raise ValueError(f"{identity}: pose {index} déborde du cadre normalisé")
            x, y = index % 4 * 192, index // 4 * 128
            atlas.blit(sprite, (x + (192 - sprite.width) // 2, y + 120 - sprite.height))
        target = ART / f"{identity}-v1.png"
        pygame.image.save(atlas, str(target))
        column = HEROES.index(identity)
        preview.blit(
            font.render(identity.capitalize(), True, (231, 211, 161)), (column * 288 + 115, 12)
        )
        for row, frame in enumerate((0, 16, 20)):
            sprite = atlas.subsurface((frame % 4 * 192, frame // 4 * 128, 192, 128))
            preview.blit(
                pygame.transform.smoothscale(sprite, (288, 192)), (column * 288, 40 + row * 192)
            )
        entries[identity] = {
            "file": target.name,
            "source": f"sources/{source.name}",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "source_rects": [list(rect) for rect in frames],
            "cell": [192, 128],
            "anchor": [96, 120],
            "walk": {
                "down": [0, 1, 2, 3],
                "left": [4, 5, 6, 7],
                "up": [8, 9, 10, 11],
                "right": [12, 13, 14, 15],
            },
            "action": list(range(16, 24)),
        }
    manifest = {
        "version": 1,
        "generator": "OpenAI imagegen intégré",
        "provenance": "Créations originales, références artistiques du projet poo",
        "rights": "Images générées pour ce projet ; aucune licence tierce attribuée.",
        "prompts": "docs/art/HERO_PROMPTS.md",
        "segmentation": "Composante alpha > 127 ; fragments voisins exclus avant découpage.",
        "heroes": entries,
    }
    (ART / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    preview_path = ROOT / "docs" / "previews" / "heroes.png"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(preview, str(preview_path))
    print("4 atlas normalisés, 24 poses par héros ; originaux conservés.")


if __name__ == "__main__":
    main()
