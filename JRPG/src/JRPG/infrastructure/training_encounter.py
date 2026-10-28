"""Composition des rencontres depuis le catalogue ; exemple autonome conservé."""

from dataclasses import dataclass

from JRPG.application.battle_session import BattleSession
from JRPG.application.encounter import BattleEncounter
from JRPG.application.save_data import RandomCheckpoint
from JRPG.domain.characters import Character
from JRPG.domain.combat.ai import BasicAI, TelegraphedAI
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import Combatant
from JRPG.domain.combat.rewards import RewardTable
from JRPG.domain.items import Inventory
from JRPG.domain.party import Party
from JRPG.domain.wallet import Wallet
from JRPG.infrastructure.combat_content import CombatCatalog, load_combat_catalog
from JRPG.infrastructure.random_source import SeededRandom
from JRPG.infrastructure.validation import ContentError


@dataclass(frozen=True, slots=True)
class CombatSetup:
    party: Party
    inventory: Inventory
    wallet: Wallet
    factory: CatalogEncounterFactory


def create_combat_setup(seed: int = 7) -> CombatSetup:
    catalog = load_combat_catalog()
    heroes = []
    for template in catalog.heroes:
        hero = Character(template.definition)
        for skill in template.skills:
            hero.learn_skill(skill)
        heroes.append(hero)
    return CombatSetup(
        Party(heroes),
        Inventory(catalog.initial_items),
        Wallet(),
        CatalogEncounterFactory(catalog, SeededRandom(seed)),
    )


class CatalogEncounterFactory:
    def __init__(self, catalog: CombatCatalog, random: SeededRandom) -> None:
        self.abilities, self.consumables = catalog.abilities, catalog.consumables
        self.enemies = {enemy.id: enemy for enemy in catalog.enemies}
        self._profiles = {profile.id: profile for profile in catalog.profiles}
        self._enemy_profiles = dict(catalog.enemy_profiles)
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
        if not enemies or any(key not in self.enemies for key in enemies):
            raise ContentError("Rencontre vide ou ennemi inconnu.")
        profile_ids = {self._enemy_profiles[key] for key in enemies}
        if len(profile_ids) != 1:
            raise ContentError("Une rencontre doit partager un profil de combat et de récompenses.")
        profile = self._profiles[next(iter(profile_ids))]
        fighters = [Combatant.from_character(hero) for hero in party.members]
        counts: dict[str, int] = {}
        for key in enemies:
            counts[key] = counts.get(key, 0) + 1
            fighters.append(self.enemies[key].spawn(f"{key}-{counts[key]}"))
        battle = Battle(
            identity,
            tuple(fighters),
            self.abilities,
            self.consumables,
            inventory.stacks,
            allow_flee=profile.allow_flee,
        )
        rewards = RewardTable(
            profile.experience_per_enemy * len(enemies),
            profile.gold_per_enemy * len(enemies),
            profile.guaranteed,
            profile.weighted,
        )
        policy = TelegraphedAI(profile.telegraph) if profile.telegraph is not None else BasicAI()
        return BattleEncounter(
            battle,
            BattleSession(battle, party, inventory, wallet, rewards),
            self._random,
            policy,
            self.abilities,
            self.consumables,
        )


def create_training_encounter(seed: int = 7) -> BattleEncounter:
    setup = create_combat_setup(seed)
    return setup.factory.create(
        "training", ("wolf", "wolf", "slime"), setup.party, setup.inventory, setup.wallet
    )
