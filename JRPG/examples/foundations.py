"""Démonstration exécutable de phase 1, sans import ni initialisation Pygame."""

from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition
from JRPG.domain.items import EquipmentSlot, Inventory, ItemCategory, ItemDefinition
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats, StatModifiers


def main() -> None:
    warrior = ClassDefinition(
        "warrior",
        "Guerrier",
        CharacterStats(100, 20, 10, 10, 5, 5, 10),
        StatModifiers(hp=10, strength=2),
    )
    hero = Character(CharacterDefinition("hero", "Ari", warrior))
    party = Party([hero])
    inventory = Inventory()
    sword = ItemDefinition(
        "iron_sword",
        "Épée de fer",
        ItemCategory.WEAPON,
        frozenset({EquipmentSlot.WEAPON}),
        frozenset({"warrior"}),
        StatModifiers(strength=5),
    )
    inventory.add(sword)
    hero.equip(inventory, sword, EquipmentSlot.WEAPON)
    hero.gain_experience(300)
    print(f"{hero.definition.name} : niveau {hero.level}, force {hero.stats.strength}")
    print(f"PV {hero.hp}/{hero.stats.hp}, PM {hero.mp}/{hero.stats.mp}")
    print(f"Équipe : {len(party.members)}, épées dans le sac : {inventory.quantity(sword.id)}")
    hero.unequip(inventory, EquipmentSlot.WEAPON)
    print(f"Épée rendue au sac : {inventory.quantity(sword.id)}")


if __name__ == "__main__":
    main()
