"""Accès aux nouvelles quêtes, rencontres, objets et sauvegardes de contenu 3."""

from unittest.mock import patch

import pygame
import pytest

from JRPG.application.consumables import use_consumable
from JRPG.application.exploration import ExplorationSession
from JRPG.application.progression import Conversation
from JRPG.domain.combat.model import Action, BattleCommand, EventKind, Side, StatusKind
from JRPG.domain.quests import QuestKind, QuestStatus
from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
from JRPG.infrastructure.world_content import create_exploration_session
from JRPG.presentation.battle_controller import BattleController, Playback
from JRPG.presentation.battle_scene import BattleScene
from JRPG.presentation.game_menu import GameMenu, MenuPage
from tests.world_helpers import finish_battle, walk_to


def choose(session: ExplorationSession, npc: str, choice: str) -> None:
    walk_to(session, npc)
    session.interact()
    assert session.story is not None
    definition = session.story.dialogue_for(npc)
    assert definition is not None
    Conversation(session.story, definition).choose(choice)


def travel(session: ExplorationSession, portal: str) -> None:
    walk_to(session, portal)
    session.interact()


def test_three_secondary_quests_can_be_finished_and_loaded_without_duplicate_rewards() -> None:
    session = create_exploration_session()
    choose(session, "village_herbalist", "accept")
    choose(session, "mira_village", "accept_road")
    travel(session, "village_to_forest")
    choose(session, "forest_traveler", "accept")
    for identity in ("forest_herb_cache", "forest_chest"):
        walk_to(session, identity)
        session.interact()
    choose(session, "forest_traveler", "claim")
    walk_to(session, "forest_wolves")
    session.interact()
    finish_battle(session, guard=True)
    session.finish_encounter()
    travel(session, "forest_to_village")
    choose(session, "village_herbalist", "claim")
    choose(session, "mira_village", "claim_road")
    choose(session, "mira_village", "rest")
    for identity in ("forest_ravens", "forest_briar"):
        travel(session, "village_to_forest")
        walk_to(session, identity)
        session.interact()
        finish_battle(session, guard=True)
        assert session.finish_encounter().outcome == "victory"
        travel(session, "forest_to_village")
        choose(session, "mira_village", "rest")
    travel(session, "village_to_forest")
    travel(session, "forest_to_ruins")
    # Les deux menaces déjà vaincues comptent avant l'acceptation de cette quête.
    choose(session, "ruins_scholar", "accept_grove")
    walk_to(session, "ruins_wisps")
    session.interact()
    finish_battle(session, guard=True)
    assert session.finish_encounter().outcome == "victory"
    choose(session, "ruins_scholar", "claim_grove")
    assert session.story is not None
    assert len(session.story.content.items) == 15
    assert sum(bool(item.slots) for item in session.story.content.items) == 10
    side = [quest for quest in session.story.content.quests if quest.kind == QuestKind.SIDE]
    assert len(side) == 3
    assert all(session.story.quests.status(quest.id) == QuestStatus.REWARDED for quest in side)
    mapper = GameSnapshotMapper()
    snapshot = mapper.capture(session)
    restored = mapper.restore(snapshot)
    assert mapper.capture(restored) == snapshot
    before = mapper.capture(restored)
    with pytest.raises(ValueError):
        choose(restored, "ruins_scholar", "claim_grove")
    # Seul l'événement de conversation transitoire peut être ajouté ; aucun gain répété.
    assert mapper.capture(restored) == before


