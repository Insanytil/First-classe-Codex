"""Intégrité des ressources, scènes vivantes et absence d'effets métier du rendu."""

import hashlib
import json
from importlib.resources import files
from io import BytesIO
from unittest.mock import patch

import pygame
import pytest

from JRPG.domain.world import MapPosition
from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
from JRPG.infrastructure.training_encounter import create_training_encounter
from JRPG.infrastructure.world_content import create_exploration_session
from JRPG.presentation.battle_controller import BattleController
from JRPG.presentation.battle_scene import BattleScene
from JRPG.presentation.exploration_controller import Camera, ExplorationController
from JRPG.presentation.exploration_renderer import ExplorationRenderer
from JRPG.presentation.painted_sprites import SHEETS, PaintedSprites, enemy_kind
from JRPG.presentation.world_ambience import WorldAmbience
from JRPG.presentation.world_art import Registration, WorldArt


def test_embedded_legacy_sprites_match_source_hashes_and_dimensions() -> None:
    for name, specification in SHEETS.items():
        root = files("JRPG").joinpath("infrastructure", "content", "art", specification.folder)
        manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
        entry = manifest["sprites" if specification.folder == "legacy" else "creatures"][name]
        data = root.joinpath(entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        if specification.folder == "legacy":
            assert entry["origin"].startswith("assets/")
        else:
            assert (
                hashlib.sha256(root.joinpath(entry["source"]).read_bytes()).hexdigest()
                == entry["source_sha256"]
            )
        assert tuple(entry["cell"]) == specification.cell
        image = pygame.image.load(BytesIO(data))
        assert image.get_size() == (
            specification.cell[0] * specification.count,
            specification.cell[1],
        )
        assert image.get_flags() & pygame.SRCALPHA


def test_generated_map_paintings_are_complete_and_match_manifest() -> None:
    root = files("JRPG").joinpath("infrastructure", "content", "art", "maps")
    manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
    art = WorldArt()
    for identity, entry in manifest["maps"].items():
        data = root.joinpath(entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        painting = art.painting(identity, tuple(entry["world_size"]))
        assert painting is not None
        assert painting.get_size() == tuple(entry["world_size"])
        assert art.painting(identity, painting.get_size()) is painting
    assert art.painting("extension", (640, 360)) is None


@pytest.mark.parametrize("identity", ["village", "forest", "ruins"])
def test_ambience_lives_while_stationary_without_mutating_world(identity: str) -> None:
    pygame.font.init()
    session = create_exploration_session(position=MapPosition(identity, 8.5 * 32, 10.5 * 32))
    view = ExplorationController(session)
    renderer = ExplorationRenderer()
    mapper = GameSnapshotMapper()
    before = mapper.capture(session)
    first, later = pygame.Surface((640, 360)), pygame.Surface((640, 360))
    renderer.background(first, view)
    renderer.update(1.7)
    renderer.background(later, view)
    assert pygame.image.tobytes(first, "RGB") != pygame.image.tobytes(later, "RGB")
    assert mapper.capture(session) == before
    renderer.background(first, view)
    assert pygame.image.tobytes(first, "RGB") == pygame.image.tobytes(later, "RGB")


@pytest.mark.parametrize("size", [(1600, 360), (360, 1000), (640, 360)])
def test_painted_camera_fills_wide_and_tall_windows(size: tuple[int, int]) -> None:
    session = create_exploration_session()
    area = session.world.current_map
    camera = Camera.follow(session.world.position, area.pixel_size, size)
    surface = pygame.Surface(size)
    assert WorldArt().draw(surface, area.id, area.pixel_size, (camera.x, camera.y))
    assert all(
        surface.get_at(point)[:3] != (0, 0, 0)
        for point in ((0, 0), (size[0] - 1, 0), (0, size[1] - 1), (size[0] - 1, size[1] - 1))
    )


def test_texture_registration_covers_every_pixel_without_gaps() -> None:
    image = pygame.Surface((100, 100))
    image.fill((170, 110, 80))
    pygame.draw.rect(image, (20, 150, 180), (40, 0, 20, 100))
    mapped = Registration(((0, 0), (0.4, 0.475), (0.6, 0.525), (1, 1))).apply(image, (1280, 768))
    assert mapped.get_at((639, 200))[:3] == (20, 150, 180)
    assert mapped.get_at((607, 200))[:3] == (170, 110, 80)
    assert mapped.get_at((672, 200))[:3] == (170, 110, 80)
    assert all(mapped.get_at((x, 300))[:3] != (0, 0, 0) for x in range(1280))


@pytest.mark.parametrize(
    "axis",
    [
        ((0.0, 0.0), (0.5, 0.6), (0.4, 0.8), (1.0, 1.0)),
        ((0.0, 0.0), (0.5, float("nan")), (1.0, 1.0)),
        ((0.1, 0.0), (1.0, 1.0)),
    ],
)
def test_invalid_registration_fails_explicitly(axis: tuple[tuple[float, float], ...]) -> None:
    with pytest.raises(ValueError):
        Registration(axis)


def test_monster_identity_does_not_depend_on_formation_index() -> None:
    pygame.font.init()
    controller = BattleController(create_training_encounter())
    controller.displayed = tuple(reversed(controller.displayed))
    scene = BattleScene(lambda: controller)
    with patch.object(scene.renderer._monsters, "draw") as draw:
        scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    assert [call.args[1] for call in draw.call_args_list] == ["flan", "wolf", "wolf"]
    assert enemy_kind("wolf-2") == "wolf"
    assert enemy_kind("extension-1") is None


def test_monster_action_frames_differ_and_scaled_images_are_cached() -> None:
    art = PaintedSprites()
    surface = pygame.Surface((200, 150), pygame.SRCALPHA)
    with patch("pygame.image.load", wraps=pygame.image.load) as load:
        art.draw(surface, "wolf_claw", (100, 130), 0, 100, True)
        first = pygame.image.tobytes(surface, "RGBA")
        surface.fill((0, 0, 0, 0))
        art.draw(surface, "wolf_claw", (100, 130), 4, 100, True)
        assert pygame.image.tobytes(surface, "RGBA") != first
        load.assert_called_once()
        with patch("pygame.transform.smoothscale") as scale:
            art.draw(surface, "wolf_claw", (100, 130), 4, 100, True)
            scale.assert_not_called()


def test_ambience_rejects_invalid_time_and_stays_bounded() -> None:
    ambience = WorldAmbience()
    for elapsed in (-1.0, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            ambience.update(elapsed)
    ambience.update(12000.5)
    assert 0 <= ambience.time < 120
