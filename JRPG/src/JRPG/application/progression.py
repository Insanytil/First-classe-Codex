"""Conditions de dialogue et transactions de progression : préparer puis publier."""

from dataclasses import dataclass

from JRPG.domain.characters import Character
from JRPG.domain.dialogues import (
    DialogueChoice,
    DialogueCondition,
    DialogueDefinition,
    DialogueNode,
    StoryEffect,
    StoryOperation,
)
from JRPG.domain.economy import Shop, ShopDefinition
from JRPG.domain.errors import DomainError
from JRPG.domain.items import Inventory, ItemDefinition
from JRPG.domain.party import Party
from JRPG.domain.quests import QuestBook, QuestDefinition
from JRPG.domain.stats import require_text
from JRPG.domain.wallet import Wallet
from JRPG.domain.world import ObjectKind, World, WorldEvent, WorldEventKind, WorldState


@dataclass(frozen=True, slots=True)
class EncounterGate:
    encounter: str
    conditions: tuple[DialogueCondition, ...]
    message: str

    def __post_init__(self) -> None:
        require_text(self.encounter)
        require_text(self.message)
        object.__setattr__(self, "conditions", tuple(self.conditions))
        if not self.conditions:
            raise DomainError("Une restriction de rencontre doit avoir une condition.")


@dataclass(frozen=True, slots=True)
class AdventureContent:
    items: tuple[ItemDefinition, ...]
    quests: tuple[QuestDefinition, ...]
    shops: tuple[ShopDefinition, ...]
    dialogues: tuple[DialogueDefinition, ...]
    npc_dialogues: tuple[tuple[str, str], ...]
    flags: frozenset[str]
    flag_conditions: tuple[tuple[str, DialogueCondition], ...] = ()
    encounter_gates: tuple[EncounterGate, ...] = ()

    def __post_init__(self) -> None:
        for entries in (self.items, self.quests, self.shops, self.dialogues):
            if len({entry.id for entry in entries}) != len(entries):
                raise DomainError("Définition d'aventure dupliquée.")
        quest_ids = {entry.id for entry in self.quests}
        shop_ids = {entry.id for entry in self.shops}
        dialogue_ids = {entry.id for entry in self.dialogues}
        if len({gate.encounter for gate in self.encounter_gates}) != len(self.encounter_gates):
            raise DomainError("Restriction de rencontre dupliquée.")
        for gate in self.encounter_gates:
            for condition in gate.conditions:
                if (
                    condition.quest
                    and condition.quest not in quest_ids
                    or condition.flag
                    and condition.flag not in self.flags
                ):
                    raise DomainError("Condition de rencontre sans référence valide.")
        if len(dict(self.npc_dialogues)) != len(self.npc_dialogues) or any(
            identity not in dialogue_ids for _, identity in self.npc_dialogues
        ):
            raise DomainError("Dialogue de PNJ inconnu ou dupliqué.")
        for identity, condition in self.flag_conditions:
            if identity not in self.flags or condition.quest and condition.quest not in quest_ids:
                raise DomainError("Condition de drapeau inconnue.")
        for dialogue in self.dialogues:
            for node in dialogue.nodes:
                for choice in node.choices:
                    for condition in choice.conditions:
                        if (
                            condition.quest
                            and condition.quest not in quest_ids
                            or condition.flag
                            and condition.flag not in self.flags
                        ):
                            raise DomainError("Condition de dialogue sans référence valide.")
                    for effect in choice.effects:
                        if (
                            effect.operation
                            in {StoryOperation.ACCEPT_QUEST, StoryOperation.CLAIM_QUEST}
                            and effect.reference not in quest_ids
                            or effect.operation == StoryOperation.OPEN_SHOP
                            and effect.reference not in shop_ids
                            or effect.operation == StoryOperation.SET_FLAG
                            and effect.reference not in self.flags
                        ):
                            raise DomainError("Effet de dialogue sans référence valide.")

    def validate_flags(self, quests: QuestBook, flags: frozenset[str]) -> None:
        for identity, condition in self.flag_conditions:
            if identity in flags:
                valid = (
                    quests.status(condition.quest) in condition.states
                    if condition.quest
                    else (condition.flag in flags) == condition.present
                )
                if not valid:
                    raise DomainError("Drapeau incompatible avec la progression.")

    def validate_world(self, world: World) -> None:
        objects = [entry for area in world.maps for entry in area.objects]
        subjects = {
            WorldEventKind.MAP_ENTERED: {area.id for area in world.maps},
            WorldEventKind.NPC_SPOKEN: {
                entry.id for entry in objects if entry.kind == ObjectKind.NPC
            },
            WorldEventKind.CHEST_OPENED: {
                entry.id for entry in objects if entry.kind == ObjectKind.CHEST
            },
            WorldEventKind.ENCOUNTER_CLEARED: {
                entry.id for entry in objects if entry.kind == ObjectKind.ENCOUNTER
            },
            WorldEventKind.FLAG_SET: self.flags,
        }
        if any(
            identity not in subjects[WorldEventKind.NPC_SPOKEN]
            for identity, _ in self.npc_dialogues
        ):
            raise DomainError("Dialogue attaché à un PNJ absent.")
        for quest in self.quests:
            for objective in quest.objectives:
                if not objective.subjects <= subjects[objective.kind]:
                    raise DomainError("Objectif de quête sans référence de monde valide.")
        if not world.state.flags <= self.flags:
            raise DomainError("Drapeau narratif inconnu.")
        if any(
            gate.encounter not in subjects[WorldEventKind.ENCOUNTER_CLEARED]
            for gate in self.encounter_gates
        ):
            raise DomainError("Restriction attachée à une rencontre absente.")

    def item(self, identity: str) -> ItemDefinition:
        for entry in self.items:
            if entry.id == identity:
                return entry
        raise DomainError("Objet inconnu du catalogue.")


