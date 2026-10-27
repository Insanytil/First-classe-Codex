"""Route exploration, dialogues, menus et combat sans mutations de rendu."""

import pygame

from JRPG.application.battle_session import SettlementResult
from JRPG.application.exploration import ExplorationSession
from JRPG.application.saves import SaveService
from JRPG.presentation.battle_controller import BattleController
from JRPG.presentation.battle_scene import BattleScene
from JRPG.presentation.exploration_controller import ExplorationController
from JRPG.presentation.exploration_renderer import ExplorationRenderer
from JRPG.presentation.game_menu import GameMenu, MenuPage
from JRPG.presentation.menu_renderer import MenuRenderer


class AdventureScene:
    def __init__(self, session: ExplorationSession, saves: SaveService | None = None) -> None:
        self.controller = ExplorationController(session)
        self.renderer = ExplorationRenderer()
        self.menus = GameMenu(session, saves, self._loaded)
        self.menu_renderer = MenuRenderer()
        self.battle: BattleScene | None = None
        self._pressed: set[int] = set()

    def _loaded(self, session: ExplorationSession) -> None:
        self.controller = ExplorationController(session)
        self.controller.message = "Partie chargée."
        self.menus.session = session
        self.menus.close()
        self._pressed.clear()

    def handle_event(
        self, event: pygame.event.Event, position: tuple[int, int] | None = None
    ) -> None:
        if event.type == pygame.WINDOWFOCUSLOST:
            self._pressed.clear()
        if self.battle is not None:
            self.battle.handle_event(event, position)
            return
        if self.menus.opened:
            self._menu_event(event, position)
            return
        if self.controller.dialogue:
            self._dialogue_event(event, position)
            self._check_shop()
            return
        if event.type == pygame.KEYUP:
            self._pressed.discard(event.key)
        elif event.type == pygame.KEYDOWN:
            shortcuts = {
                pygame.K_TAB: MenuPage.MAIN,
                pygame.K_i: MenuPage.INVENTORY,
                pygame.K_c: MenuPage.CHARACTERS,
                pygame.K_j: MenuPage.QUESTS,
                pygame.K_F5: MenuPage.SAVE,
                pygame.K_F9: MenuPage.LOAD,
            }
            if event.key in shortcuts:
                self._pressed.clear()
                self.menus.open(shortcuts[event.key])
            elif event.key in {pygame.K_e, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER}:
                self._pressed.clear()
                encounter = self.controller.interact()
                if encounter is not None:
                    self.battle = BattleScene(
                        lambda: BattleController(encounter), self._finish_battle
                    )
            else:
                self._pressed.add(event.key)

    def _check_shop(self) -> None:
        if self.controller.shop_requested is not None:
            self.menus.open_shop(self.controller.shop_requested)
            self.controller.shop_requested = None
            self._pressed.clear()

    def _menu_event(self, event: pygame.event.Event, position: tuple[int, int] | None) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.menus.close()
            elif event.key == pygame.K_BACKSPACE:
                self.menus.back()
            elif event.key in {pygame.K_DOWN, pygame.K_RIGHT}:
                self.menus.move(1)
            elif event.key in {pygame.K_UP, pygame.K_LEFT}:
                self.menus.move(-1)
            elif event.key in {pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER}:
                self.menus.choose()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and position is not None:
            for rect, index in self.menu_renderer.hits:
                if rect.collidepoint(position):
                    self.menus.choose(index)
                    break

    def _dialogue_event(self, event: pygame.event.Event, position: tuple[int, int] | None) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in {pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB}:
                self.controller.move_dialogue(1)
            elif event.key in {pygame.K_UP, pygame.K_LEFT}:
                self.controller.move_dialogue(-1)
            elif event.key == pygame.K_BACKSPACE:
                self.controller.close_dialogue()
            elif event.key in {pygame.K_e, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER}:
                self.controller.interact()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.controller.conversation is None:
                self.controller.close_dialogue()
            elif position is not None:
                for rect, index in self.renderer.dialogue_hits:
                    if rect.collidepoint(position):
                        self.controller.choose_dialogue(index)
                        break

    def update(self, elapsed: float) -> None:
        self.controller.session.advance_time(elapsed)
        if self.battle is not None:
            self.battle.update(elapsed)
            return
        self.renderer.update(elapsed)
        if self.menus.opened:
            return
        dx = int(bool(self._pressed & {pygame.K_RIGHT, pygame.K_d})) - int(
            bool(self._pressed & {pygame.K_LEFT, pygame.K_q, pygame.K_a})
        )
        dy = int(bool(self._pressed & {pygame.K_DOWN, pygame.K_s})) - int(
            bool(self._pressed & {pygame.K_UP, pygame.K_z, pygame.K_w})
        )
        self.controller.update(dx, dy, elapsed)

    def _finish_battle(self, result: SettlementResult) -> None:
        self.controller.after_combat()
        self.battle = None
        self._pressed.clear()

    def draw_background(self, surface: pygame.Surface) -> None:
        if self.battle is not None:
            self.battle.draw_background(surface)
        else:
            self.renderer.background(surface, self.controller)

    def draw_foreground(self, surface: pygame.Surface) -> None:
        if self.battle is not None:
            self.battle.draw_foreground(surface)
        else:
            self.renderer.foreground(surface, self.controller)
            if self.menus.opened:
                self.menu_renderer.draw(surface, self.menus)
