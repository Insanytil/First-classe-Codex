"""Effets composables : aucune branche sur le nom d'une compétence."""

from dataclasses import dataclass, replace

from JRPG.domain.combat.model import (
    ActiveStatus,
    BattleEvent,
    Combatant,
    Element,
    EventKind,
    RandomSource,
    StatusDefinition,
    stats_with_statuses,
)
from JRPG.domain.errors import DomainError
from JRPG.domain.stats import require_integer


def with_statuses(target: Combatant, statuses: tuple[ActiveStatus, ...]) -> Combatant:
    stats = stats_with_statuses(target.base_stats, statuses, target.permanent_modifiers)
    return replace(
        target, statuses=statuses, hp=min(target.hp, stats.hp), mp=min(target.mp, stats.mp)
    )


@dataclass(frozen=True, slots=True)
class Damage:
    power: int = 0
    magical: bool = False
    element: Element = Element.NEUTRAL

    def __post_init__(self) -> None:
        require_integer(self.power)
        if not isinstance(self.element, Element):
            raise DomainError("Élément inconnu.")

    def apply(
        self, actor: Combatant, target: Combatant, random: RandomSource
    ) -> tuple[Combatant, tuple[BattleEvent, ...]]:
        if target.hp == 0:
            return target, ()
        hit_chance = max(0, actor.stats.accuracy - target.stats.evasion)
        if random.randint(1, 100) > hit_chance:
            return target, (BattleEvent(EventKind.MISS, actor.id, target.id),)
        critical = random.randint(1, 100) <= actor.stats.critical
        attack = actor.stats.magic if self.magical else actor.stats.strength
        defense = target.stats.resistance if self.magical else target.stats.defense
        raw = max(1, attack * 2 + self.power - defense)
        resistance = target.resistance(self.element)
        amount = raw * (2 if critical else 1) * resistance // 100
        if resistance:
            amount = max(1, amount // (2 if target.defending else 1))
        amount = min(target.hp, amount)
        return replace(target, hp=target.hp - amount), (
            BattleEvent(EventKind.DAMAGE, actor.id, target.id, amount, critical=critical),
        )


@dataclass(frozen=True, slots=True)
class Heal:
    amount: int

    def __post_init__(self) -> None:
        require_integer(self.amount, 1)

    def apply(
        self, actor: Combatant, target: Combatant, random: RandomSource
    ) -> tuple[Combatant, tuple[BattleEvent, ...]]:
        if not target.hp:
            return target, ()
        amount = min(self.amount, target.stats.hp - target.hp)
        return replace(target, hp=target.hp + amount), (
            BattleEvent(EventKind.HEAL, actor.id, target.id, amount),
        )


@dataclass(frozen=True, slots=True)
class Revive:
    amount: int

    def __post_init__(self) -> None:
        require_integer(self.amount, 1)

    def apply(
        self, actor: Combatant, target: Combatant, random: RandomSource
    ) -> tuple[Combatant, tuple[BattleEvent, ...]]:
        if target.hp:
            return target, ()
        amount = min(self.amount, target.stats.hp)
        # Les états temporaires sont effacés lors d'une résurrection.
        clean = with_statuses(target, ())
        amount = min(amount, clean.stats.hp)
        return replace(clean, hp=amount, defending=False), (
            BattleEvent(EventKind.REVIVED, actor.id, target.id, amount),
        )


@dataclass(frozen=True, slots=True)
class ApplyStatus:
    status: StatusDefinition
    chance: int = 100

    def __post_init__(self) -> None:
        require_integer(self.chance)
        if self.chance > 100:
            raise DomainError("Probabilité supérieure à 100 %.")

    def apply(
        self, actor: Combatant, target: Combatant, random: RandomSource
    ) -> tuple[Combatant, tuple[BattleEvent, ...]]:
        if not target.hp or random.randint(1, 100) > self.chance:
            return target, ()
        existing = next(
            (entry for entry in target.statuses if entry.definition.id == self.status.id), None
        )
        if existing and existing.definition != self.status:
            raise DomainError("Définitions d'état contradictoires.")
        statuses = tuple(
            entry for entry in target.statuses if entry.definition.id != self.status.id
        )
        statuses += (ActiveStatus(self.status, self.status.duration),)
        return with_statuses(target, statuses), (
            BattleEvent(EventKind.STATUS_APPLIED, actor.id, target.id, status_id=self.status.id),
        )
