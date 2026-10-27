"""Données de la bataille de démonstration ; pas d'exploration ni de sauvegarde."""

from dataclasses import dataclass

from JRPG.application.battle_session import BattleSession
from JRPG.application.encounter import BattleEncounter
from JRPG.application.save_data import RandomCheckpoint
from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition
from JRPG.domain.combat.ai import BasicAI
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.effects import ApplyStatus, Damage, Heal, Revive
from JRPG.domain.combat.model import (
    Ability,
    Combatant,
    Consumable,
    Element,
    EnemyDefinition,
    Resistance,
    StatusDefinition,
    StatusKind,
    TargetLife,
    TargetRule,
    TargetSide,
)
from JRPG.domain.combat.rewards import LootEntry, RewardTable
from JRPG.domain.items import Inventory, ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats, StatModifiers
from JRPG.domain.wallet import Wallet
from JRPG.infrastructure.random_source import SeededRandom


def create_combat_setup(seed: int = 7) -> CombatSetup:
    poison = StatusDefinition("venom", StatusKind.POISON, 3, 7)
    strike = Ability("strike", "Frappe puissante", 6, TargetRule(), (Damage(24),))
    fire = Ability("fire", "Feu", 8, TargetRule(), (Damage(20, True, Element.FIRE),), True)
    storm = Ability(
        "storm",
        "Brasier collectif",
        20,
        TargetRule(multiple=True),
        (Damage(10, True, Element.FIRE),),
        True,
    )
    cure = Ability("cure", "Soin", 7, TargetRule(TargetSide.ALLY), (Heal(65),), True)
    revive = Ability(
        "revive",
        "Résurrection",
        15,
        TargetRule(TargetSide.ALLY, TargetLife.KO),
        (Revive(45),),
        True,
    )
    venom = Ability("venom", "Lame empoisonnée", 6, TargetRule(), (Damage(4), ApplyStatus(poison)))
    abilities = (strike, fire, storm, cure, revive, venom)
    heroes = []
    for identity, name, job, stats, skills in (
        ("ari", "Ari", "Guerrier", CharacterStats(180, 24, 26, 14, 6, 8, 16), (strike,)),
        ("lyra", "Lyra", "Mage", CharacterStats(110, 42, 10, 7, 27, 16, 18), (fire, storm)),
        ("mira", "Mira", "Soigneur", CharacterStats(130, 36, 13, 10, 18, 16, 14), (cure, revive)),
        ("nox", "Nox", "Voleur", CharacterStats(120, 24, 22, 9, 8, 8, 24, 100, 5, 15), (venom,)),
    ):
        character = Character(
            CharacterDefinition(
                identity,
                name,
                ClassDefinition(
                    job.lower(),
                    job,
                    stats,
                    StatModifiers(hp=8, mp=2, strength=1, defense=1, magic=1, resistance=1),
                ),
            )
        )
        for skill in skills:
            character.learn_skill(skill.id)
        heroes.append(character)
    wolf = EnemyDefinition(
        "wolf",
        "Loup des ruines",
        CharacterStats(95, 0, 22, 9, 4, 8, 12),
        resistances=(Resistance(Element.FIRE, 150),),
    )
    slime = EnemyDefinition(
        "slime",
        "Flan sylvestre",
        CharacterStats(120, 18, 18, 12, 15, 12, 8),
        (venom.id,),
        (Resistance(Element.FIRE, 50),),
    )
    potion = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)
    phoenix = ItemDefinition("phoenix", "Plume de vie", ItemCategory.CONSUMABLE)
    consumables = (
        Consumable(
            potion, Ability("potion_heal", "Potion", 0, TargetRule(TargetSide.ALLY), (Heal(60),))
        ),
        Consumable(
            phoenix,
            Ability(
                "phoenix_revive",
                "Plume de vie",
                0,
                TargetRule(TargetSide.ALLY, TargetLife.KO),
                (Revive(40),),
            ),
        ),
    )
    inventory = Inventory((ItemQuantity(potion, 3), ItemQuantity(phoenix, 1)))
    party, wallet = Party(heroes), Wallet()
    factory = DemoEncounterFactory(abilities, consumables, (wolf, slime), SeededRandom(seed))
    return CombatSetup(party, inventory, wallet, factory)


@dataclass(frozen=True, slots=True)
class CombatSetup:
    party: Party
    inventory: Inventory
    wallet: Wallet
    factory: DemoEncounterFactory


class DemoEncounterFactory:
    def __init__(
        self,
        abilities: tuple[Ability, ...],
        consumables: tuple[Consumable, ...],
        enemies: tuple[EnemyDefinition, ...],
        random: SeededRandom,
    ) -> None:
        self.abilities, self.consumables = abilities, consumables
        self.enemies = {enemy.id: enemy for enemy in enemies}
        self._random = random

    def checkpoint(self) -> RandomCheckpoint:
        return self._random.checkpoint()

    def restore_checkpoint(self, checkpoint: RandomCheckpoint) -> None:
        self._random.restore_checkpoint(checkpoint)

    def create(
        self,
        identity: str,
        enemies: tuple[str, ...],
        party: Party,
        inventory: Inventory,
        wallet: Wallet,
    ) -> BattleEncounter:
        fighters = [Combatant.from_character(hero) for hero in party.members]
        counts: dict[str, int] = {}
        for key in enemies:
            if key not in self.enemies:
                raise ValueError(f"Ennemi inconnu : {key}")
            counts[key] = counts.get(key, 0) + 1
            fighters.append(self.enemies[key].spawn(f"{key}-{counts[key]}"))
        battle = Battle(
            identity, tuple(fighters), self.abilities, self.consumables, inventory.stacks
        )
        potion = next(entry.item for entry in self.consumables if entry.item.id == "potion")
        rewards = RewardTable(
            40 * len(enemies),
            15 * len(enemies),
            (ItemQuantity(potion, 1),),
            (LootEntry(2), LootEntry(1, ItemQuantity(potion, 1))),
        )
        return BattleEncounter(
            battle,
            BattleSession(battle, party, inventory, wallet, rewards),
            self._random,
            BasicAI(),
            self.abilities,
            self.consumables,
        )


def create_training_encounter(seed: int = 7) -> BattleEncounter:
    setup = create_combat_setup(seed)
    return setup.factory.create(
        "training", ("wolf", "wolf", "slime"), setup.party, setup.inventory, setup.wallet
    )
