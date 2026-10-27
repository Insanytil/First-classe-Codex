"""Dialogues déclaratifs : conditions et opérations énumérées, aucun code exécutable."""

from dataclasses import dataclass
from enum import StrEnum

from JRPG.domain.errors import DomainError
from JRPG.domain.quests import QuestStatus
from JRPG.domain.stats import require_text


class StoryOperation(StrEnum):
    ACCEPT_QUEST = "accept_quest"
    CLAIM_QUEST = "claim_quest"
    SET_FLAG = "set_flag"
    OPEN_SHOP = "open_shop"
    REST = "rest"


@dataclass(frozen=True, slots=True)
class StoryEffect:
    operation: StoryOperation
    reference: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.operation, StoryOperation):
            raise DomainError("Opération de dialogue inconnue.")
        if self.operation != StoryOperation.REST:
            require_text(self.reference)


@dataclass(frozen=True, slots=True)
class DialogueCondition:
    quest: str = ""
    states: frozenset[QuestStatus] = frozenset()
    flag: str = ""
    present: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "states", frozenset(self.states))
        if bool(self.quest) == bool(self.flag) or bool(self.quest) != bool(self.states):
            raise DomainError("Condition de dialogue invalide.")
        if any(not isinstance(status, QuestStatus) for status in self.states):
            raise DomainError("Condition de quête inconnue.")


@dataclass(frozen=True, slots=True)
class DialogueChoice:
    id: str
    label: str
    next_node: str | None = None
    conditions: tuple[DialogueCondition, ...] = ()
    effects: tuple[StoryEffect, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.label)
        object.__setattr__(self, "conditions", tuple(self.conditions))
        object.__setattr__(self, "effects", tuple(self.effects))


@dataclass(frozen=True, slots=True)
class DialogueNode:
    id: str
    text: str
    choices: tuple[DialogueChoice, ...]

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.text)
        object.__setattr__(self, "choices", tuple(self.choices))
        if not self.choices or len({entry.id for entry in self.choices}) != len(self.choices):
            raise DomainError("Choix absents ou dupliqués.")


@dataclass(frozen=True, slots=True)
class DialogueDefinition:
    id: str
    start: str
    nodes: tuple[DialogueNode, ...]

    def __post_init__(self) -> None:
        require_text(self.id)
        object.__setattr__(self, "nodes", tuple(self.nodes))
        ids = {entry.id for entry in self.nodes}
        if len(ids) != len(self.nodes) or self.start not in ids:
            raise DomainError("Nœud initial absent ou dupliqué.")
        if any(
            choice.next_node is not None and choice.next_node not in ids
            for node in self.nodes
            for choice in node.choices
        ):
            raise DomainError("Destination de dialogue inconnue.")

    def node(self, identity: str) -> DialogueNode:
        for entry in self.nodes:
            if entry.id == identity:
                return entry
        raise DomainError("Nœud de dialogue inconnu.")
