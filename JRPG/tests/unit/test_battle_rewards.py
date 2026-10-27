"""Règlement atomique et idempotent ; tirages pondérés à graine fixe."""

from dataclasses import replace

import pytest

from JRPG.application.battle_session import BattleSession
from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition
from JRPG.domain.combat.ai import BasicAI
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.effects import Heal
from JRPG.domain.combat.model import (
    Ability,
    Action,
    BattleCommand,
    BattleRuleError,
    BattleState,
    Combatant,
    Consumable,
    Outcome,
    Side,
    TargetRule,
    TargetSide,
)
from JRPG.domain.combat.rewards import LootEntry, RewardTable
from JRPG.domain.errors import DomainError
from JRPG.domain.items import Inventory, ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats
from JRPG.domain.wallet import Wallet
from JRPG.infrastructure.random_source import SeededRandom

POTION = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)
STATS = CharacterStats(100, 20, 40, 5, 10, 5, 20)


def setup_session(
    rewards: RewardTable | None = None,
) -> tuple[BattleSession, Battle, Character, Party, Inventory, Wallet]:
    actor = Character(
        CharacterDefinition("a", "Ari", ClassDefinition("warrior", "Guerrier", STATS))
    )
    party, inventory, wallet = Party([actor]), Inventory([ItemQuantity(POTION, 2)]), Wallet(10)
    enemy = Combatant("z", "Loup", Side.ENEMIES, replace(STATS, hp=30), 30, 20)
    battle = Battle("encounter-1", (Combatant.from_character(actor), enemy), items=inventory.stacks)
    return (
        BattleSession(battle, party, inventory, wallet, rewards),
        battle,
        actor,
        party,
        inventory,
        wallet,
    )


def win(battle: Battle) -> None:
    battle.start()
    actor = battle.prepare_turn()
    battle.execute(BattleCommand(actor.id, battle.turn_id, Action.ATTACK, ("z",)), SeededRandom(2))
    assert battle.outcome == Outcome.VICTORY


def test_rewards_once_even_with_repeated_settlement_and_second_session() -> None:
    table = RewardTable(
        120, 25, (ItemQuantity(POTION, 1),), (LootEntry(1, ItemQuantity(POTION, 2)),)
    )
    session, battle, actor, party, bag, wallet = setup_session(table)
    second = BattleSession(battle, party, bag, wallet, table)
    win(battle)
    result = session.settle(SeededRandom(7))
    assert (actor.experience, actor.level, bag.quantity(POTION.id), wallet.gold) == (120, 2, 5, 35)
    assert result.levels_gained == (("a", 1),)
    assert session.settle(SeededRandom(8)) is result
    with pytest.raises(BattleRuleError):
        second.settle(SeededRandom(8))
    assert (actor.experience, bag.quantity(POTION.id), wallet.gold) == (120, 5, 35)


def test_reward_conflict_rejects_before_any_resource_or_xp_changes() -> None:
    table = RewardTable(100, 50, (ItemQuantity(replace(POTION, name="Conflicting"), 1),))
    session, battle, actor, _, bag, wallet = setup_session(table)
    win(battle)
    before = actor.hp, actor.mp, actor.experience, bag.stacks, wallet.gold
    with pytest.raises(DomainError):
        session.settle(SeededRandom(7))
    assert (actor.hp, actor.mp, actor.experience, bag.stacks, wallet.gold) == before
    assert not battle.settled


@pytest.mark.parametrize("change", ["inventory", "wallet", "character", "party"])
def test_stale_state_rejects_settlement_without_overwriting_user_changes(change: str) -> None:
    session, battle, actor, party, bag, wallet = setup_session()
    win(battle)
    if change == "inventory":
        bag.add(POTION)
    elif change == "wallet":
        wallet.credit(1)
    elif change == "character":
        actor.lose_hp(1)
    else:
        party.remove(actor.id)
    before = actor.hp, actor.experience, bag.stacks, wallet.gold, party.members
    with pytest.raises(BattleRuleError):
        session.settle(SeededRandom(7))
    assert (actor.hp, actor.experience, bag.stacks, wallet.gold, party.members) == before


