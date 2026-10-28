"""Décor et atlas Pygame ; lecture seule du contrôleur et de ses événements."""

from dataclasses import dataclass
from importlib.resources import files
from io import BytesIO
from math import ceil, pi

import pygame

from JRPG.domain.combat.model import Action, EventKind, Outcome, Side, StatusKind
from JRPG.presentation.attack_animation import attack_pose, contact_frame
from JRPG.presentation.battle_controller import BattleController, MenuMode, Playback
from JRPG.presentation.hero_art import HeroArt, action_frame
from JRPG.presentation.painted_sprites import ENEMY_SHEETS, SHEETS, PaintedSprites, enemy_kind
from JRPG.presentation.ui import GOLD, INK, JADE, MUTED, UiPainter


@dataclass(frozen=True, slots=True)
class HitRegion:
    rect: pygame.Rect
    kind: str
    index: int = 0
    identity: str = ""


class BattleRenderer:
    def __init__(self, continuation: bool = False) -> None:
        self._continuation = continuation
        self._backdrop: pygame.Surface | None = None
        self._scaled_backdrop: pygame.Surface | None = None
        self._backdrop_size = (0, 0)
        self._time = 0.0
        self._ui = UiPainter()
        self._heroes = HeroArt()
        self._monsters = PaintedSprites()
        self.hits: tuple[HitRegion, ...] = ()

    def update(self, elapsed: float) -> None:
        self._time = (self._time + elapsed) % 120

    def background(self, surface: pygame.Surface) -> None:
        if self._backdrop is None:
            data = (
                files("JRPG")
                .joinpath("infrastructure", "content", "art", "legacy", "battle_dalmasca.png")
                .read_bytes()
            )
            painting = pygame.image.load(BytesIO(data))
            # Les pieds des combattants doivent reposer sur la clairière, pas sur l'horizon.
            top = round(painting.height * 0.36)
            self._backdrop = painting.subsurface(
                (0, top, painting.width, painting.height - top)
            ).copy()
        if self._scaled_backdrop is None or self._backdrop_size != surface.get_size():
            width, height = surface.get_size()
            ratio = max(width / self._backdrop.width, height / self._backdrop.height)
            self._scaled_backdrop = pygame.transform.smoothscale(
                self._backdrop,
                (ceil(self._backdrop.width * ratio), ceil(self._backdrop.height * ratio)),
            )
            self._backdrop_size = surface.get_size()
        surface.blit(
            self._scaled_backdrop, self._scaled_backdrop.get_rect(center=surface.get_rect().center)
        )

    def draw(
        self, surface: pygame.Surface, controller: BattleController, log_offset: int = 0
    ) -> None:
        surface.fill((0, 0, 0, 0))
        hits: list[HitRegion] = []
        self._ui.panel(surface, pygame.Rect(12, 9, 616, 28))
        boss = next(
            (
                fighter
                for fighter in controller.displayed
                if fighter.side == Side.ENEMIES and enemy_kind(fighter.id) == "boss"
            ),
            None,
        )
        title = controller.threat_hint or (
            boss.name.upper() if boss is not None else "CLAIRIÈRE DES RUINES"
        )
        self._ui.text(surface, title, (23, 18), 13 if controller.threat_hint else 15, GOLD, 375)
        battle = controller.encounter.battle
        current = battle.current
        label = f"Tour {battle.turn_id}"
        if current is not None:
            label += f" · {current.name}"
        self._ui.text(surface, label, (405, 18), 14, JADE, 210)
        centers = self._centers(controller)
        counts = {Side.ALLIES: 0, Side.ENEMIES: 0}
        selected = controller.target_ids
        for fighter in controller.displayed:
            index = counts[fighter.side]
            counts[fighter.side] += 1
            ally = fighter.side == Side.ALLIES
            x, y = (450, 52 + index * 43) if ally else (17, 72 + index * 53)
            rect = pygame.Rect(x, y, 173, 38)
            center = centers[fighter.id]
            border = (
                GOLD
                if fighter.id in selected
                else (JADE if current is not None and current.id == fighter.id else (62, 91, 90))
            )
            self._ui.panel(surface, rect, border)
            self._ui.text(
                surface, fighter.name, (x + 7, y + 4), 14, INK if fighter.hp else MUTED, 112
            )
            status_labels = {
                StatusKind.POISON: "PSN",
                StatusKind.BURN: "BRU",
                StatusKind.SLEEP: "SOM",
                StatusKind.PARALYSIS: "PAR",
                StatusKind.SILENCE: "SIL",
                StatusKind.MODIFIER: "EFF",
                StatusKind.CHARGING: "CHARGE",
            }
            status = "/".join(status_labels[entry.definition.kind] for entry in fighter.statuses)
            self._ui.text(
                surface,
                status or ("GARDE" if fighter.defending else "KO" if not fighter.hp else ""),
                (x + 120, y + 6),
                10,
                GOLD,
                48,
            )
            for offset, value, maximum, color in (
                (21, fighter.hp, fighter.stats.hp, JADE),
                (30, fighter.mp, fighter.stats.mp, (109, 164, 222)),
            ):
                pygame.draw.rect(
                    surface, (40, 58, 63), (x + 7, y + offset, 101, 4), border_radius=2
                )
                if maximum:
                    pygame.draw.rect(
                        surface,
                        color,
                        (x + 7, y + offset, int(101 * value / maximum), 4),
                        border_radius=2,
                    )
                self._ui.text(surface, f"{value}/{maximum}", (x + 115, y + offset - 3), 10, MUTED)
            self._figure(
                surface,
                center,
                ally,
                index,
                fighter.hp > 0,
                fighter.defending,
                controller,
                fighter.id,
                centers,
            )
            hits.append(
                HitRegion(
                    rect.union(pygame.Rect(center[0] - 20, center[1] - 25, 40, 38)),
                    "target",
                    identity=fighter.id,
                )
            )
        self._effects(surface, controller, centers)
        self._ui.panel(surface, pygame.Rect(12, 226, 616, 20))
        self._ui.text(surface, controller.focus_hint, (21, 232), 13, GOLD, 598)
        self._menu(surface, controller, hits)
        self._journal(surface, controller, log_offset)
        self._ui.text(
            surface,
            "Flèches / Tab : choisir   Entrée : valider   Retour : annuler   Échap : quitter",
            (17, 351),
            10,
            MUTED,
        )
        if controller.settlement is not None:
            self._outcome(surface, controller, hits)
        self.hits = tuple(hits)

    @staticmethod
    def _centers(controller: BattleController) -> dict[str, tuple[int, int]]:
        counts = {Side.ALLIES: 0, Side.ENEMIES: 0}
        centers = {}
        for fighter in controller.displayed:
            index = counts[fighter.side]
            counts[fighter.side] += 1
            centers[fighter.id] = (
                (420, 75 + index * 43)
                if fighter.side == Side.ALLIES
                else ((260, 155) if enemy_kind(fighter.id) == "boss" else (219, 95 + index * 53))
            )
        return centers

    def _figure(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        ally: bool,
        index: int,
        alive: bool,
        defending: bool,
        controller: BattleController,
        identity: str,
        centers: dict[str, tuple[int, int]],
    ) -> None:
        x, y = center
        ground_y = y
        playback = controller.playback
        kind = enemy_kind(identity) if not ally else None
        attacking = (
            playback is not None
            and playback.result.command.actor_id == identity
            and playback.result.command.action in {Action.ATTACK, Action.SKILL}
        )
        if attacking and playback is not None and playback.result.command.action == Action.ATTACK:
            targets = playback.result.command.targets
            if targets and targets[0] in centers:
                tx, ty = centers[targets[0]]
                pose = attack_pose(
                    playback.elapsed,
                    Playback.IMPACT,
                    Playback.DURATION,
                    center,
                    (tx + (45 if ally else -45), ty),
                    jump=kind == "slime",
                )
                x, y, ground_y = round(pose.x), round(pose.y), round(pose.ground_y)
        pygame.draw.ellipse(surface, (17, 36, 37, 160), (x - 19, ground_y + 7, 38, 9))
        palettes = ((218, 176, 103), (107, 166, 213), (130, 193, 157), (175, 144, 201))
        color = palettes[index % len(palettes)] if ally else (129, 154, 130)
        if not alive:
            pygame.draw.ellipse(surface, (78, 91, 85), (x - 14, y + 2, 28, 9))
            return
        frame = 16
        if (
            playback is not None
            and playback.result.command.actor_id == identity
            and playback.result.command.action in {Action.ATTACK, Action.SKILL}
        ):
            frame = action_frame(playback.elapsed, Playback.IMPACT, Playback.DURATION)
        if ally and self._heroes.draw(surface, identity, (x, y + 13), frame):
            if defending:
                pygame.draw.ellipse(surface, (130, 206, 214), (x - 22, y - 35, 44, 53), 1)
            return
        if kind is not None:
            idle, action = ENEMY_SHEETS[kind]
            monster_frame = int(self._time * 3) % 4
            sheet, height = idle, 110 if kind == "boss" else 68
            charging = any(
                fighter.id == identity and fighter.has_status(StatusKind.CHARGING)
                for fighter in controller.displayed
            )
            telegraphing = (
                attacking
                and playback is not None
                and playback.result.command.targets == (identity,)
            )
            if (
                kind == "boss"
                and (charging or telegraphing)
                and not (attacking and not telegraphing)
            ):
                monster_frame = 3
                pygame.draw.ellipse(surface, GOLD, (x - 34, ground_y + 4, 68, 17), 2)
            elif attacking and playback is not None:
                monster_frame = contact_frame(
                    playback.elapsed,
                    Playback.IMPACT,
                    Playback.DURATION,
                    5 if kind == "slime" else 4,
                )
                sheet, height = action, 118 if kind == "boss" else 74
                monster_frame += SHEETS[action].action_start
            self._monsters.draw(surface, sheet, (x, y + 13), monster_frame, height, flip=True)
            return
        if ally:
            pygame.draw.polygon(
                surface, color, [(x - 10, y + 8), (x - 7, y - 15), (x + 6, y - 15), (x + 12, y + 8)]
            )
            pygame.draw.circle(surface, (218, 193, 153), (x, y - 21), 7)
            pygame.draw.arc(surface, (62, 58, 55), (x - 7, y - 29, 15, 16), 0, pi, 5)
            pygame.draw.line(surface, (205, 214, 196), (x - 10, y - 4), (x - 19, y - 17), 3)
            pygame.draw.line(surface, (55, 62, 58), (x - 5, y + 8), (x - 7, y + 13), 4)
            pygame.draw.line(surface, (55, 62, 58), (x + 6, y + 8), (x + 8, y + 13), 4)
        else:
            pygame.draw.ellipse(surface, color, (x - 17, y - 17, 34, 28))
            pygame.draw.polygon(
                surface, color, [(x - 14, y - 9), (x - 16, y - 27), (x - 3, y - 14)]
            )
            pygame.draw.polygon(
                surface, color, [(x + 3, y - 14), (x + 16, y - 27), (x + 14, y - 9)]
            )
            pygame.draw.circle(surface, (237, 206, 131), (x - 6, y - 6), 2)
            pygame.draw.circle(surface, (237, 206, 131), (x + 6, y - 6), 2)
        if defending:
            pygame.draw.ellipse(surface, (130, 206, 214), (x - 22, y - 35, 44, 53), 1)

    def _effects(
        self,
        surface: pygame.Surface,
        controller: BattleController,
        centers: dict[str, tuple[int, int]],
    ) -> None:
        playback = controller.playback
        if playback is None:
            return
        progress = (playback.elapsed - Playback.IMPACT) / (Playback.DURATION - Playback.IMPACT)
        actor_position = centers[playback.result.command.actor_id]
        for event in playback.result.events:
            if event.target_id not in centers:
                continue
            x, y = centers[event.target_id]
            if playback.elapsed < Playback.IMPACT and event.kind in {
                EventKind.DAMAGE,
                EventKind.HEAL,
                EventKind.MANA_RESTORED,
                EventKind.REVIVED,
            }:
                color = JADE if event.kind != EventKind.DAMAGE else GOLD
                pygame.draw.line(surface, color, actor_position, (x, y - 12), 2)
            if 0 <= progress < 1 and event.kind in {
                EventKind.DAMAGE,
                EventKind.HEAL,
                EventKind.MANA_RESTORED,
                EventKind.REVIVED,
                EventKind.MISS,
            }:
                healing = event.kind in {EventKind.HEAL, EventKind.REVIVED, EventKind.MANA_RESTORED}
                color = JADE if healing else GOLD if event.critical else (245, 203, 165)
                if event.kind == EventKind.MANA_RESTORED:
                    color = (109, 164, 222)
                value = (
                    "Raté"
                    if event.kind == EventKind.MISS
                    else f"{'+' if healing else '-'}{event.amount}"
                )
                self._ui.text(surface, value, (x - 12, y - 35 - int(progress * 15)), 23, color)
                if event.kind == EventKind.MANA_RESTORED:
                    self._ui.text(surface, "PM", (x + 20, y - 30 - int(progress * 15)), 12, color)

    def _menu(
        self, surface: pygame.Surface, controller: BattleController, hits: list[HitRegion]
    ) -> None:
        self._ui.panel(surface, pygame.Rect(12, 252, 258, 94))
        heading = {
            MenuMode.ACTION: "COMMANDES",
            MenuMode.SKILL: "COMPÉTENCES",
            MenuMode.ITEM: "OBJETS",
            MenuMode.TARGET: "CIBLES",
        }[controller.mode]
        self._ui.text(surface, heading, (22, 259), 11, MUTED)
        options = controller.options
        if not options:
            self._ui.text(
                surface,
                "Action en cours…" if controller.playback else "L'ennemi se prépare…",
                (23, 289),
                15,
                GOLD,
            )
            return
        start = (
            0
            if controller.mode == MenuMode.ACTION
            else max(0, min(controller.selected - 1, len(options) - 3))
        )
        for index in range(
            start, min(len(options), start + (6 if controller.mode == MenuMode.ACTION else 3))
        ):
            slot = index - start
            if controller.mode == MenuMode.ACTION:
                rect = pygame.Rect(19 + (slot % 2) * 123, 272 + (slot // 2) * 23, 119, 21)
            else:
                rect = pygame.Rect(19, 272 + slot * 23, 244, 21)
            option = options[index]
            pygame.draw.rect(
                surface,
                (39, 65, 69) if index == controller.selected else (22, 43, 53),
                rect,
                border_radius=3,
            )
            if index == controller.selected:
                pygame.draw.rect(surface, GOLD, rect, 1, border_radius=3)
            label = (
                f"{index + 1}  {option.label}"
                if controller.mode == MenuMode.ACTION
                else option.label
            )
            self._ui.text(
                surface,
                label,
                (rect.x + 6, rect.y + 5),
                13,
                MUTED if option.reason else INK,
                rect.width - 10,
            )
            hits.append(HitRegion(rect, "menu", index))

    def _journal(self, surface: pygame.Surface, controller: BattleController, offset: int) -> None:
        self._ui.panel(surface, pygame.Rect(280, 252, 348, 94))
        self._ui.text(surface, "JOURNAL", (290, 259), 11, MUTED)
        self._ui.text(surface, "Page haut / bas", (544, 259), 10, MUTED)
        end = len(controller.log) - offset
        lines = controller.log[max(0, end - 4) : end]
        for index, line in enumerate(lines):
            self._ui.text(surface, line, (290, 276 + index * 16), 12, INK, 326)

    def _outcome(
        self, surface: pygame.Surface, controller: BattleController, hits: list[HitRegion]
    ) -> None:
        result = controller.settlement
        assert result is not None
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((5, 15, 24, 170))
        surface.blit(shade, (0, 0))
        self._ui.panel(surface, pygame.Rect(158, 83, 324, 132), GOLD)
        titles = {
            Outcome.VICTORY: "Victoire",
            Outcome.DEFEAT: "Défaite",
            Outcome.FLED: "Fuite réussie",
        }
        self._ui.text(surface, titles[result.outcome], (180, 99), 28, GOLD)
        reward = result.rewards
        detail = (
            f"{reward.experience} XP par héros · {reward.gold} pièces"
            if result.outcome == Outcome.VICTORY
            else "Le combat est terminé."
        )
        self._ui.text(surface, detail, (181, 131), 16, INK, 280)
        loot = ", ".join(f"{stack.quantity} {stack.item.name}" for stack in reward.items)
        self._ui.text(surface, f"Butin : {loot or 'aucun'}", (181, 151), 14, MUTED, 280)
        rect = pygame.Rect(180, 177, 279, 25)
        pygame.draw.rect(surface, (44, 80, 80), rect, border_radius=4)
        label = "Entrée  ·  Revenir à la carte" if self._continuation else "R  ·  Rejouer le combat"
        self._ui.text(surface, label, (229, 184), 15, INK)
        hits.clear()
        hits.append(HitRegion(rect, "continue" if self._continuation else "restart"))