@dataclass(frozen=True, slots=True)
class StoryResult:
    notice: str = ""
    shop_id: str | None = None


class AdventureProgress:
    def __init__(
        self,
        content: AdventureContent,
        world: WorldState,
        party: Party,
        inventory: Inventory,
        wallet: Wallet,
    ) -> None:
        self.content, self.world, self.party = content, world, party
        self.inventory, self.wallet = inventory, wallet
        self.quests = QuestBook(content.quests, world)
        self.shops = {entry.id: Shop(entry.id, entry.name, entry.offers) for entry in content.shops}

    def observe(self, event: WorldEvent) -> None:
        self.quests.observe(event)

    def condition(self, condition: DialogueCondition) -> bool:
        if condition.quest:
            return self.quests.status(condition.quest) in condition.states
        return (condition.flag in self.world.flags) == condition.present

    def dialogue_for(self, npc_id: str) -> DialogueDefinition | None:
        identity = dict(self.content.npc_dialogues).get(npc_id)
        return next((entry for entry in self.content.dialogues if entry.id == identity), None)

    def encounter_error(self, encounter_id: str) -> str | None:
        for gate in self.content.encounter_gates:
            if gate.encounter == encounter_id and not all(
                self.condition(rule) for rule in gate.conditions
            ):
                return gate.message
        return None

    def apply(self, effects: tuple[StoryEffect, ...]) -> StoryResult:
        if not effects:
            return StoryResult()
        quests = QuestBook(self.content.quests, self.world, self.quests.states)
        inventory = Inventory(self.inventory.stacks)
        members = tuple(
            Character.from_state(member.definition, member.snapshot(), member.progression)
            for member in self.party.members
        )
        gold = 0
        flags = set(self.world.flags)
        notices: list[str] = []
        shop_id = None
        for effect in effects:
            if effect.operation == StoryOperation.ACCEPT_QUEST:
                quests.accept(effect.reference)
                notices.append(f"Quête acceptée : {quests.definition(effect.reference).name}.")
            elif effect.operation == StoryOperation.CLAIM_QUEST:
                reward = quests.claim(effect.reference)
                inventory.exchange((), reward.items)
                gold += reward.gold
                for member in members:
                    if reward.experience:
                        member.gain_experience(reward.experience)
                notices.append(f"Récompense : {reward.experience} XP, {reward.gold} pièces.")
            elif effect.operation == StoryOperation.SET_FLAG:
                if effect.reference not in self.content.flags:
                    raise DomainError("Drapeau inconnu.")
                flags.add(effect.reference)
                quests.observe(WorldEvent(WorldEventKind.FLAG_SET, effect.reference))
            elif effect.operation == StoryOperation.OPEN_SHOP:
                if effect.reference not in self.shops:
                    raise DomainError("Boutique inconnue.")
                shop_id = effect.reference
            elif effect.operation == StoryOperation.REST:
                for member in members:
                    member.set_resources(member.stats.hp, member.stats.mp)
                notices.append("Le groupe a retrouvé toutes ses forces.")
            else:
                raise DomainError("Opération de récit inconnue.")
        self.content.validate_flags(quests, frozenset(flags))
        self.inventory.exchange(self.inventory.stacks, inventory.stacks)
        for member, candidate in zip(self.party.members, members, strict=True):
            member.apply_state(candidate.snapshot())
        self.wallet.credit(gold)
        for identity in sorted(flags - self.world.flags):
            self.world.record(WorldEventKind.FLAG_SET, identity)
        self.quests = quests
        return StoryResult(" ".join(notices), shop_id)


class Conversation:
    def __init__(self, progress: AdventureProgress, definition: DialogueDefinition) -> None:
        self.progress, self.definition = progress, definition
        self._node: str | None = definition.start

    @property
    def node(self) -> DialogueNode | None:
        return self.definition.node(self._node) if self._node is not None else None

    @property
    def choices(self) -> tuple[DialogueChoice, ...]:
        node = self.node
        return (
            tuple(
                choice
                for choice in node.choices
                if all(self.progress.condition(condition) for condition in choice.conditions)
            )
            if node
            else ()
        )

    def choose(self, identity: str) -> StoryResult:
        choice = next((entry for entry in self.choices if entry.id == identity), None)
        if choice is None:
            raise DomainError("Choix absent ou condition non satisfaite.")
        result = self.progress.apply(choice.effects)
        self._node = choice.next_node
        return result
