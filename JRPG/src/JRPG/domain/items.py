"""Définitions immuables, piles et échanges atomiques sans identité par potion."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from JRPG.domain.errors import DomainError, InvalidQuantity, MissingItem
from JRPG.domain.stats import StatModifiers, require_text


class ItemCategory(StrEnum):
    CONSUMABLE = "consumable"
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    QUEST = "quest"
    MATERIAL = "material"
    SPECIAL = "special"


class Rarity(StrEnum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class EquipmentSlot(StrEnum):
    WEAPON = "weapon"
    OFF_HAND = "off_hand"
    HEAD = "head"
    BODY = "body"
    ACCESSORY_1 = "accessory_1"
    ACCESSORY_2 = "accessory_2"


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    id: str
    name: str
    category: ItemCategory
    slots: frozenset[EquipmentSlot] = frozenset()
    allowed_classes: frozenset[str] = frozenset()
    modifiers: StatModifiers = StatModifiers()
    rarity: Rarity = Rarity.COMMON

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        if not isinstance(self.modifiers, StatModifiers):
            raise DomainError("Modificateurs invalides.")
        object.__setattr__(self, "slots", frozenset(self.slots))
        object.__setattr__(self, "allowed_classes", frozenset(self.allowed_classes))
        if not isinstance(self.rarity, Rarity):
            raise DomainError("Rareté inconnue.")
        if not isinstance(self.category, ItemCategory):
            raise DomainError("Catégorie inconnue.")
        if any(not isinstance(slot, EquipmentSlot) for slot in self.slots):
            raise DomainError("Emplacement inconnu.")
        equipment = self.category in {
            ItemCategory.WEAPON,
            ItemCategory.ARMOR,
            ItemCategory.ACCESSORY,
        }
        if equipment != bool(self.slots):
            raise DomainError("Seul un équipement déclare des emplacements, au moins un.")
        for class_id in self.allowed_classes:
            require_text(class_id)


@dataclass(frozen=True, slots=True)
class ItemQuantity:
    item: ItemDefinition
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.item, ItemDefinition):
            raise DomainError("Définition d’objet invalide.")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise InvalidQuantity("Quantité entière strictement positive attendue.")


class Inventory:
    def __init__(self, stacks: Iterable[ItemQuantity] = ()) -> None:
        self._stacks: dict[str, ItemQuantity] = {}
        self.exchange((), stacks)

    @property
    def stacks(self) -> tuple[ItemQuantity, ...]:
        return tuple(self._stacks[key] for key in sorted(self._stacks))

    def quantity(self, item_id: str) -> int:
        stack = self._stacks.get(item_id)
        return stack.quantity if stack else 0

    def add(self, item: ItemDefinition, quantity: int = 1) -> None:
        self.exchange((), (ItemQuantity(item, quantity),))

    def remove(self, item: ItemDefinition, quantity: int = 1) -> None:
        self.exchange((ItemQuantity(item, quantity),), ())

    def exchange(self, removed: Iterable[ItemQuantity], added: Iterable[ItemQuantity]) -> None:
        """Valider une copie puis publier l'état complet, sans rollback fragile."""
        candidate = self._stacks.copy()
        definitions = {key: stack.item for key, stack in candidate.items()}
        for sign, changes in ((-1, tuple(removed)), (1, tuple(added))):
            for change in changes:
                item = change.item
                if item.id in definitions and definitions[item.id] != item:
                    raise DomainError(f"Définitions contradictoires : {item.id}")
                definitions[item.id] = item
                old = candidate.get(item.id)
                quantity = (old.quantity if old else 0) + sign * change.quantity
                if quantity < 0:
                    raise MissingItem(item.id)
                if quantity:
                    candidate[item.id] = ItemQuantity(item, quantity)
                else:
                    candidate.pop(item.id, None)
        self._stacks = candidate
