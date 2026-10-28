"""Navigation et progression de la présentation, sans SDL ni horloge réelle."""

import pytest

from JRPG.application.battle_session import BattleSession
from JRPG.application.encounter import BattleEncounter
from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition
from JRPG.domain.combat.ai import BasicAI
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.effects import Damage, Heal
from JRPG.domain.combat.model import (
    Ability,
    Combatant,
    Consumable,
    EnemyDefinition,
    Outcome,
    TargetRule,
    TargetSide,
)
from JRPG.domain.items import Inventory, ItemCategory, ItemDefinition
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats
from JRPG.domain.wallet import Wallet
from JRPG.infrastructure.random_source import SeededRandom
from JRPG.infrastructure.training_encounter import create_training_encounter
from JRPG.presentation.battle_controller import BattleController, MenuMode, Playback


def controller() -> BattleController:
    return BattleController(create_training_encounter())


def assert_mode(view: BattleController, expected: MenuMode) -> None:
    assert view.mode == expected


def pass_to(view: BattleController, identity: str) -> None:
    for _ in range(20):
        actor = view.encounter.battle.current
        if actor is not None and actor.id == identity:
            return
        if view.accepting_input:
            view.select(5)
        view.update(1)
    raise AssertionError("Acteur non atteint.")


def test_target_selection_then_single_submission_with_animation_lock() -> None:
    view = controller()
    before = view.displayed
    view.select(0)
    assert_mode(view, MenuMode.TARGET)
    assert view.target_ids == ("wolf-1",)
    view.click_target("ari")
    assert view.playback is None
    view.confirm()
    after = view.encounter.battle.combatants
    assert view.playback is not None and after != before
    assert view.displayed == before
    journal = view.encounter.battle.journal
    for _ in range(5):
        view.confirm()
        view.select(0)
        view.click_target("wolf-1")
    assert view.encounter.battle.journal == journal
    view.update(Playback.IMPACT - 0.01)
    assert view.displayed == before
    view.update(0.02)
    assert view.displayed == after
    view.update(Playback.DURATION)
    assert view.playback is None and view.accepting_input
    assert view.encounter.battle.current is not None
    assert view.encounter.battle.current.id == "lyra"


def test_skill_menu_cancel_and_multiple_target_highlighting() -> None:
    view = controller()
    pass_to(view, "lyra")
    view.select(1)
    assert_mode(view, MenuMode.SKILL)
    assert "8 PM" in view.options[0].label
    view.select(
        next(
            index
            for index, option in enumerate(view.options)
            if option.commands and option.commands[0].ability_id == "storm"
        )
    )
    assert_mode(view, MenuMode.TARGET)
    assert len(view.target_ids) == 3
    view.back()
    assert_mode(view, MenuMode.SKILL)
    view.back()
    assert_mode(view, MenuMode.ACTION)
    view.select(1)
    view.select(
        next(
            index
            for index, option in enumerate(view.options)
            if option.commands and option.commands[0].ability_id == "storm"
        )
    )
    view.confirm()
    assert view.playback is not None
    assert view.playback.result.command.ability_id == "storm"
    assert len(view.playback.result.command.targets) == 3


def test_revival_disabled_until_a_ko_target_exists_and_items_are_counted() -> None:
    view = controller()
    pass_to(view, "mira")
    view.select(1)
    view.move(
        next(
            index
            for index, option in enumerate(view.options)
            if option.commands and option.commands[0].ability_id == "revive"
        )
    )
    assert "Résurrection" in view.options[view.selected].label
    assert view.options[view.selected].reason is not None
    before = view.encounter.battle.combatants
    view.confirm()
    assert view.playback is None and view.encounter.battle.combatants == before
    assert view.focus_hint
    view.back()
    view.select(3)
    assert_mode(view, MenuMode.ITEM)
    assert "×3" in view.options[0].label
    view.select(0)
    view.click_target("ari")
    assert view.playback is not None
    assert view.playback.result.command.item_id == "potion"
    assert (
        next(stack.quantity for stack in view.encounter.battle.items if stack.item.id == "potion")
        == 2
    )


def test_mana_and_exhausted_item_reasons_come_from_domain_validation() -> None:
    stats = CharacterStats(100, 10, 20, 5, 20, 5, 20)
    hero = Character(CharacterDefinition("a", "Mage", ClassDefinition("mage", "Mage", stats)))
    fire = Ability("fire", "Feu", 8, TargetRule(), (Damage(10),), True)
    hero.learn_skill(fire.id)
    hero.spend_mana(10)
    potion = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)
    consumable = Consumable(
        potion, Ability("heal", "Potion", 0, TargetRule(TargetSide.ALLY), (Heal(20),))
    )
    inventory, wallet = Inventory(), Wallet()
    enemy = EnemyDefinition("wolf", "Loup", stats).spawn("z")
    battle = Battle("reasons", (Combatant.from_character(hero), enemy), (fire,), (consumable,))
    session = BattleSession(battle, Party([hero]), inventory, wallet)
    view = BattleController(
        BattleEncounter(battle, session, SeededRandom(1), BasicAI(), (fire,), (consumable,))
    )
    assert view.options[1].reason == "PM insuffisants."
    assert view.options[3].reason == "Objet épuisé."
    before = battle.combatants, battle.journal, battle.turn_id
    view.select(1)
    assert view.message == "PM insuffisants."
    view.select(3)
    assert view.message == "Objet épuisé."
    assert (battle.combatants, battle.journal, battle.turn_id) == before


def test_enemy_turns_auto_advance_and_full_player_battle_settles_once() -> None:
    view = controller()
    seen_enemy = False
    for _ in range(300):
        if view.accepting_input:
            view.select(0)
            view.confirm()
        elif view.encounter.battle.current is not None and view.playback is None:
            seen_enemy = True
        view.update(1)
        if view.settlement is not None:
            break
    assert seen_enemy and view.settlement is not None
    assert view.settlement.outcome == Outcome.VICTORY
    before = view.encounter.battle.journal, view.settlement
    for _ in range(10):
        view.confirm()
        view.move(1)
        view.update(1)
    assert (view.encounter.battle.journal, view.settlement) == before
    assert len(view.log) <= 80


def test_navigation_wraps_and_rejects_negative_presentation_time() -> None:
    view = controller()
    view.move(-1)
    assert view.selected == 5
    view.move(1)
    assert view.selected == 0
    view.select(999)
    assert view.playback is None
    with pytest.raises(ValueError):
        view.update(-0.1)


def test_moving_off_a_disabled_choice_clears_its_error_message() -> None:
    view = controller()
    pass_to(view, "mira")
    view.select(1)
    view.move(
        next(
            index
            for index, option in enumerate(view.options)
            if option.commands and option.commands[0].ability_id == "revive"
        )
    )
    view.confirm()
    assert view.options[view.selected].reason is not None
    rejected = view.message
    view.move(-1)
    assert view.options[view.selected].reason is None
    assert view.focus_hint != rejected
