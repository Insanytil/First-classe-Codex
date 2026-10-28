"""Normaliser les 12 poses imagegen de chaque créature, sources conservées."""

import hashlib
import json
from pathlib import Path
from statistics import median

import pygame

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "src/JRPG/infrastructure/content/art/creatures"


def main() -> None:
    entries = {}
    for identity in ("wisp", "briar", "raven"):
        source = ART / "sources" / f"{identity}-v1.png"
        image = pygame.image.load(str(source))
        frames = []
        for index in range(12):
            left, right = (
                round(index % 4 * image.width / 4),
                round((index % 4 + 1) * image.width / 4),
            )
            top, bottom = (
                round(index // 4 * image.height / 3),
                round((index // 4 + 1) * image.height / 3),
            )
            cell = image.subsurface((left, top, right - left, bottom - top)).copy()
            components = pygame.mask.from_surface(cell, 127).connected_components(100)
            if not components:
                raise ValueError(f"Pose vide : {identity} {index}")
            mask = max(components, key=lambda entry: entry.count())
            isolated = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
            cell.blit(isolated, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            frames.append(cell.subsurface(mask.get_bounding_rects()[0]).copy())
        scale = min(
            140 / median(frame.height for frame in frames[:4]),
            240 / max(frame.width for frame in frames),
            176 / max(frame.height for frame in frames),
        )
        atlas = pygame.Surface((256 * 12, 192), pygame.SRCALPHA)
        for index, frame in enumerate(frames):
            sprite = pygame.transform.smoothscale(
                frame, (round(frame.width * scale), round(frame.height * scale))
            )
            atlas.blit(sprite, (index * 256 + (256 - sprite.width) // 2, 184 - sprite.height))
        target = ART / f"{identity}.png"
        pygame.image.save(atlas, str(target))
        entries[identity] = dict(
            file=target.name,
            source=f"sources/{source.name}",
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            cell=[256, 192],
            count=12,
            anchor=[128, 184],
            idle=[0, 1, 2, 3],
            action=list(range(4, 12)),
        )
    (ART / "manifest.json").write_text(
        json.dumps(
            dict(
                version=1,
                generator="imagegen intégré",
                prompts="docs/art/CREATURE_PROMPTS.md",
                creatures=entries,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("Trois atlas : quatre poses d'attente et huit poses d'action par créature.")


if __name__ == "__main__":
    main()
