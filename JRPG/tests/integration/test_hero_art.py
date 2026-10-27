"""Contrats des images embarquées et synchronisation des animations."""

import hashlib
import json
from importlib.resources import files
from io import BytesIO
from unittest.mock import patch

import pygame
import pytest

from JRPG.presentation.hero_art import HERO_IDS, HeroArt, action_frame, walk_frame


def test_packaged_hero_art_matches_manifest_and_has_real_alpha() -> None:
    root = files("JRPG").joinpath("infrastructure", "content", "art")
    manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["heroes"]) == HERO_IDS
    for entry in manifest["heroes"].values():
        data = root.joinpath(entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        source = root.joinpath(entry["source"]).read_bytes()
        assert hashlib.sha256(source).hexdigest() == entry["source_sha256"]
        atlas = pygame.image.load(BytesIO(data))
        assert atlas.get_size() == (768, 768)
        assert atlas.get_flags() & pygame.SRCALPHA
        for frame in range(24):
            rect = pygame.Rect(frame % 4 * 192, frame // 4 * 128, 192, 128)
            mask = pygame.mask.from_surface(atlas.subsurface(rect))
            assert 100 < mask.count() < rect.width * rect.height // 2
            assert not any(mask.get_at((x, 0)) for x in range(192))
            assert not any(mask.get_at((x, 127)) for x in range(192))
            assert not any(mask.get_at((0, y)) or mask.get_at((191, y)) for y in range(128))


def test_art_loads_lazily_and_reuses_scaled_frames() -> None:
    surface = pygame.Surface((200, 150), pygame.SRCALPHA)
    with patch("pygame.image.load", wraps=pygame.image.load) as load:
        art = HeroArt()
        load.assert_not_called()
        assert not art.draw(surface, "extension", (100, 100))
        assert art.draw(surface, "ari", (100, 100), 16, 60)
        first = pygame.image.tobytes(surface, "RGBA")
        assert art.draw(surface, "ari", (100, 100), 17, 60)
        assert pygame.image.tobytes(surface, "RGBA") != first
        assert art.draw(surface, "ari", (100, 100), 16, 48)
        load.assert_called_once()
        with patch("pygame.transform.smoothscale") as scale:
            assert art.draw(surface, "ari", (100, 100), 16, 60)
            scale.assert_not_called()


def test_action_contact_matches_damage_reveal_and_clamps_time() -> None:
    assert action_frame(-1, 0.24, 0.72) == 16
    assert action_frame(0.239, 0.24, 0.72) == 19
    assert action_frame(0.24, 0.24, 0.72) == 20
    assert action_frame(0.72, 0.24, 0.72) == 23
    assert action_frame(9, 0.24, 0.72) == 23
    with pytest.raises(ValueError):
        action_frame(0, 0, 1)


@pytest.mark.parametrize("frame,height", [(-1, 60), (24, 60), (0, 0)])
def test_invalid_atlas_coordinates_fail_explicitly(frame: int, height: int) -> None:
    with pytest.raises(ValueError):
        HeroArt().draw(pygame.Surface((1, 1)), "ari", (0, 0), frame, height)


def test_walk_direction_and_cycle() -> None:
    assert walk_frame((0, 1), 0) == 0
    assert walk_frame((-1, 0), 0) == 4
    assert walk_frame((0, -1), 0) == 8
    assert walk_frame((1, 0), 0) == 12
    assert walk_frame((1, 0), 0.125) == 13
    assert walk_frame((1, 0), 0.5) == 12
