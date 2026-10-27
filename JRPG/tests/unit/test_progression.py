"""Quêtes, dialogues et économie : refus sans changement et récompenses uniques."""

from collections.abc import Callable
from dataclasses import replace

import pytest

from JRPG.application.progression import Conversation
from JRPG.domain.dialogues import StoryEffect, StoryOperation
from JRPG.domain.economy import Shop, ShopOffer
from JRPG.domain.errors import DomainError
from JRPG.domain.items import EquipmentSlot, Inventory, ItemCategory, ItemDefinition
from JRPG.domain.quests import Objective, QuestBook, QuestDefinition, QuestStatus
from JRPG.domain.wallet import Wallet
from JRPG.domain.world import WorldEvent, WorldEventKind, WorldState
from JRPG.infrastructure.world_content import create_exploration_session

ITEM = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)


def test_quest_facts_deduplicate_and_preexisting_facts_complete_on_acceptance() -> None:
    objective = Objective(
        "visit", "Visiter les lieux", WorldEventKind.MAP_ENTERED, frozenset({"a", "b"}), 2
    )
    definition = QuestDefinition("travel", "Voyage", "Visiter deux cartes.", (objective,))
    state = WorldState(visited_maps=frozenset({"a"}))
    book = QuestBook((definition,), state)
    book.accept("travel")
    for _ in range(3):
        book.observe(WorldEvent(WorldEventKind.MAP_ENTERED, "a"))
    assert book.progress(objective) == 1 and book.status("travel") == QuestStatus.ACTIVE
    book.observe(WorldEvent(WorldEventKind.MAP_ENTERED, "b"))
    assert book.status("travel") == QuestStatus.COMPLETED
    book.claim("travel")
    with pytest.raises(DomainError):
        book.claim("travel")
    preexisting = QuestBook((definition,), WorldState(visited_maps=frozenset({"a", "b"})))
    preexisting.accept("travel")
    assert preexisting.status("travel") == QuestStatus.COMPLETED


def test_prerequisites_unlock_only_after_reward_and_cycles_are_rejected() -> None:
    objective = Objective("x", "Parler", WorldEventKind.NPC_SPOKEN, frozenset({"npc"}))
    first = QuestDefinition("a", "A", "Premier voyage.", (objective,))
    second = replace(first, id="b", prerequisites=("a",))
    book = QuestBook((second, first), WorldState(talked_to=frozenset({"npc"})))
    with pytest.raises(DomainError):
        book.accept("b")
    book.accept("a")
    assert book.status("b") == QuestStatus.LOCKED
    book.claim("a")
    assert book.status("b") == QuestStatus.AVAILABLE
    with pytest.raises(DomainError):
        QuestBook((replace(first, prerequisites=("b",)), second), WorldState())
    with pytest.raises(DomainError):
        QuestBook((first,), WorldState(), (("a", QuestStatus.REWARDED),))


def test_compound_dialogue_reward_failure_is_atomic() -> None:
    session = create_exploration_session()
    story = session.story
    assert story is not None
    story.apply((StoryEffect(StoryOperation.ACCEPT_QUEST, "road"),))
    for kind, identity in (
        (WorldEventKind.MAP_ENTERED, "forest"),
        (WorldEventKind.ENCOUNTER_CLEARED, "forest_wolves"),
    ):
        session.world.state.record(kind, identity)
        story.observe(WorldEvent(kind, identity))
    before = (
        session.inventory.stacks,
        session.wallet.gold,
        tuple(member.snapshot() for member in session.party.members),
        story.quests.states,
    )
    claim = StoryEffect(StoryOperation.CLAIM_QUEST, "road")
    with pytest.raises(DomainError):
        story.apply((claim, claim))
    assert (
        session.inventory.stacks,
        session.wallet.gold,
        tuple(member.snapshot() for member in session.party.members),
        story.quests.states,
    ) == before
    story.apply((claim,))
    assert session.wallet.gold == 30
    assert story.quests.status("road") == QuestStatus.REWARDED
    with pytest.raises(DomainError):
        story.apply((claim,))
    assert session.wallet.gold == 30


