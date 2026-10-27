"""Personnages composés de définitions, progression et équipements."""

from dataclasses import dataclass, fields

from JRPG.domain.errors import (
    CharacterKnockedOut,
    DomainError,
    IncompatibleEquipment,
    InsufficientMana,
)
from JRPG.domain.items import EquipmentSlot, Inventory, ItemDefinition, ItemQuantity
from JRPG.domain.stats import CharacterStats, StatModifiers, require_integer, require_text


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    id: str
    name: str
    base_stats: CharacterStats
    growth: StatModifiers = StatModifiers()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        if not isinstance(self.base_stats, CharacterStats) or not isinstance(
            self.growth, StatModifiers
        ):
            raise DomainError("Caractéristiques de classe invalides.")
        for field in fields(self.growth):
            require_integer(getattr(self.growth, field.name))


@dataclass(frozen=True, slots=True)
class CharacterDefinition:
    id: str
    name: str
    character_class: ClassDefinition

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        if not isinstance(self.character_class, ClassDefinition):
            raise DomainError("Définition de classe invalide.")


@dataclass(frozen=True, slots=True)
class ProgressionRules:
    """XP cumulée : palier * niveau * (niveau - 1) / 2 ; plafond explicite."""

    step: int = 100
    max_level: int = 99

    def __post_init__(self) -> None:
        require_integer(self.step, 1)
        require_integer(self.max_level, 1)

    def threshold(self, level: int) -> int:
        require_integer(level, 1)
        if level > self.max_level:
            raise DomainError("Niveau au-delà du plafond.")
        return self.step * level * (level - 1) // 2

    def level_for(self, experience: int) -> int:
        require_integer(experience)
        level = 1
        while level < self.max_level and experience >= self.threshold(level + 1):
            level += 1
        return level


@dataclass(frozen=True, slots=True)
class CharacterState:
    experience: int
    hp: int
    mp: int
    skills: tuple[str, ...]
    equipment: tuple[tuple[EquipmentSlot, ItemDefinition], ...]

    def __post_init__(self) -> None:
        for value in (self.experience, self.hp, self.mp):
            require_integer(value)
        object.__setattr__(self, "skills", tuple(self.skills))
        object.__setattr__(self, "equipment", tuple(self.equipment))
        if len(set(self.skills)) != len(self.skills):
            raise DomainError("Compétence dupliquée.")
        for skill in self.skills:
            require_text(skill)


