"""Contrats et valeurs immuables du combat, sans rendu ni aléatoire global."""

from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Protocol

from JRPG.domain.characters import Character
from JRPG.domain.errors import DomainError
from JRPG.domain.items import ItemCategory, ItemDefinition
from JRPG.domain.stats import CharacterStats, StatModifiers, require_integer, require_text


class BattleRuleError(DomainError):
    """Commande ou transition illégale, rejetée avant mutation."""


class InvalidTarget(BattleRuleError):
    """Le ciblage ne respecte pas la définition de l'action."""


class RandomSource(Protocol):
    def randint(self, minimum: int, maximum: int) -> int: ...


class Side(StrEnum):
    ALLIES = "allies"
    ENEMIES = "enemies"


class BattleState(StrEnum):
    INITIALIZING = "initializing"
    TURN_READY = "turn_ready"
    AWAITING_ACTION = "awaiting_action"
    RESOLVING = "resolving"
    TURN_END = "turn_end"
    FINISHED = "finished"


class Outcome(StrEnum):
    VICTORY = "victory"
    DEFEAT = "defeat"
    FLED = "fled"


class Action(StrEnum):
    ATTACK = "attack"
    SKILL = "skill"
    DEFEND = "defend"
    ITEM = "item"
    FLEE = "flee"
    PASS = "pass"


class Element(StrEnum):
    NEUTRAL = "neutral"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"


class StatusKind(StrEnum):
    CHARGING = "charging"
    POISON = "poison"
    BURN = "burn"
    SLEEP = "sleep"
    PARALYSIS = "paralysis"
    SILENCE = "silence"
    MODIFIER = "modifier"


@dataclass(frozen=True, slots=True)
class StatusDefinition:
    id: str
    kind: StatusKind
    duration: int
    potency: int = 0
    modifiers: StatModifiers = StatModifiers()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_integer(self.duration, 1)
        require_integer(self.potency)
        if not isinstance(self.kind, StatusKind) or not isinstance(self.modifiers, StatModifiers):
            raise DomainError("Définition d'état invalide.")


@dataclass(frozen=True, slots=True)
class ActiveStatus:
    definition: StatusDefinition
    remaining: int

    def __post_init__(self) -> None:
        require_integer(self.remaining, 1)
        if self.remaining > self.definition.duration:
            raise DomainError("Durée d'état supérieure à sa définition.")


def stats_with_statuses(
    base: CharacterStats,
    statuses: tuple[ActiveStatus, ...],
    permanent: StatModifiers | None = None,
) -> CharacterStats:
    permanent = permanent if permanent is not None else StatModifiers()
    modifiers = StatModifiers(
        **{
            field.name: getattr(permanent, field.name)
            + sum(getattr(status.definition.modifiers, field.name) for status in statuses)
            for field in fields(StatModifiers)
        }
    )
    return base.modified(modifiers)


@dataclass(frozen=True, slots=True)
class Resistance:
    element: Element
    percent: int

    def __post_init__(self) -> None:
        if not isinstance(self.element, Element):
            raise DomainError("Élément inconnu.")
        require_integer(self.percent)