def test_dialogue_conditions_hide_invalid_choices_and_rest_is_explicit() -> None:
    session = create_exploration_session()
    story = session.story
    assert story is not None
    definition = story.dialogue_for("mira_village")
    assert definition is not None
    conversation = Conversation(story, definition)
    assert "accept_road" in {choice.id for choice in conversation.choices}
    with pytest.raises(DomainError):
        conversation.choose("claim_sanctuary")
    conversation.choose("accept_road")
    assert "accept_road" not in {choice.id for choice in conversation.choices}
    member = session.party.members[0]
    member.lose_hp(20)
    conversation.choose("rest")
    assert member.hp == member.stats.hp
    conversation.choose("leave")
    assert conversation.node is None


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5])
def test_shop_rejects_invalid_quantities_without_mutating_any_owner(quantity: int) -> None:
    shop, bag, wallet = (
        Shop("shop", "Boutique", (ShopOffer(ITEM, 10, 4, 3),)),
        Inventory(),
        Wallet(30),
    )
    before = bag.stacks, wallet.gold, shop.stock
    with pytest.raises(DomainError):
        shop.buy(ITEM.id, quantity, bag, wallet)
    assert (bag.stacks, wallet.gold, shop.stock) == before


def test_shop_transactions_conserve_stock_and_money_and_reject_impossible_sales() -> None:
    shop, bag, wallet = (
        Shop("shop", "Boutique", (ShopOffer(ITEM, 10, 4, 2),)),
        Inventory(),
        Wallet(20),
    )
    shop.buy(ITEM.id, 2, bag, wallet)
    assert (bag.quantity(ITEM.id), wallet.gold, dict(shop.stock)[ITEM.id]) == (2, 0, 0)
    before = bag.stacks, wallet.gold, shop.stock
    with pytest.raises(DomainError):
        shop.buy(ITEM.id, 1, bag, wallet)
    assert (bag.stacks, wallet.gold, shop.stock) == before
    shop.sell(ITEM.id, 1, bag, wallet)
    assert (bag.quantity(ITEM.id), wallet.gold, dict(shop.stock)[ITEM.id]) == (1, 4, 1)
    operations: tuple[Callable[[], None], ...] = (
        lambda: shop.sell(ITEM.id, 2, bag, wallet),
        lambda: shop.buy(ITEM.id, 1, bag, wallet),
    )
    for operation in operations:
        before = bag.stacks, wallet.gold, shop.stock
        with pytest.raises(DomainError):
            operation()
        assert (bag.stacks, wallet.gold, shop.stock) == before


def test_equipment_comparison_is_read_only_and_restore_keeps_resources_and_identity() -> None:
    session = create_exploration_session()
    story = session.story
    assert story is not None
    member = session.party.members[0]
    upgraded = story.content.item("steel_sword")
    before = member.snapshot(), session.inventory.stacks
    assert (
        member.stats_with_equipment(EquipmentSlot.WEAPON, upgraded).strength > member.stats.strength
    )
    assert (member.snapshot(), session.inventory.stacks) == before
    session.inventory.add(upgraded)
    member.equip(session.inventory, upgraded, EquipmentSlot.WEAPON)
    snapshot = member.snapshot()
    member.lose_hp(10)
    member.apply_state(snapshot)
    assert member.snapshot() == snapshot
    with pytest.raises(DomainError):
        member.apply_state(replace(snapshot, hp=99999))
    assert member.snapshot() == snapshot


def test_invalid_prices_unknown_goods_and_counterfeit_definitions_cannot_change_money() -> None:
    with pytest.raises(DomainError):
        ShopOffer(ITEM, 5, 6, 1)
    offer = ShopOffer(ITEM, 10, 4, 2)
    with pytest.raises(DomainError):
        Shop("shop", "Boutique", (offer, offer))
    shop = Shop("shop", "Boutique", (offer,))
    wallet = Wallet(30)
    bag = Inventory()
    bag.add(replace(ITEM, name="Définition contradictoire"))
    before = bag.stacks, wallet.gold, shop.stock
    with pytest.raises(DomainError):
        shop.buy("potion", 1, bag, wallet)
    with pytest.raises(DomainError):
        shop.sell("unknown", 1, bag, wallet)
    with pytest.raises(DomainError):
        wallet.debit(31)
    assert (bag.stacks, wallet.gold, shop.stock) == before