def test_ether_restores_mana_outside_combat_and_antidote_has_clear_context() -> None:
    session = create_exploration_session()
    assert session.story is not None
    lyra = next(hero for hero in session.party.members if hero.id == "lyra")
    lyra.spend_mana(30)
    session.inventory.add(session.story.content.item("ether"))
    session.inventory.add(session.story.content.item("antidote"))
    use_consumable(session, "ether", "lyra")
    assert lyra.mp == lyra.stats.mp - 5
    assert session.inventory.quantity("ether") == 0
    before = lyra.snapshot(), session.inventory.stacks
    with pytest.raises(ValueError, match="hors combat"):
        use_consumable(session, "antidote", "lyra")
    assert (lyra.snapshot(), session.inventory.stacks) == before
    menu = GameMenu(session, None, lambda loaded: None)
    menu.open(MenuPage.INVENTORY)
    entry = next(entry for entry in menu.entries if entry.id == "antidote")
    assert entry.reason == "Utilisable uniquement en combat."


def test_antidote_in_real_battle_removes_poison_and_consumes_one_unit() -> None:
    session = create_exploration_session()
    assert session.story is not None
    session.inventory.add(session.story.content.item("antidote"))
    encounter = session.encounter_factory.create(
        "antidote_test", ("slime",), session.party, session.inventory, session.wallet
    )
    battle = encounter.battle
    battle.start()
    poisoned = False
    for _ in range(20):
        actor = battle.prepare_turn()
        if actor.side == Side.ENEMIES:
            command = next(
                c
                for c in battle.legal_commands()
                if c.ability_id == "venom" and c.targets == ("ari",)
            )
            battle.execute(command, encounter.random)
            poisoned = True
        elif poisoned:
            before = next(f for f in battle.combatants if f.id == "ari")
            assert before.has_status(StatusKind.POISON)
            command = BattleCommand(
                actor.id, battle.turn_id, Action.ITEM, ("ari",), item_id="antidote"
            )
            result = battle.execute(command, encounter.random)
            assert any(event.kind == EventKind.STATUS_EXPIRED for event in result.events)
            assert not next(f for f in battle.combatants if f.id == "ari").has_status(
                StatusKind.POISON
            )
            assert not any(stack.item.id == "antidote" for stack in battle.items)
            break
        else:
            battle.execute(BattleCommand(actor.id, battle.turn_id, Action.PASS), encounter.random)
    else:
        pytest.fail("Le consommable n'a pas été testé après application du poison.")


@pytest.mark.parametrize("kind", ["wisp", "briar", "raven"])
def test_new_creature_reaches_its_action_contact_frame(kind: str) -> None:
    pygame.font.init()
    session = create_exploration_session()
    encounter = session.encounter_factory.create(
        "new_art", (kind,), session.party, session.inventory, session.wallet
    )
    controller = BattleController(encounter)
    scene = BattleScene(lambda: controller)
    for _ in range(20):
        if controller.encounter.battle.current is not None and not controller.accepting_input:
            scene.update(0.35)
            break
        if controller.accepting_input:
            controller.select(5)
        scene.update(Playback.DURATION)
    assert controller.playback is not None
    scene.update(Playback.IMPACT)
    with patch.object(
        scene.renderer._monsters, "draw", wraps=scene.renderer._monsters.draw
    ) as draw:
        scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    frame = next(call.args[3] for call in draw.call_args_list if call.args[1] == kind)
    assert frame == 8  # Quatre attentes, puis la cinquième pose de l'attaque.


def test_ether_uses_the_real_combat_menu_and_reports_mana() -> None:
    pygame.font.init()
    session = create_exploration_session()
    assert session.story is not None
    nox = next(hero for hero in session.party.members if hero.id == "nox")
    nox.spend_mana(10)
    session.inventory.add(session.story.content.item("ether"))
    encounter = session.encounter_factory.create(
        "mana_ui", ("briar",), session.party, session.inventory, session.wallet
    )
    controller = BattleController(encounter)
    scene = BattleScene(lambda: controller)
    controller.select(3)
    controller.select(
        next(
            index
            for index, option in enumerate(controller.options)
            if option.commands[0].item_id == "ether"
        )
    )
    controller.click_target("nox")
    scene.update(Playback.IMPACT)
    scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    assert any("récupère 10 PM" in line for line in controller.log)
    assert not any(stack.item.id == "ether" for stack in encounter.battle.items)
