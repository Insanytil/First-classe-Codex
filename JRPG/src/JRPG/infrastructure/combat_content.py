"""Compilation d'un catalogue JSON en définitions métier, sans code exécutable."""

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import cast

from JRPG.domain.characters import CharacterDefinition, ClassDefinition
from JRPG.domain.combat.ai import TelegraphPattern
from JRPG.domain.combat.effects import ApplyStatus, CureStatuses, Damage, Heal, RestoreMana, Revive
from JRPG.domain.combat.model import (
    Ability,
    Consumable,
    Effect,
    Element,
    EnemyDefinition,
    Resistance,
    StatusDefinition,
    StatusKind,
    TargetLife,
    TargetRule,
    TargetSide,
)
from JRPG.domain.combat.rewards import LootEntry
from JRPG.domain.items import ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.stats import CharacterStats, StatModifiers
from JRPG.infrastructure.validation import ContentError, boolean, integer, record, sequence, text


@dataclass(frozen=True, slots=True)
class HeroTemplate:
    definition: CharacterDefinition
    skills: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EncounterProfile:
    id: str
    experience_per_enemy: int
    gold_per_enemy: int
    allow_flee: bool
    guaranteed: tuple[ItemQuantity, ...]
    weighted: tuple[LootEntry, ...]
    telegraph: TelegraphPattern | None
    boss: bool = False


@dataclass(frozen=True, slots=True)
class CombatCatalog:
    heroes: tuple[HeroTemplate, ...]
    abilities: tuple[Ability, ...]
    consumables: tuple[Consumable, ...]
    enemies: tuple[EnemyDefinition, ...]
    profiles: tuple[EncounterProfile, ...]
    enemy_profiles: tuple[tuple[str, str], ...]
    initial_items: tuple[ItemQuantity, ...]


def unique(entries: list[str], label: str) -> None:
    if len(set(entries)) != len(entries):
        raise ContentError(f"Identifiant dupliqué : {label}.")


def known_fields(data: dict[str, object], names: str) -> None:
    if set(data) - set(names.split()):
        raise ContentError("Champs inconnus dans le catalogue de combat.")


def modifiers(value: object) -> StatModifiers:
    data = record(value)
    if any(type(number) is not int for number in data.values()):
        raise ContentError("Modificateur entier attendu.")
    return StatModifiers(**{key: cast(int, number) for key, number in data.items()})


def targeting(data: dict[str, object]) -> TargetRule:
    known_fields(data, "side life multiple")
    return TargetRule(
        TargetSide(text(data.get("side", "enemy"))),
        TargetLife(text(data.get("life", "alive"))),
        boolean(data.get("multiple", False)),
    )


def effect(data: dict[str, object], statuses: dict[str, StatusDefinition]) -> Effect:
    kind = text(data["kind"])
    fields = {
        "damage": "kind power magical element",
        "heal": "kind amount",
        "revive": "kind amount",
        "mana": "kind amount",
        "cure": "kind kinds",
        "status": "kind status chance",
    }
    if kind not in fields:
        raise ContentError(f"Effet inconnu : {kind}.")
    known_fields(data, fields[kind])
    if kind == "damage":
        return Damage(
            integer(data.get("power", 0)),
            boolean(data.get("magical", False)),
            Element(text(data.get("element", "neutral"))),
        )
    if kind == "heal":
        return Heal(integer(data["amount"]))
    if kind == "revive":
        return Revive(integer(data["amount"]))
    if kind == "mana":
        return RestoreMana(integer(data["amount"]))
    if kind == "cure":
        return CureStatuses(frozenset(StatusKind(text(key)) for key in sequence(data["kinds"])))
    if kind == "status":
        return ApplyStatus(statuses[text(data["status"])], integer(data.get("chance", 100)))
    raise ContentError(f"Effet inconnu : {kind}.")


def ability(data: dict[str, object], statuses: dict[str, StatusDefinition]) -> Ability:
    known_fields(data, "id name cost targeting effects magical required_status description")
    required = text(data["required_status"]) if "required_status" in data else ""
    if required and required not in statuses:
        raise ContentError("Préparation de compétence inconnue.")
    return Ability(
        text(data["id"]),
        text(data["name"]),
        integer(data.get("cost", 0)),
        targeting(record(data.get("targeting", {}))),
        tuple(effect(record(raw), statuses) for raw in sequence(data["effects"])),
        boolean(data.get("magical", False)),
        required,
        text(data["description"]) if "description" in data else "",
    )


def stack(data: dict[str, object], items: dict[str, ItemDefinition]) -> ItemQuantity:
    return ItemQuantity(items[text(data["id"])], integer(data["quantity"]))


