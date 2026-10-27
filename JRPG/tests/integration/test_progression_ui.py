"""Menus et conversations Pygame, avec sauvegardes de test explicitement injectées."""

from collections.abc import Iterator
from pathlib import Path

import pygame
import pytest

from JRPG.application.saves import SaveService
from JRPG.domain.quests import QuestStatus
from JRPG.domain.world import MapPosition
from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
from JRPG.infrastructure.save_repository import JsonSaveRepository
from JRPG.infrastructure.world_content import create_exploration_session
from JRPG.presentation.adventure_scene import AdventureScene
from JRPG.presentation.game_menu import GameMenu, MenuPage


@pytest.fixture(autouse=True)
def sdl() -> Iterator[None]:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    yield
    pygame.quit()


def key(scene: AdventureScene, value: int) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=value))


def draw(scene: AdventureScene) -> pygame.Surface:
    surface = pygame.Surface((640, 360), pygame.SRCALPHA)
    scene.draw_foreground(surface)
    return surface


def page(menu: GameMenu, expected: MenuPage) -> None:
    assert menu.page == expected


def test_dialogue_acceptance_changes_choices_and_journal_without_repeating_reward() -> None:
    scene = AdventureScene(
        create_exploration_session(position=MapPosition("village", 8.5 * 32, 8.5 * 32))
    )
    key(scene, pygame.K_e)
    assert scene.controller.conversation is not None
    draw(scene)
    key(scene, pygame.K_RETURN)
    story = scene.controller.session.story
    assert story is not None and story.quests.status("road") == QuestStatus.ACTIVE
    assert "accept_road" not in {entry.id for entry in scene.controller.conversation.choices}
    key(scene, pygame.K_BACKSPACE)
    key(scene, pygame.K_j)
    page(scene.menus, MenuPage.QUESTS)
    assert any("En cours" in entry.label for entry in scene.menus.entries)
    before = scene.controller.session.world.position
    key(scene, pygame.K_d)
    scene.update(1)
    assert scene.controller.session.world.position == before
    draw(scene)
    key(scene, pygame.K_TAB)
    assert not scene.menus.opened


def test_merchant_opens_shop_and_buy_sell_updates_stock_and_wallet() -> None:
    session = create_exploration_session(position=MapPosition("village", 25.5 * 32, 9.5 * 32))
    scene = AdventureScene(session)
    key(scene, pygame.K_e)
    key(scene, pygame.K_RETURN)
    assert scene.menus.opened and not scene.controller.dialogue
    page(scene.menus, MenuPage.SHOP)
    key(scene, pygame.K_RETURN)
    page(scene.menus, MenuPage.BUY)
    key(scene, pygame.K_RETURN)
    assert scene.menus.message == "Fonds insuffisants."
    session.wallet.credit(100)
    key(scene, pygame.K_RETURN)
    assert (session.wallet.gold, session.inventory.quantity("potion")) == (85, 4)
    key(scene, pygame.K_BACKSPACE)
    key(scene, pygame.K_DOWN)
    key(scene, pygame.K_RETURN)
    page(scene.menus, MenuPage.SELL)
    key(scene, pygame.K_RETURN)
    assert (session.wallet.gold, session.inventory.quantity("potion")) == (92, 3)
    assert session.story is not None
    assert dict(session.story.shops["oren"].stock)["potion"] == 8
    draw(scene)


def test_inventory_can_heal_and_revive_without_consuming_invalid_target() -> None:
    session = create_exploration_session()
    scene = AdventureScene(session)
    member = session.party.members[0]
    member.lose_hp(50)
    key(scene, pygame.K_i)
    potion = next(index for index, entry in enumerate(scene.menus.entries) if entry.id == "potion")
    scene.menus.choose(potion)
    page(scene.menus, MenuPage.ITEM_TARGET)
    scene.menus.choose(0)
    assert member.hp == member.stats.hp and session.inventory.quantity("potion") == 2
    phoenix = next(
        index for index, entry in enumerate(scene.menus.entries) if entry.id == "phoenix"
    )
    scene.menus.choose(phoenix)
    scene.menus.choose(0)
    assert "incompatible" in scene.menus.message
    assert session.inventory.quantity("phoenix") == 1
    member.lose_hp(99999)
    scene.menus.choose(0)
    assert member.hp == 40 and session.inventory.quantity("phoenix") == 0
    draw(scene)


def test_equipment_menu_compares_then_transfers_and_refuses_incompatible_class() -> None:
    session = create_exploration_session()
    assert session.story is not None
    steel = session.story.content.item("steel_sword")
    session.inventory.add(steel)
    scene = AdventureScene(session)
    scene.menus.open(MenuPage.EQUIPMENT_HERO)
    scene.menus.choose(0)
    scene.menus.choose(0)
    page(scene.menus, MenuPage.EQUIPMENT_ITEM)
    entry = next(
        index for index, entry in enumerate(scene.menus.entries) if entry.id == "steel_sword"
    )
    assert any("->" in line for line in scene.menus.entries[entry].details)
    before = session.party.members[0].stats.strength
    scene.menus.choose(entry)
    assert session.party.members[0].stats.strength > before
    assert session.inventory.quantity("steel_sword") == 0
    assert session.inventory.quantity("iron_sword") == 1
    scene.menus.choose(0)
    scene.menus.choose(0)
    assert session.inventory.quantity("steel_sword") == 1
    scene.menus.open(MenuPage.EQUIPMENT_HERO)
    scene.menus.choose(1)
    scene.menus.choose(0)
    index = next(
        index for index, entry in enumerate(scene.menus.entries) if entry.id == "steel_sword"
    )
    state = session.inventory.stacks, session.party.members[1].equipment
    scene.menus.choose(index)
    assert scene.menus.message == "Classe incompatible."
    assert (session.inventory.stacks, session.party.members[1].equipment) == state
    draw(scene)


def test_party_leader_and_character_sheets_are_available_via_mouse() -> None:
    scene = AdventureScene(create_exploration_session())
    key(scene, pygame.K_TAB)
    draw(scene)
    rect, index = scene.menu_renderer.hits[3]
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), rect.center)
    page(scene.menus, MenuPage.PARTY)
    scene.menus.choose(3)
    assert scene.controller.session.party.leader is not None
    assert scene.controller.session.party.leader.id == "nox"
    scene.menus.open(MenuPage.CHARACTERS)
    assert any("Précision" in line for line in scene.menus.entries[0].details)
    draw(scene)


def test_save_load_menus_replace_session_only_after_success(tmp_path: Path) -> None:
    session = create_exploration_session()
    service = SaveService(JsonSaveRepository(tmp_path), GameSnapshotMapper())
    scene = AdventureScene(session, service)
    key(scene, pygame.K_F5)
    page(scene.menus, MenuPage.SAVE)
    assert not list(tmp_path.iterdir())
    key(scene, pygame.K_RETURN)
    assert (tmp_path / "slot-1.json").is_file()
    assert "sauvegardée" in scene.menus.message
    session.wallet.credit(50)
    scene.menus.close()
    key(scene, pygame.K_F9)
    key(scene, pygame.K_RETURN)
    assert not scene.menus.opened
    assert scene.controller.session is not session
    assert scene.controller.session.wallet.gold == 0
    original = scene.controller.session
    (tmp_path / "slot-1.json").write_text("{", encoding="utf-8")
    key(scene, pygame.K_F9)
    key(scene, pygame.K_RETURN)
    assert scene.controller.session is original
    assert scene.menus.opened and "invalide" in scene.menus.message
    draw(scene)
