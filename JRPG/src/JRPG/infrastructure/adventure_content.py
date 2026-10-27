"""Catalogue narratif JSON : données compilées en définitions typées."""

import json
from importlib.resources import files

from JRPG.application.progression import AdventureContent
from JRPG.domain.combat.rewards import RewardBundle
from JRPG.domain.dialogues import (
    DialogueChoice,
    DialogueCondition,
    DialogueDefinition,
    DialogueNode,
    StoryEffect,
    StoryOperation,
)
from JRPG.domain.economy import ShopDefinition, ShopOffer
from JRPG.domain.errors import DomainError
from JRPG.domain.items import EquipmentSlot, ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.quests import Objective, QuestDefinition, QuestStatus
from JRPG.domain.stats import StatModifiers
from JRPG.domain.world import WorldEventKind
from JRPG.infrastructure.validation import ContentError, boolean, integer, record, sequence, text


def load_adventure_content(base_items: tuple[ItemDefinition, ...]) -> AdventureContent:
    try:
        source = (
            files("JRPG.infrastructure.content")
            .joinpath("adventure.json")
            .read_text(encoding="utf-8")
        )
        return decode_adventure(source, base_items)
    except (OSError, DomainError) as error:
        raise ContentError(f"adventure.json : {error}") from error


def decode_adventure(source: str, base_items: tuple[ItemDefinition, ...]) -> AdventureContent:
    try:
        data = record(json.loads(source))
        if integer(data["version"]) != 1:
            raise ContentError("Version de récit inconnue.")
        items = list(base_items)
        for raw in sequence(data["equipment"]):
            entry = record(raw)
            modifiers = {key: signed(value) for key, value in record(entry["modifiers"]).items()}
            items.append(
                ItemDefinition(
                    text(entry["id"]),
                    text(entry["name"]),
                    ItemCategory(text(entry["category"])),
                    frozenset(EquipmentSlot(text(slot)) for slot in sequence(entry["slots"])),
                    frozenset(text(key) for key in sequence(entry["classes"])),
                    StatModifiers(**modifiers),
                )
            )
        catalog = {item.id: item for item in items}
        if len(catalog) != len(items):
            raise ContentError("Objet dupliqué.")
        quests = []
        for raw in sequence(data["quests"]):
            entry = record(raw)
            objectives = []
            for objective_raw in sequence(entry["objectives"]):
                objective = record(objective_raw)
                objectives.append(
                    Objective(
                        text(objective["id"]),
                        text(objective["description"]),
                        WorldEventKind(text(objective["event"])),
                        frozenset(text(key) for key in sequence(objective["subjects"])),
                        integer(objective.get("required", 1)),
                    )
                )
            reward = record(entry["reward"])
            stacks = tuple(
                parse_stack(record(stack), catalog) for stack in sequence(reward.get("items", []))
            )
            quests.append(
                QuestDefinition(
                    text(entry["id"]),
                    text(entry["name"]),
                    text(entry["description"]),
                    tuple(objectives),
                    RewardBundle(integer(reward["experience"]), integer(reward["gold"]), stacks),
                    tuple(text(key) for key in sequence(entry.get("prerequisites", []))),
                )
            )
        shops = []
        for raw in sequence(data["shops"]):
            entry = record(raw)
            offers = []
            for offer_raw in sequence(entry["offers"]):
                offer = record(offer_raw)
                offers.append(
                    ShopOffer(
                        catalog[text(offer["item"])],
                        integer(offer["buy"]),
                        integer(offer["sell"]),
                        integer(offer["stock"]),
                    )
                )
            shops.append(ShopDefinition(text(entry["id"]), text(entry["name"]), tuple(offers)))
        dialogues = tuple(parse_dialogue(record(raw)) for raw in sequence(data["dialogues"]))
        links = record(data["npc_dialogues"])
        return AdventureContent(
            tuple(items),
            tuple(quests),
            tuple(shops),
            dialogues,
            tuple((key, text(value)) for key, value in links.items()),
            frozenset(text(value) for value in sequence(data["flags"])),
            tuple(
                (
                    text(rule["flag"]),
                    DialogueCondition(
                        quest=text(rule["quest"]),
                        states=frozenset(
                            QuestStatus(text(value)) for value in sequence(rule["states"])
                        ),
                    ),
                )
                for rule in (record(raw) for raw in sequence(data.get("flag_conditions", [])))
            ),
        )
    except (ValueError, TypeError, KeyError) as error:
        raise ContentError(f"Récit invalide : {error}") from error


def signed(value: object) -> int:
    if type(value) is not int:
        raise ContentError("Modificateur entier attendu.")
    return value


def parse_stack(data: dict[str, object], catalog: dict[str, ItemDefinition]) -> ItemQuantity:
    return ItemQuantity(catalog[text(data["id"])], integer(data["quantity"]))


def parse_dialogue(data: dict[str, object]) -> DialogueDefinition:
    nodes = []
    for raw in sequence(data["nodes"]):
        node = record(raw)
        choices = []
        for choice_raw in sequence(node["choices"]):
            choice = record(choice_raw)
            conditions = []
            for condition_raw in sequence(choice.get("conditions", [])):
                condition = record(condition_raw)
                conditions.append(
                    DialogueCondition(
                        text(condition["quest"]) if "quest" in condition else "",
                        frozenset(
                            QuestStatus(text(status))
                            for status in sequence(condition.get("states", []))
                        ),
                        text(condition["flag"]) if "flag" in condition else "",
                        boolean(condition.get("present", True)),
                    )
                )
            effects = []
            for effect_raw in sequence(choice.get("effects", [])):
                effect = record(effect_raw)
                effects.append(
                    StoryEffect(
                        StoryOperation(text(effect["operation"])),
                        text(effect["reference"]) if "reference" in effect else "",
                    )
                )
            target = choice.get("next")
            choices.append(
                DialogueChoice(
                    text(choice["id"]),
                    text(choice["label"]),
                    text(target) if target is not None else None,
                    tuple(conditions),
                    tuple(effects),
                )
            )
        nodes.append(DialogueNode(text(node["id"]), text(node["text"]), tuple(choices)))
    return DialogueDefinition(text(data["id"]), text(data["start"]), tuple(nodes))