@dataclass(frozen=True, slots=True)
class Combatant:
    id: str
    name: str
    side: Side
    base_stats: CharacterStats
    hp: int
    mp: int
    skills: tuple[str, ...] = ()
    resistances: tuple[Resistance, ...] = ()
    statuses: tuple[ActiveStatus, ...] = ()
    defending: bool = False
    permanent_modifiers: StatModifiers = StatModifiers()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        if not isinstance(self.side, Side):
            raise DomainError("Camp inconnu.")
        for name in ("skills", "resistances", "statuses"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        require_integer(self.hp)
        require_integer(self.mp)
        if self.hp > self.stats.hp or self.mp > self.stats.mp:
            raise DomainError("Ressources de combattant hors limites.")
        if len({entry.element for entry in self.resistances}) != len(self.resistances):
            raise DomainError("Résistance dupliquée.")
        if len({entry.definition.id for entry in self.statuses}) != len(self.statuses):
            raise DomainError("État actif dupliqué.")
        if len(set(self.skills)) != len(self.skills):
            raise DomainError("Compétence dupliquée.")
        for skill in self.skills:
            require_text(skill)

    @classmethod
    def from_character(cls, character: Character) -> Combatant:
        return cls(
            character.id,
            character.definition.name,
            Side.ALLIES,
            character.base_stats,
            character.hp,
            character.mp,
            character.skills,
            permanent_modifiers=character.equipment_modifiers,
        )

    @property
    def stats(self) -> CharacterStats:
        return stats_with_statuses(self.base_stats, self.statuses, self.permanent_modifiers)

    def has_status(self, kind: StatusKind) -> bool:
        return any(status.definition.kind == kind for status in self.statuses)

    def resistance(self, element: Element) -> int:
        return next((entry.percent for entry in self.resistances if entry.element == element), 100)


@dataclass(frozen=True, slots=True)
class EnemyDefinition:
    id: str
    name: str
    stats: CharacterStats
    skills: tuple[str, ...] = ()
    resistances: tuple[Resistance, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        object.__setattr__(self, "skills", tuple(self.skills))
        object.__setattr__(self, "resistances", tuple(self.resistances))
        self.spawn("validation")

    def spawn(self, instance_id: str) -> Combatant:
        return Combatant(
            instance_id,
            self.name,
            Side.ENEMIES,
            self.stats,
            self.stats.hp,
            self.stats.mp,
            self.skills,
            self.resistances,
        )


class EventKind(StrEnum):
    MANA_RESTORED = "mana_restored"
    DAMAGE = "damage"
    MISS = "miss"
    HEAL = "heal"
    REVIVED = "revived"
    MANA_SPENT = "mana_spent"
    STATUS_APPLIED = "status_applied"
    STATUS_EXPIRED = "status_expired"
    KNOCKED_OUT = "knocked_out"
    ENEMY_DEFEATED = "enemy_defeated"
    DEFENDED = "defended"
    PASSED = "passed"
    FLEE_FAILED = "flee_failed"
    BATTLE_WON = "battle_won"
    BATTLE_LOST = "battle_lost"
    FLED = "fled"


@dataclass(frozen=True, slots=True)
class BattleEvent:
    kind: EventKind
    actor_id: str
    target_id: str = ""
    amount: int = 0
    status_id: str = ""
    critical: bool = False


class TargetSide(StrEnum):
    ENEMY = "enemy"
    ALLY = "ally"
    SELF = "self"


class TargetLife(StrEnum):
    ALIVE = "alive"
    KO = "ko"


@dataclass(frozen=True, slots=True)
class TargetRule:
    side: TargetSide = TargetSide.ENEMY
    life: TargetLife = TargetLife.ALIVE
    multiple: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.side, TargetSide) or not isinstance(self.life, TargetLife):
            raise DomainError("Règle de ciblage invalide.")


class Effect(Protocol):
    def apply(
        self, actor: Combatant, target: Combatant, random: RandomSource
    ) -> tuple[Combatant, tuple[BattleEvent, ...]]: ...


@dataclass(frozen=True, slots=True)
class Ability:
    id: str
    name: str
    cost: int
    targeting: TargetRule
    effects: tuple[Effect, ...]
    magical: bool = False
    required_status: str = ""

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        require_integer(self.cost)
        if self.required_status:
            require_text(self.required_status)
        object.__setattr__(self, "effects", tuple(self.effects))
        if not self.effects or not isinstance(self.targeting, TargetRule):
            raise DomainError("Une compétence nécessite un ciblage et des effets.")


@dataclass(frozen=True, slots=True)
class Consumable:
    item: ItemDefinition
    ability: Ability

    def __post_init__(self) -> None:
        if self.item.category != ItemCategory.CONSUMABLE or self.ability.cost:
            raise DomainError("Un consommable de combat ne coûte pas de PM.")


@dataclass(frozen=True, slots=True)
class BattleCommand:
    actor_id: str
    turn_id: int
    action: Action
    targets: tuple[str, ...] = ()
    ability_id: str = ""
    item_id: str = ""

    def __post_init__(self) -> None:
        require_text(self.actor_id)
        require_integer(self.turn_id, 1)
        object.__setattr__(self, "targets", tuple(self.targets))
        if not isinstance(self.action, Action):
            raise BattleRuleError("Action inconnue.")


@dataclass(frozen=True, slots=True)
class BattleActionResult:
    command: BattleCommand
    events: tuple[BattleEvent, ...]
    transitions: tuple[BattleState, ...]
    combatants: tuple[Combatant, ...]
    outcome: Outcome | None
