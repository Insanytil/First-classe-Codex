"""Scénarios métier sans Pygame : invariants, progression et conservation d'objets."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace

import pytest

from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition, ProgressionRules
from JRPG.domain.errors import (
    CharacterKnockedOut,
    DomainError,
    IncompatibleEquipment,
    InsufficientMana,
    InvalidQuantity,
    MissingItem,
)
from JRPG.domain.items import EquipmentSlot, Inventory, ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats, StatModifiers

BASE = CharacterStats(100, 20, 10, 10, 10, 10, 10)
JOBS = tuple(
    ClassDefinition(name, name.title(), BASE, growth)
    for name, growth in (
        ("warrior", StatModifiers(hp=10, strength=2)),
        ("mage", StatModifiers(mp=5, magic=2)),
        ("healer", StatModifiers(mp=4, resistance=2)),
        ("thief", StatModifiers(speed=3, evasion=1)),
    )
)
SWORD = ItemDefinition(
    "sword",
    "Épée",
    ItemCategory.WEAPON,
    frozenset({EquipmentSlot.WEAPON}),
    frozenset({"warrior"}),
    StatModifiers(strength=5),
)
POTION = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)


def hero(identity: str = "hero", job: ClassDefinition = JOBS[0]) -> Character:
    return Character(CharacterDefinition(identity, identity.title(), job))


@pytest.mark.parametrize("job", JOBS)
def test_classes_are_data_and_characters_have_independent_state(job: ClassDefinition) -> None:
    first, second = hero("first", job), hero("second", job)
    first.lose_hp(20)
    first.spend_mana(5)
    first.gain_experience(100)
    assert (second.hp, second.mp, second.level) == (100, 20, 1)
    assert first.base_stats == BASE.modified(job.growth)
    assert (first.hp, first.mp) == (80, 15)
    with pytest.raises(FrozenInstanceError):
        job.name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("amount", [-1, 0, True, 1.5])
def test_invalid_quantities_are_rejected_without_mutation(amount: int) -> None:
    bag = Inventory([ItemQuantity(POTION, 3)])
    with pytest.raises(InvalidQuantity):
        bag.remove(POTION, amount)
    assert bag.quantity(POTION.id) == 3


def test_inventory_stacks_and_missing_removal_are_atomic() -> None:
    bag = Inventory([ItemQuantity(POTION, 2)])
    bag.add(POTION, 3)
    before = bag.stacks
    with pytest.raises(MissingItem):
        bag.exchange((ItemQuantity(POTION, 1), ItemQuantity(SWORD, 1)), ())
    assert bag.stacks == before
    bag.remove(POTION, 5)
    assert bag.stacks == ()


def test_definition_conflict_does_not_change_inventory() -> None:
    bag = Inventory([ItemQuantity(SWORD, 1)])
    with pytest.raises(DomainError):
        bag.add(replace(SWORD, name="Conflicting sword"))
    assert bag.stacks == (ItemQuantity(SWORD, 1),)


def test_equipment_swap_and_unequip_conserve_objects() -> None:
    actor = hero()
    upgraded = replace(SWORD, id="steel", modifiers=StatModifiers(strength=12))
    bag = Inventory([ItemQuantity(SWORD, 1), ItemQuantity(upgraded, 1)])
    actor.equip(bag, SWORD, EquipmentSlot.WEAPON)
    assert actor.stats.strength == 15
    assert actor.base_stats.strength == 10
    actor.equip(bag, upgraded, EquipmentSlot.WEAPON)
    assert actor.stats.strength == 22
    assert (bag.quantity(SWORD.id), bag.quantity(upgraded.id)) == (1, 0)
    actor.unequip(bag, EquipmentSlot.WEAPON)
    assert actor.stats == BASE
    assert actor.equipment == ()
    assert bag.stacks == tuple(
        sorted((ItemQuantity(SWORD, 1), ItemQuantity(upgraded, 1)), key=lambda stack: stack.item.id)
    )


@pytest.mark.parametrize("failure", ["class", "slot", "missing"])
def test_rejected_equipment_preserves_both_aggregates(failure: str) -> None:
    actor = hero(job=JOBS[1] if failure == "class" else JOBS[0])
    bag = Inventory([] if failure == "missing" else [ItemQuantity(SWORD, 1)])
    before = bag.stacks, actor.equipment, actor.stats, actor.hp, actor.mp
    slot = EquipmentSlot.HEAD if failure == "slot" else EquipmentSlot.WEAPON
    with pytest.raises((IncompatibleEquipment, MissingItem)):
        actor.equip(bag, SWORD, slot)
    assert (bag.stacks, actor.equipment, actor.stats, actor.hp, actor.mp) == before


def test_unequip_conflict_is_atomic_and_empty_slot_is_rejected() -> None:
    actor = hero()
    bag = Inventory([ItemQuantity(SWORD, 1)])
    actor.equip(bag, SWORD, EquipmentSlot.WEAPON)
    bag.add(replace(SWORD, name="Conflicting"))
    before = actor.equipment, bag.stacks
    with pytest.raises(DomainError):
        actor.unequip(bag, EquipmentSlot.WEAPON)
    assert (actor.equipment, bag.stacks) == before
    with pytest.raises(IncompatibleEquipment):
        actor.unequip(bag, EquipmentSlot.HEAD)


def test_resource_caps_follow_equipment_without_free_healing() -> None:
    actor = hero()
    hat = ItemDefinition(
        "hat",
        "Chapeau",
        ItemCategory.ARMOR,
        frozenset({EquipmentSlot.HEAD}),
        modifiers=StatModifiers(hp=50, mp=20),
    )
    bag = Inventory([ItemQuantity(hat, 1)])
    actor.equip(bag, hat, EquipmentSlot.HEAD)
    assert (actor.hp, actor.mp) == (100, 20)
    actor.restore_hp(999)
    actor.restore_mana(999)
    assert (actor.hp, actor.mp) == (150, 40)
    actor.unequip(bag, EquipmentSlot.HEAD)
    assert (actor.hp, actor.mp) == (100, 20)


def test_equipment_bonuses_are_summed_before_clamping() -> None:
    actor = hero()
    negative = ItemDefinition(
        "curse",
        "Malus",
        ItemCategory.ACCESSORY,
        frozenset({EquipmentSlot.ACCESSORY_1}),
        modifiers=StatModifiers(strength=-50),
    )
    positive = replace(
        negative,
        id="blessing",
        slots=frozenset({EquipmentSlot.ACCESSORY_2}),
        modifiers=StatModifiers(strength=45),
    )
    bag = Inventory([ItemQuantity(negative, 1), ItemQuantity(positive, 1)])
    actor.equip(bag, negative, EquipmentSlot.ACCESSORY_1)
    actor.equip(bag, positive, EquipmentSlot.ACCESSORY_2)
    assert actor.stats.strength == 5


def test_mana_and_hp_bounds_and_ko_guard() -> None:
    actor = hero()
    with pytest.raises(InsufficientMana):
        actor.spend_mana(21)
    assert actor.mp == 20
    actor.spend_mana(20)
    actor.restore_mana(999)
    actor.lose_hp(999)
    assert actor.hp == 0
    operations: tuple[Callable[[], None], ...] = (
        lambda: actor.restore_hp(10),
        lambda: actor.spend_mana(0),
    )
    for operation in operations:
        with pytest.raises(CharacterKnockedOut):
            operation()
    assert (actor.hp, actor.mp) == (0, 20)


@pytest.mark.parametrize("amount", [-1, True, 1.5])
def test_invalid_resource_operations_leave_state_unchanged(amount: int) -> None:
    actor = hero()
    for operation in (
        actor.lose_hp,
        actor.restore_hp,
        actor.spend_mana,
        actor.restore_mana,
        actor.gain_experience,
    ):
        with pytest.raises(DomainError):
            operation(amount)
    assert (actor.hp, actor.mp, actor.level, actor.experience) == (100, 20, 1, 0)


def test_progression_thresholds_multiple_levels_and_cap() -> None:
    actor = Character(hero().definition, ProgressionRules(step=10, max_level=4))
    assert actor.gain_experience(9) == 0
    assert actor.gain_experience(1) == 1
    assert actor.gain_experience(50) == 2
    assert (actor.level, actor.experience, actor.base_stats.hp, actor.hp) == (4, 60, 130, 100)
    assert actor.gain_experience(999) == 0
    assert actor.experience == 60
    with pytest.raises(DomainError):
        ProgressionRules().threshold(100)


def test_party_uniqueness_capacity_order_and_leader() -> None:
    members = tuple(hero(str(index)) for index in range(5))
    party = Party(members[:4])
    before = party.members
    with pytest.raises(DomainError):
        party.add(members[4])
    assert party.members == before
    party.remove("3")
    with pytest.raises(DomainError):
        party.add(hero("0"))
    party.move("2", 0)
    assert party.leader is members[2]
    operations: tuple[Callable[[], None], ...] = (
        lambda: party.move("0", 99),
        lambda: party.remove("absent"),
    )
    for operation in operations:
        before = party.members
        with pytest.raises(DomainError):
            operation()
        assert party.members == before
    assert not party.all_knocked_out
    for member in party.members:
        member.lose_hp(999)
    assert party.all_knocked_out
    empty = Party()
    assert empty.leader is None and not empty.all_knocked_out


@pytest.mark.parametrize("field", ["hp", "mp", "strength", "speed", "accuracy"])
def test_stats_reject_invalid_values(field: str) -> None:
    with pytest.raises(DomainError):
        replace(BASE, **{field: -1})


def test_stat_bounds_and_invalid_definitions() -> None:
    assert BASE.modified(StatModifiers(hp=-999, mp=-999, accuracy=99, evasion=200)) == (
        replace(BASE, hp=1, mp=0, evasion=100)
    )
    for operation in (
        lambda: replace(BASE, critical=101),
        lambda: replace(BASE, hp=0),
        lambda: replace(JOBS[0], id=" "),
        lambda: replace(JOBS[0], growth=StatModifiers(hp=-1)),
        lambda: replace(SWORD, slots=frozenset()),
        lambda: replace(POTION, slots=frozenset({EquipmentSlot.WEAPON})),
    ):
        with pytest.raises(DomainError):
            operation()
