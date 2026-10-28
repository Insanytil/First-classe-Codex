"""Quêtes à faits dédupliqués : progression indépendante du rendu et du journal."""

from dataclasses import dataclass
from enum import StrEnum

from JRPG.domain.combat.rewards import RewardBundle
from JRPG.domain.errors import DomainError
from JRPG.domain.stats import require_integer, require_text
from JRPG.domain.world import WorldEvent, WorldEventKind, WorldState


class QuestKind(StrEnum):
    MAIN = "main"
    SIDE = "side"


class QuestStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    REWARDED = "rewarded"


@dataclass(frozen=True, slots=True)
class Objective:
    id: str
    description: str
    kind: WorldEventKind
    subjects: frozenset[str]
    required: int = 1

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.description)
        object.__setattr__(self, "subjects", frozenset(self.subjects))
        require_integer(self.required, 1)
        if not isinstance(self.kind, WorldEventKind) or self.required > len(self.subjects):
            raise DomainError("Objectif impossible ou événement inconnu.")
        for subject in self.subjects:
            require_text(subject)


@dataclass(frozen=True, slots=True)
class QuestDefinition:
    id: str
    name: str
    description: str
    objectives: tuple[Objective, ...]
    reward: RewardBundle = RewardBundle()
    prerequisites: tuple[str, ...] = ()
    kind: QuestKind = QuestKind.SIDE

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        require_text(self.description)
        if not isinstance(self.kind, QuestKind):
            raise DomainError("Type de quête inconnu.")
        object.__setattr__(self, "objectives", tuple(self.objectives))
        object.__setattr__(self, "prerequisites", tuple(self.prerequisites))
        if not self.objectives or len({entry.id for entry in self.objectives}) != len(
            self.objectives
        ):
            raise DomainError("Objectifs absents ou dupliqués.")


class QuestBook:
    def __init__(
        self,
        definitions: tuple[QuestDefinition, ...],
        world: WorldState,
        states: tuple[tuple[str, QuestStatus], ...] | None = None,
    ) -> None:
        self._definitions = {entry.id: entry for entry in definitions}
        if len(self._definitions) != len(definitions):
            raise DomainError("Identifiant de quête dupliqué.")
        self._facts = {
            WorldEventKind.MAP_ENTERED: world.visited_maps,
            WorldEventKind.NPC_SPOKEN: world.talked_to,
            WorldEventKind.CHEST_OPENED: world.opened_chests,
            WorldEventKind.ENCOUNTER_CLEARED: world.cleared_encounters,
            WorldEventKind.FLAG_SET: world.flags,
        }

        def visit(identity: str, ancestors: frozenset[str]) -> None:
            if identity not in self._definitions or identity in ancestors:
                raise DomainError("Prérequis de quête inconnu ou cyclique.")
            for dependency in self._definitions[identity].prerequisites:
                visit(dependency, ancestors | {identity})

        for identity in self._definitions:
            visit(identity, frozenset())
        self._states = {identity: QuestStatus.LOCKED for identity in self._definitions}
        self._refresh()
        if states is not None:
            supplied = dict(states)
            if len(supplied) != len(states) or set(supplied) != set(self._states):
                raise DomainError("État de quêtes incomplet ou dupliqué.")
            for identity, status in supplied.items():
                if not isinstance(status, QuestStatus):
                    raise DomainError("Statut de quête inconnu.")
                unlocked = all(
                    supplied[key] == QuestStatus.REWARDED
                    for key in self.definition(identity).prerequisites
                )
                complete = self._complete(identity)
                if (
                    (status == QuestStatus.LOCKED) == unlocked
                    or status == QuestStatus.ACTIVE
                    and complete
                    or status in {QuestStatus.COMPLETED, QuestStatus.REWARDED}
                    and not complete
                ):
                    raise DomainError("Progression de quête incohérente.")
            self._states = supplied

    @property
    def definitions(self) -> tuple[QuestDefinition, ...]:
        return tuple(self._definitions.values())

    @property
    def states(self) -> tuple[tuple[str, QuestStatus], ...]:
        return tuple(sorted(self._states.items()))

    def definition(self, identity: str) -> QuestDefinition:
        if identity not in self._definitions:
            raise DomainError("Quête inconnue.")
        return self._definitions[identity]

    def status(self, identity: str) -> QuestStatus:
        self.definition(identity)
        return self._states[identity]

    def progress(self, objective: Objective) -> int:
        return min(objective.required, len(objective.subjects & self._facts[objective.kind]))

    def _complete(self, identity: str) -> bool:
        return all(
            self.progress(entry) == entry.required for entry in self.definition(identity).objectives
        )

    def _refresh(self) -> None:
        for identity, definition in self._definitions.items():
            if self._states[identity] == QuestStatus.LOCKED and all(
                self._states[key] == QuestStatus.REWARDED for key in definition.prerequisites
            ):
                self._states[identity] = QuestStatus.AVAILABLE
            if self._states[identity] == QuestStatus.ACTIVE and self._complete(identity):
                self._states[identity] = QuestStatus.COMPLETED

    def observe(self, event: WorldEvent) -> None:
        self._facts[event.kind] = self._facts[event.kind] | {event.subject_id}
        self._refresh()

    def accept(self, identity: str) -> None:
        if self.status(identity) != QuestStatus.AVAILABLE:
            raise DomainError("Cette quête ne peut pas être acceptée.")
        self._states[identity] = QuestStatus.ACTIVE
        self._refresh()

    def claim(self, identity: str) -> RewardBundle:
        if self.status(identity) != QuestStatus.COMPLETED:
            raise DomainError("Récompense indisponible ou déjà reçue.")
        reward = self.definition(identity).reward
        self._states[identity] = QuestStatus.REWARDED
        self._refresh()
        return reward
