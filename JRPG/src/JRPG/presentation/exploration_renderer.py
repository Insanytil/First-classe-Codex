"""Tuiles 32 px, profondeur, éléments de surplomb et HUD d'exploration."""

from math import ceil, sin

import pygame

from JRPG.domain.world import TILE_SIZE, Decoration, DecorationKind, MapObject, ObjectKind, Tile
from JRPG.presentation.exploration_controller import Camera, ExplorationController
from JRPG.presentation.hero_art import HeroArt, walk_frame
from JRPG.presentation.painted_sprites import ENEMY_SHEETS, NPC_SHEETS, PaintedSprites
from JRPG.presentation.ui import GOLD, INK, JADE, MUTED, UiPainter
from JRPG.presentation.world_ambience import WorldAmbience
from JRPG.presentation.world_art import WorldArt


class ExplorationRenderer:
    def __init__(self) -> None:
        self._ui = UiPainter()
        self._heroes = HeroArt()
        self._sprites = PaintedSprites()
        self._world_art = WorldArt()
        self._ambience = WorldAmbience()
        self.dialogue_hits: tuple[tuple[pygame.Rect, int], ...] = ()

    def update(self, elapsed: float) -> None:
        self._ambience.update(elapsed)

    def background(self, surface: pygame.Surface, view: ExplorationController) -> None:
        world = view.session.world
        area = world.current_map
        camera = Camera.follow(world.position, area.pixel_size, surface.get_size())
        painted = self._world_art.draw(surface, area.id, area.pixel_size, (camera.x, camera.y))
        if not painted:
            surface.fill((39, 65, 51))
            width, height = surface.get_size()
            left, top = int(camera.x // TILE_SIZE), int(camera.y // TILE_SIZE)
            for row in range(top, ceil((camera.y + height) / TILE_SIZE) + 1):
                for column in range(left, ceil((camera.x + width) / TILE_SIZE) + 1):
                    tile = (
                        area.ground[row][column] if area.contains_cell(column, row) else Tile.GRASS
                    )
                    x, y = camera.project(column * TILE_SIZE, row * TILE_SIZE)
                    self._tile(surface, tile, x, y, column, row)
        for decoration in area.decorations:
            if not decoration.foreground and (
                not painted or decoration.kind != DecorationKind.ROOF
            ):
                self._decoration(surface, decoration, camera)
        objects = world.visible_objects()
        entities: list[tuple[float, MapObject | Decoration | None]] = [
            (entry.center[1], entry) for entry in objects
        ]
        entities.extend(
            ((decoration.row + 0.5) * TILE_SIZE, decoration)
            for decoration in area.decorations
            if decoration.foreground and (not painted or decoration.kind != DecorationKind.ROOF)
        )
        entities.append((world.position.y, None))
        nearby = world.nearby()
        for _, entry in sorted(entities, key=lambda pair: pair[0]):
            if entry is None:
                x, y = camera.project(world.position.x, world.position.y)
                leader = view.session.party.leader
                if leader is None or not self._heroes.draw(
                    surface,
                    leader.id,
                    (x, y),
                    walk_frame(view.facing, view.walk_phase),
                    48,
                ):
                    self._person(
                        surface, x, y, (221, 179, 101), sin(view.walk_phase * 12) * 2, view.facing
                    )
            elif isinstance(entry, Decoration):
                self._decoration(surface, entry, camera)
            else:
                self._object(
                    surface,
                    entry,
                    camera,
                    entry.id in world.state.opened_chests,
                    nearby is not None and nearby.id == entry.id,
                )
        self._ambience.draw(surface, area, camera)

    @staticmethod
    def _tile(surface: pygame.Surface, tile: Tile, x: int, y: int, column: int, row: int) -> None:
        colors = {
            Tile.GRASS: (62, 91, 63),
            Tile.PATH: (139, 121, 81),
            Tile.WATER: (45, 101, 118),
            Tile.WALL: (82, 92, 83),
            Tile.FLOOR: (112, 119, 99),
            Tile.BRIDGE: (133, 101, 66),
        }
        base = colors[tile]
        delta = ((column * 7 + row * 11) % 3) * 3
        color = tuple(min(255, component + delta) for component in base)
        pygame.draw.rect(surface, color, (x, y, 32, 32))
        if tile == Tile.GRASS:
            pygame.draw.line(surface, (76, 108, 73), (x + 8, y + 18), (x + 10, y + 13), 1)
            pygame.draw.line(surface, (50, 79, 57), (x + 24, y + 28), (x + 26, y + 23), 1)
        elif tile == Tile.WATER:
            pygame.draw.line(surface, (72, 135, 143), (x + 4, y + 10), (x + 20, y + 10), 1)
            pygame.draw.line(surface, (55, 119, 134), (x + 15, y + 23), (x + 29, y + 23), 1)
        elif tile in {Tile.WALL, Tile.FLOOR}:
            pygame.draw.rect(surface, (77, 88, 78), (x, y, 32, 32), 1)
            pygame.draw.line(surface, (135, 139, 116), (x + 3, y + 3), (x + 26, y + 3), 1)
        elif tile == Tile.BRIDGE:
            for dy in (3, 11, 19, 27):
                pygame.draw.line(surface, (84, 66, 48), (x, y + dy), (x + 31, y + dy), 2)

    @staticmethod
    def _person(
        surface: pygame.Surface,
        x: int,
        y: int,
        color: tuple[int, int, int],
        stride: float = 0,
        facing: tuple[float, float] = (0, 1),
    ) -> None:
        pygame.draw.ellipse(surface, (31, 49, 43), (x - 10, y - 3, 20, 8))
        pygame.draw.line(surface, (46, 49, 46), (x - 4, y - 3), (x - 5, y + int(stride)), 4)
        pygame.draw.line(surface, (46, 49, 46), (x + 4, y - 3), (x + 5, y - int(stride)), 4)
        pygame.draw.polygon(
            surface, color, [(x - 8, y - 3), (x - 6, y - 18), (x + 6, y - 18), (x + 8, y - 3)]
        )
        pygame.draw.circle(surface, (219, 191, 151), (x, y - 22), 6)
        pygame.draw.arc(surface, (77, 60, 47), (x - 6, y - 29, 13, 13), 0, 3.14, 4)
        if facing[1] < 0:
            pygame.draw.circle(surface, (77, 60, 47), (x, y - 23), 5)
        else:
            pygame.draw.circle(surface, (46, 51, 48), (x + int(facing[0] * 3), y - 21), 1)

    def _object(
        self, surface: pygame.Surface, entry: MapObject, camera: Camera, opened: bool, nearby: bool
    ) -> None:
        x, y = camera.project(*entry.center)
        if not surface.get_rect().inflate(120, 120).collidepoint(x, y):
            return
        if nearby:
            pygame.draw.ellipse(surface, GOLD, (x - 15, y - 7, 30, 15), 1)
        if entry.kind == ObjectKind.NPC:
            sprite = NPC_SHEETS.get(entry.id)
            if sprite is None:
                self._person(surface, x, y, (128, 171, 174))
            else:
                self._sprites.draw(surface, sprite, (x, y), int(self._ambience.time * 1.5) % 4, 48)
        elif entry.kind == ObjectKind.CHEST:
            pygame.draw.rect(surface, (102, 69, 46), (x - 12, y - 14, 24, 16), border_radius=2)
            pygame.draw.rect(surface, GOLD, (x - 12, y - 14, 24, 16), 1, border_radius=2)
            pygame.draw.rect(surface, (193, 148, 73), (x - 2, y - 12, 4, 10))
            if opened:
                pygame.draw.rect(surface, (71, 51, 38), (x - 9, y - 12, 18, 7))
                pygame.draw.line(surface, GOLD, (x - 12, y - 20), (x + 12, y - 20), 3)
        elif entry.kind == ObjectKind.ENCOUNTER:
            kind = entry.enemies[0] if entry.enemies else ""
            sheet = ENEMY_SHEETS.get(kind)
            if sheet is not None:
                self._sprites.draw(
                    surface,
                    sheet[0],
                    (x, y),
                    int(self._ambience.time * 3) % 4,
                    110 if kind == "boss" else 50,
                )
            else:
                pygame.draw.ellipse(surface, (126, 144, 125), (x - 12, y - 14, 24, 17))
        else:
            pygame.draw.ellipse(surface, (59, 102, 97), (x - 15, y - 7, 30, 16))
            pygame.draw.ellipse(surface, JADE, (x - 15, y - 7, 30, 16), 2)
            pygame.draw.line(surface, JADE, (x, y - 23), (x, y - 10), 2)
            pygame.draw.polygon(surface, JADE, [(x - 5, y - 16), (x + 5, y - 16), (x, y - 9)])
        if nearby or entry.kind == ObjectKind.PORTAL:
            self._ui.text(surface, entry.name, (x - 40, y - 41), 13, GOLD, 120)

    def _decoration(self, surface: pygame.Surface, decoration: Decoration, camera: Camera) -> None:
        x, y = camera.project((decoration.column + 0.5) * 32, (decoration.row + 0.5) * 32)
        if not surface.get_rect().inflate(240, 200).collidepoint(x, y):
            return
        if decoration.kind == DecorationKind.TREE:
            sway = round(sin(self._ambience.time * 1.4 + decoration.column) * 1.2)
            self._sprites.draw(surface, "tree", (x + sway, y + 5), height=96)
        elif decoration.kind == DecorationKind.ROOF:
            pygame.draw.polygon(
                surface,
                (116, 79, 61),
                [(x - 119, y + 49), (x - 90, y - 47), (x + 94, y - 47), (x + 122, y + 49)],
            )
            for dy in range(-31, 49, 16):
                pygame.draw.line(surface, (143, 95, 65), (x - 95, y + dy), (x + 98, y + dy), 2)
        else:
            self._sprites.draw(surface, "pillar", (x, y + 5), height=64)

    def foreground(self, surface: pygame.Surface, view: ExplorationController) -> None:
        surface.fill((0, 0, 0, 0))
        self.dialogue_hits = ()
        session = view.session
        self._ui.panel(surface, pygame.Rect(10, 8, 620, 29))
        self._ui.text(surface, session.world.current_map.name, (20, 16), 18, GOLD)
        self._ui.text(surface, f"{session.wallet.gold} pièces", (534, 18), 14, INK)
        self._ui.panel(surface, pygame.Rect(12, 45, 120, 79))
        for index, member in enumerate(session.party.members):
            self._ui.text(
                surface,
                f"{member.definition.name}  {member.hp}/{member.stats.hp} PV",
                (20, 52 + index * 17),
                12,
                INK if member.hp else MUTED,
                105,
            )
        nearby = session.world.nearby()
        prompt = "Flèches / ZQSD : marcher · E : interagir · Tab : menu · F5/F9 : sauvegarde"
        if nearby is not None:
            prompt = f"E / Entrée : {nearby.name}"
        self._ui.panel(surface, pygame.Rect(10, 335, 620, 19))
        self._ui.text(surface, prompt, (20, 341), 12, JADE, 600)
        if view.message and not view.dialogue:
            self._ui.panel(surface, pygame.Rect(12, 305, 616, 24))
            self._ui.text(surface, view.message, (21, 313), 13, GOLD, 598)
        if "adventure_complete" in session.world.state.flags:
            self._ui.text(surface, "Voyage accompli", (450, 49), 15, GOLD)
        if view.dialogue:
            has_choices = view.conversation is not None
            top = 167 if has_choices else 242
            self._ui.panel(surface, pygame.Rect(16, top, 608, 330 - top), GOLD)
            self._ui.text(surface, view.speaker, (28, top + 9), 17, GOLD)
            font = self._ui.font(15)
            lines: list[str] = []
            current = ""
            for word in view.dialogue.split():
                candidate = f"{current} {word}".strip()
                if font.size(candidate)[0] > 575:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
            for index, line in enumerate(lines[:3]):
                self._ui.text(surface, line, (28, top + 30 + index * 14), 15, INK, 575)
            if view.conversation is not None:
                choices = view.conversation.choices
                start = max(0, min(view.dialogue_selected - 1, len(choices) - 3))
                hits = []
                for index in range(start, min(len(choices), start + 3)):
                    rect = pygame.Rect(27, 248 + (index - start) * 23, 584, 21)
                    if index == view.dialogue_selected:
                        pygame.draw.rect(surface, (39, 65, 69), rect, border_radius=3)
                        pygame.draw.rect(surface, GOLD, rect, 1, border_radius=3)
                    self._ui.text(
                        surface, choices[index].label, (rect.x + 7, rect.y + 5), 14, INK, 565
                    )
                    hits.append((rect, index))
                self.dialogue_hits = tuple(hits)
                self._ui.text(
                    surface,
                    "Flèches : choisir · Entrée : valider · Retour : repartir",
                    (300, 321),
                    10,
                    MUTED,
                )
            else:
                self._ui.text(surface, "E / Entrée / clic : continuer", (464, 316), 11, MUTED)