def test_unfinished_battle_cannot_be_settled() -> None:
    session, _, _, _, _, _ = setup_session()
    with pytest.raises(BattleRuleError):
        session.settle(SeededRandom())


def test_flee_settles_consumption_and_hp_but_awards_nothing() -> None:
    actor = Character(
        CharacterDefinition("a", "Ari", ClassDefinition("warrior", "Guerrier", STATS))
    )
    actor.lose_hp(50)
    inventory = Inventory([ItemQuantity(POTION, 2)])
    wallet = Wallet()
    healing = Ability("potion", "Potion", 0, TargetRule(TargetSide.ALLY), (Heal(20),))
    enemy = Combatant("z", "Loup", Side.ENEMIES, STATS, 100, 20)
    battle = Battle(
        "flee",
        (Combatant.from_character(actor), enemy),
        consumables=(Consumable(POTION, healing),),
        items=inventory.stacks,
        flee_chance=100,
    )
    session = BattleSession(battle, Party([actor]), inventory, wallet, RewardTable(999, 999))
    battle.start()
    battle.prepare_turn()
    battle.execute(
        BattleCommand("a", battle.turn_id, Action.ITEM, ("a",), item_id="potion"), SeededRandom(1)
    )
    battle.prepare_turn()
    battle.execute(BattleCommand("z", battle.turn_id, Action.PASS), SeededRandom(1))
    battle.prepare_turn()
    battle.execute(BattleCommand("a", battle.turn_id, Action.FLEE), SeededRandom(1))
    session.settle(SeededRandom(1))
    assert (actor.hp, actor.experience, inventory.quantity("potion"), wallet.gold) == (70, 0, 1, 0)


def test_defeat_awards_no_loot_and_keeps_ko_resources() -> None:
    session, battle, actor, _, bag, wallet = setup_session(RewardTable(999, 999))
    battle.start()
    battle.prepare_turn()
    random = SeededRandom(4)
    while battle.state != BattleState.FINISHED:
        current = battle.current
        assert current is not None
        action = Action.PASS if current.side == Side.ALLIES else Action.ATTACK
        targets = () if action == Action.PASS else ("a",)
        result = battle.execute(BattleCommand(current.id, battle.turn_id, action, targets), random)
        if result.outcome is None:
            battle.prepare_turn()
    session.settle(random)
    assert (battle.outcome, actor.hp, actor.experience, wallet.gold) == (Outcome.DEFEAT, 0, 0, 10)
    assert bag.quantity("potion") == 2


def test_weighted_loot_with_no_drop_and_guaranteed_entries_is_deterministic() -> None:
    table = RewardTable(
        10, 2, (ItemQuantity(POTION, 1),), (LootEntry(3), LootEntry(1, ItemQuantity(POTION, 2))), 10
    )
    first, second = SeededRandom(123), SeededRandom(123)
    assert tuple(table.roll(first) for _ in range(10)) == tuple(
        table.roll(second) for _ in range(10)
    )
    assert RewardTable().roll(SeededRandom(1)).items == ()
    with pytest.raises(DomainError):
        LootEntry(0)
    with pytest.raises(DomainError):
        RewardTable(experience=-1)


def test_full_battle_is_deterministic_for_fixed_seed() -> None:
    first = setup_session(RewardTable(100, 25))
    second = setup_session(RewardTable(100, 25))
    for session, battle, _, _, _, _ in (first, second):
        random = SeededRandom(28)
        battle.start()
        for _ in range(100):
            battle.prepare_turn()
            battle.execute(BasicAI().choose(battle, random), random)
            if battle.state == BattleState.FINISHED:
                break
        assert battle.state == BattleState.FINISHED
        session.settle(random)
    assert first[1].journal == second[1].journal
    assert first[2].experience == second[2].experience
    assert first[4].stacks == second[4].stacks


def test_learning_and_resource_application_preserve_character_invariants() -> None:
    _, _, actor, _, _, _ = setup_session()
    actor.learn_skill("fire")
    actor.learn_skill("fire")
    assert actor.skills == ("fire",)
    with pytest.raises(DomainError):
        actor.set_resources(101, 0)
    assert (actor.hp, actor.mp) == (100, 20)
    actor.set_resources(0, 0)
    assert actor.is_knocked_out