def decode_combat(source: str) -> CombatCatalog:
    try:
        data = record(json.loads(source))
        known_fields(
            data, "version statuses abilities heroes consumables profiles enemies initial_items"
        )
        if integer(data["version"]) != 1:
            raise ContentError("Version du catalogue de combat inconnue.")
        raw_statuses = [record(raw) for raw in sequence(data["statuses"])]
        unique([text(raw["id"]) for raw in raw_statuses], "état")
        for status_data in raw_statuses:
            known_fields(status_data, "id kind duration potency modifiers")
        statuses = {
            text(raw["id"]): StatusDefinition(
                text(raw["id"]),
                StatusKind(text(raw["kind"])),
                integer(raw["duration"]),
                integer(raw.get("potency", 0)),
                modifiers(raw.get("modifiers", {})),
            )
            for raw in raw_statuses
        }
        abilities = tuple(ability(record(raw), statuses) for raw in sequence(data["abilities"]))
        unique([entry.id for entry in abilities], "compétence")
        skills = {entry.id for entry in abilities}
        by_skill = {entry.id: entry for entry in abilities}
        heroes = []
        for raw in sequence(data["heroes"]):
            hero = record(raw)
            known_fields(hero, "id name class class_name stats growth skills")
            stats = CharacterStats(
                **{key: integer(value) for key, value in record(hero["stats"]).items()}
            )
            learned = tuple(text(key) for key in sequence(hero["skills"]))
            unique(list(learned), "compétence de héros")
            if not set(learned) <= skills:
                raise ContentError("Compétence de héros inconnue.")
            job = ClassDefinition(
                text(hero["class"]), text(hero["class_name"]), stats, modifiers(hero["growth"])
            )
            heroes.append(
                HeroTemplate(
                    CharacterDefinition(text(hero["id"]), text(hero["name"]), job), learned
                )
            )
        unique([entry.definition.id for entry in heroes], "héros")
        consumables = tuple(
            Consumable(
                ItemDefinition(text(raw["id"]), text(raw["name"]), ItemCategory.CONSUMABLE),
                ability(record(raw["ability"]), statuses),
            )
            for raw in (record(value) for value in sequence(data["consumables"]))
        )
        unique([entry.item.id for entry in consumables], "consommable")
        for raw in sequence(data["consumables"]):
            known_fields(record(raw), "id name ability")
        items = {entry.item.id: entry.item for entry in consumables}
        profiles = []
        for raw in sequence(data["profiles"]):
            profile = record(raw)
            known_fields(
                profile,
                "id experience_per_enemy gold_per_enemy allow_flee "
                "guaranteed weighted telegraph boss",
            )
            pattern = None
            if "telegraph" in profile:
                telegraph = record(profile["telegraph"])
                known_fields(telegraph, "preparation attack status")
                pattern = TelegraphPattern(
                    text(telegraph["preparation"]),
                    text(telegraph["attack"]),
                    text(telegraph["status"]),
                )
                if (
                    not {pattern.preparation, pattern.attack} <= skills
                    or pattern.status not in statuses
                ):
                    raise ContentError("Séquence d'annonce inconnue.")
                preparation = by_skill[pattern.preparation]
                if (
                    preparation.targeting.side != TargetSide.SELF
                    or not any(
                        isinstance(entry, ApplyStatus)
                        and entry.status.id == pattern.status
                        and entry.status.duration >= 2
                        for entry in preparation.effects
                    )
                    or by_skill[pattern.attack].required_status != pattern.status
                ):
                    raise ContentError("Séquence d'annonce incompatible avec les compétences.")
            profiles.append(
                EncounterProfile(
                    text(profile["id"]),
                    integer(profile["experience_per_enemy"]),
                    integer(profile["gold_per_enemy"]),
                    boolean(profile["allow_flee"]),
                    tuple(stack(record(value), items) for value in sequence(profile["guaranteed"])),
                    tuple(
                        LootEntry(
                            integer(entry["weight"]), stack(entry, items) if "id" in entry else None
                        )
                        for entry in (
                            record(value) for value in sequence(profile.get("weighted", []))
                        )
                    ),
                    pattern,
                    boolean(profile.get("boss", False)),
                )
            )
        unique([entry.id for entry in profiles], "profil de rencontre")
        enemies = []
        links = []
        for raw in sequence(data["enemies"]):
            enemy = record(raw)
            known_fields(enemy, "id name stats skills resistances profile")
            learned = tuple(text(key) for key in sequence(enemy.get("skills", [])))
            unique(list(learned), "compétence ennemie")
            if not set(learned) <= skills:
                raise ContentError("Compétence ennemie inconnue.")
            profile_id = text(enemy["profile"])
            if profile_id not in {entry.id for entry in profiles}:
                raise ContentError("Profil de rencontre inconnu.")
            pattern = next(entry.telegraph for entry in profiles if entry.id == profile_id)
            if pattern is not None and not {pattern.preparation, pattern.attack} <= set(learned):
                raise ContentError("L'ennemi ne connaît pas sa séquence d'annonce.")
            enemies.append(
                EnemyDefinition(
                    text(enemy["id"]),
                    text(enemy["name"]),
                    CharacterStats(
                        **{key: integer(value) for key, value in record(enemy["stats"]).items()}
                    ),
                    learned,
                    tuple(
                        Resistance(Element(key), integer(value))
                        for key, value in record(enemy.get("resistances", {})).items()
                    ),
                )
            )
            links.append((text(enemy["id"]), profile_id))
        unique([entry.id for entry in enemies], "ennemi")
        if not heroes or not enemies or not profiles:
            raise ContentError("Catalogue de combat incomplet.")
        return CombatCatalog(
            tuple(heroes),
            abilities,
            consumables,
            tuple(enemies),
            tuple(profiles),
            tuple(links),
            tuple(stack(record(raw), items) for raw in sequence(data["initial_items"])),
        )
    except (ValueError, TypeError, KeyError) as error:
        raise ContentError(f"Catalogue de combat invalide : {error}") from error


def load_combat_catalog() -> CombatCatalog:
    try:
        source = (
            files("JRPG.infrastructure.content").joinpath("combat.json").read_text(encoding="utf-8")
        )
        return decode_combat(source)
    except OSError as error:
        raise ContentError("Catalogue de combat introuvable.") from error
