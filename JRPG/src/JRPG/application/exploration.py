"""Cas d'utilisation de l'exploration et passage vers le combat existant."""

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from JRPG.application.battle_session import SettlementResult
from JRPG.application.encounter import BattleEncounter
from JRPG.application.progression import AdventureProgress
from JRPG.application.save_data import RandomCheckpoint
from JRPG.domain.combat.model import Ability, Consumable, Outcome
from JRPG.domain.errors import DomainError
from JRPG.domain.items import Inventory
from JRPG.domain.party import Party
from JRPG.domain.wallet import Wallet
from JRPG.domain.world import MapObject, ObjectKind, World, WorldEventKind


class EncounterFactory(Protocol):
    @property
    def abilities(self) -> tuple[Ability, ...]: ...
    @property
    def consumables(self) -> tuple[Consumable, ...]: ...

    def create(
        self,
        identity: str,
        enemies: tuple[str, ...],
        party: Party,
        inventory: Inventory,
        wallet: Wallet,
    ) -> BattleEncounter: ...

    def checkpoint(self) -> RandomCheckpoint: ...
    def restore_checkpoint(self, checkpoint: RandomCheckpoint) -> None: ...


@dataclass(frozen=True, slots=True)
class InteractionResult:
    subject: MapObject
    message: str
    encounter: BattleEncounter | None = None


class ExplorationSession:
    def __init__(
        self,
        world: World,
        party: Party,
        inventory: Inventory,
        wallet: Wallet,
        encounters: EncounterFactory,
        story: AdventureProgress | None = None,
    ) -> None:
        if not party.members or party.all_knocked_out:
            raise DomainError("L'exploration nécessite un groupe conscient.")
        self.world, self.party, self.inventory, self.wallet = world, party, inventory, wallet
        self._factory = encounters
        self.story = story
        self.play_seconds = 0.0
        self._event_offset = len(world.state.events)
        self._active: BattleEncounter | None = None
        self._encounter_object: MapObject | None = None

    @property
    def encounter_factory(self) -> EncounterFactory:
        return self._factory

    @property
    def active_encounter(self) -> BattleEncounter | None:
        return self._active

    def move(self, dx: float, dy: float, elapsed: float) -> None:
        if self._active is not None:
            raise DomainError("Déplacement interdit pendant le combat.")
        self.world.move(dx, dy, elapsed)

    def _publish(self) -> None:
        if self.story is not None:
            for event in self.world.state.events[self._event_offset :]:
                self.story.observe(event)
        self._event_offset = len(self.world.state.events)

    def advance_time(self, elapsed: float) -> None:
        if not isfinite(elapsed) or elapsed < 0:
            raise DomainError("Durée de jeu invalide.")
        self.play_seconds += elapsed

    def interact(self) -> InteractionResult | None:
        result = self._interact()
        self._publish()
        return result

    def _interact(self) -> InteractionResult | None:
        if self._active is not None:
            raise DomainError("Interaction interdite pendant le combat.")
        subject = self.world.nearby()
        if subject is None:
            return None
        if subject.kind == ObjectKind.PORTAL:
            self.world.travel(subject)
            return InteractionResult(subject, f"Vous entrez dans {self.world.current_map.name}.")
        if subject.kind == ObjectKind.NPC:
            self.world.state.record(WorldEventKind.NPC_SPOKEN, subject.id)
            return InteractionResult(subject, subject.message)
        if subject.kind == ObjectKind.CHEST:
            if subject.id in self.world.state.opened_chests:
                return InteractionResult(subject, "Ce coffre est déjà vide.")
            candidate = Inventory(self.inventory.stacks)
            candidate.exchange((), subject.items)
            self.inventory.exchange((), subject.items)
            self.wallet.credit(subject.gold)
            self.world.state.record(WorldEventKind.CHEST_OPENED, subject.id)
            loot = ", ".join(f"{stack.quantity} {stack.item.name}" for stack in subject.items)
            return InteractionResult(
                subject, f"Coffre ouvert : {loot or 'aucun objet'}, {subject.gold} pièces."
            )
        if self.story is not None:
            reason = self.story.encounter_error(subject.id)
            if reason is not None:
                return InteractionResult(subject, reason)
        encounter = self._factory.create(
            subject.id, subject.enemies, self.party, self.inventory, self.wallet
        )
        self._active, self._encounter_object = encounter, subject
        return InteractionResult(subject, f"{subject.name} vous défient !", encounter)

    def finish_encounter(self) -> SettlementResult:
        if self._active is None or self._encounter_object is None:
            raise DomainError("Aucun combat à terminer.")
        result = self._active.session.settle(self._active.random)
        if result.outcome == Outcome.VICTORY:
            self.world.state.record(WorldEventKind.ENCOUNTER_CLEARED, self._encounter_object.id)
        elif result.outcome == Outcome.DEFEAT:
            # Point de reprise temporaire, sans système de sauvegarde ni pénalité économique.
            for member in self.party.members:
                member.set_resources(member.stats.hp, member.stats.mp)
            self.world.return_to_origin()
        self._active, self._encounter_object = None, None
        self._publish()
        return result