class Character:
    """L'entité protège ses ressources ; les définitions n'ont aucun état joueur."""

    def __init__(
        self, definition: CharacterDefinition, progression: ProgressionRules | None = None
    ) -> None:
        self._definition = definition
        self._progression = progression if progression is not None else ProgressionRules()
        self._experience = 0
        self._skills: frozenset[str] = frozenset()
        self._equipment: dict[EquipmentSlot, ItemDefinition] = {}
        self._hp = self.stats.hp
        self._mp = self.stats.mp

    @property
    def progression(self) -> ProgressionRules:
        return self._progression

    def snapshot(self) -> CharacterState:
        return CharacterState(self.experience, self.hp, self.mp, self.skills, self.equipment)

    @classmethod
    def from_state(
        cls,
        definition: CharacterDefinition,
        state: CharacterState,
        progression: ProgressionRules | None = None,
    ) -> Character:
        candidate = cls(definition, progression)
        if state.experience > candidate.progression.threshold(candidate.progression.max_level):
            raise DomainError("XP au-delà du plafond.")
        candidate._experience = state.experience
        candidate._skills = frozenset(state.skills)
        for slot, item in state.equipment:
            if (
                not isinstance(slot, EquipmentSlot)
                or slot in candidate._equipment
                or slot not in item.slots
                or item.allowed_classes
                and definition.character_class.id not in item.allowed_classes
            ):
                raise IncompatibleEquipment("Équipement sauvegardé incohérent.")
            candidate._equipment[slot] = item
        candidate.set_resources(state.hp, state.mp)
        return candidate

    def apply_state(self, state: CharacterState) -> None:
        candidate = Character.from_state(self.definition, state, self.progression)
        self._experience, self._skills = candidate._experience, candidate._skills
        self._equipment = candidate._equipment
        self._hp, self._mp = candidate.hp, candidate.mp

    @property
    def definition(self) -> CharacterDefinition:
        return self._definition

    @property
    def id(self) -> str:
        return self._definition.id

    @property
    def experience(self) -> int:
        return self._experience

    @property
    def level(self) -> int:
        return self._progression.level_for(self._experience)

    @property
    def base_stats(self) -> CharacterStats:
        job = self._definition.character_class
        return job.base_stats.modified(job.growth, self.level - 1)

    @property
    def equipment_modifiers(self) -> StatModifiers:
        return StatModifiers(
            **{
                field.name: sum(
                    getattr(item.modifiers, field.name) for item in self._equipment.values()
                )
                for field in fields(StatModifiers)
            }
        )

    @property
    def stats(self) -> CharacterStats:
        return self.base_stats.modified(self.equipment_modifiers)

    @property
    def hp(self) -> int:
        return self._hp

    @property
    def mp(self) -> int:
        return self._mp

    @property
    def is_knocked_out(self) -> bool:
        return self._hp == 0

    @property
    def equipment(self) -> tuple[tuple[EquipmentSlot, ItemDefinition], ...]:
        return tuple(sorted(self._equipment.items()))

    @property
    def skills(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))

    def learn_skill(self, skill_id: str) -> None:
        require_text(skill_id)
        self._skills = self._skills | {skill_id}

    def set_resources(self, hp: int, mp: int) -> None:
        """Appliquer un résultat validé de session ; conserve les bornes du personnage."""
        require_integer(hp)
        require_integer(mp)
        if hp > self.stats.hp or mp > self.stats.mp:
            raise DomainError("Ressources hors limites.")
        self._hp, self._mp = hp, mp

    def gain_experience(self, amount: int) -> int:
        require_integer(amount, 1)
        before = self.level
        self._experience = min(
            self._experience + amount, self._progression.threshold(self._progression.max_level)
        )
        return self.level - before

    def lose_hp(self, amount: int) -> None:
        require_integer(amount, 1)
        self._hp = max(0, self._hp - amount)

    def restore_hp(self, amount: int) -> None:
        require_integer(amount, 1)
        if self.is_knocked_out:
            raise CharacterKnockedOut(self.id)
        self._hp = min(self.stats.hp, self._hp + amount)

    def spend_mana(self, amount: int) -> None:
        require_integer(amount)
        if self.is_knocked_out:
            raise CharacterKnockedOut(self.id)
        if amount > self._mp:
            raise InsufficientMana(self.id)
        self._mp -= amount

    def restore_mana(self, amount: int) -> None:
        require_integer(amount, 1)
        self._mp = min(self.stats.mp, self._mp + amount)

    def equipment_error(self, item: ItemDefinition, slot: EquipmentSlot) -> str | None:
        if not isinstance(slot, EquipmentSlot) or slot not in item.slots:
            return "Emplacement incompatible."
        if item.allowed_classes and self.definition.character_class.id not in item.allowed_classes:
            return "Classe incompatible."
        return None

    def stats_with_equipment(
        self, slot: EquipmentSlot, item: ItemDefinition | None
    ) -> CharacterStats:
        if not isinstance(slot, EquipmentSlot):
            raise IncompatibleEquipment("Emplacement inconnu.")
        candidate = self._equipment.copy()
        candidate.pop(slot, None)
        if item is not None:
            reason = self.equipment_error(item, slot)
            if reason:
                raise IncompatibleEquipment(reason)
            candidate[slot] = item
        modifiers = StatModifiers(
            **{
                field.name: sum(
                    getattr(entry.modifiers, field.name) for entry in candidate.values()
                )
                for field in fields(StatModifiers)
            }
        )
        return self.base_stats.modified(modifiers)

    def equip(self, inventory: Inventory, item: ItemDefinition, slot: EquipmentSlot) -> None:
        reason = self.equipment_error(item, slot)
        if reason:
            raise IncompatibleEquipment(reason)
        previous = self._equipment.get(slot)
        candidate = self._equipment | {slot: item}
        returned = (ItemQuantity(previous, 1),) if previous else ()
        # Seul exchange peut échouer ; aucun état du personnage n'a encore changé.
        inventory.exchange((ItemQuantity(item, 1),), returned)
        self._equipment = candidate
        self._clamp_resources()

    def unequip(self, inventory: Inventory, slot: EquipmentSlot) -> None:
        if slot not in self._equipment:
            raise IncompatibleEquipment("Emplacement vide.")
        candidate = self._equipment.copy()
        previous = candidate.pop(slot)
        inventory.add(previous)
        self._equipment = candidate
        self._clamp_resources()

    def _clamp_resources(self) -> None:
        stats = self.stats
        self._hp = min(self._hp, stats.hp)
        self._mp = min(self._mp, stats.mp)
