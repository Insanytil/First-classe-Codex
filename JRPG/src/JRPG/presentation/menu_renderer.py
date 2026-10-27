"""Menu lisible dans le cadrage logique ; aucune mutation du groupe."""

import pygame

from JRPG.presentation.game_menu import GameMenu
from JRPG.presentation.ui import GOLD, INK, JADE, MUTED, UiPainter


class MenuRenderer:
    def __init__(self) -> None:
        self._ui = UiPainter()
        self.hits: tuple[tuple[pygame.Rect, int], ...] = ()

    def draw(self, surface: pygame.Surface, menu: GameMenu) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((5, 15, 24, 180))
        surface.blit(shade, (0, 0))
        self._ui.panel(surface, pygame.Rect(22, 30, 596, 302), GOLD)
        self._ui.text(surface, menu.title, (36, 43), 24, GOLD)
        self._ui.text(surface, f"{menu.session.wallet.gold} pièces", (503, 48), 15, JADE)
        entries = menu.entries
        start = max(0, min(menu.selected - 3, len(entries) - 8))
        hits = []
        for index in range(start, min(len(entries), start + 8)):
            entry = entries[index]
            rect = pygame.Rect(34, 76 + (index - start) * 24, 267, 22)
            if index == menu.selected:
                pygame.draw.rect(surface, (39, 65, 69), rect, border_radius=3)
                pygame.draw.rect(surface, GOLD, rect, 1, border_radius=3)
            self._ui.text(
                surface,
                entry.label,
                (rect.x + 6, rect.y + 6),
                14,
                MUTED if entry.reason else INK,
                252,
            )
            hits.append((rect, index))
        if not entries:
            self._ui.text(surface, "Aucun élément.", (42, 87), 16, MUTED)
        elif menu.selected < len(entries):
            entry = entries[menu.selected]
            y = 82
            font = self._ui.font(15)
            for detail in entry.details:
                line = ""
                for word in detail.split():
                    candidate = f"{line} {word}".strip()
                    if font.size(candidate)[0] > 278:
                        self._ui.text(surface, line, (318, y), 15, INK, 278)
                        y += 16
                        line = word
                    else:
                        line = candidate
                if line:
                    self._ui.text(surface, line, (318, y), 15, INK, 278)
                    y += 19
                if y > 265:
                    break
        self._ui.text(
            surface,
            menu.message or (entries[menu.selected].reason if entries else None) or "",
            (37, 287),
            14,
            GOLD,
            560,
        )
        self._ui.text(
            surface,
            "Flèches : choisir · Entrée : valider · Retour : revenir · Tab : fermer",
            (37, 313),
            12,
            MUTED,
            560,
        )
        self.hits = tuple(hits)
