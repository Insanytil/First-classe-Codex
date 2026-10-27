"""Schéma JSON v1 explicite : types stricts et refus des formats futurs."""

import json
from dataclasses import asdict, fields
from math import isfinite

from JRPG.application.save_data import GameSnapshot, HeroSave, RandomCheckpoint, ShopSave, StackSave
from JRPG.application.saves import SaveError
from JRPG.domain.items import EquipmentSlot
from JRPG.domain.quests import QuestStatus
from JRPG.domain.world import MapPosition
from JRPG.infrastructure.validation import integer, record, sequence, text


def object_fields(value: object, expected: set[str]) -> dict[str, object]:
    data = record(value)
    if set(data) != expected:
        raise SaveError("Champs de sauvegarde manquants ou inconnus.")
    return data


def number(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
        raise SaveError("Nombre fini attendu.")
    return float(value)


def strings(value: object) -> tuple[str, ...]:
    return tuple(text(entry) for entry in sequence(value))


def pairs(value: object) -> tuple[tuple[object, object], ...]:
    result = []
    for entry in sequence(value):
        pair = sequence(entry)
        if len(pair) != 2:
            raise SaveError("Paire de valeurs attendue.")
        result.append((pair[0], pair[1]))
    return tuple(result)


def position(value: object) -> MapPosition:
    data = object_fields(value, {"map_id", "x", "y"})
    return MapPosition(text(data["map_id"]), number(data["x"]), number(data["y"]))


class SaveCodec:
    def encode(self, snapshot: GameSnapshot) -> str:
        try:
            source = (
                json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            )
            self.decode(source)
            return source
        except (TypeError, ValueError, OverflowError) as error:
            raise SaveError(f"Sauvegarde non sérialisable : {error}") from error

    def decode(self, source: str) -> GameSnapshot:
        try:
            root = record(json.loads(source))
            if integer(root["version"]) != 1:
                raise SaveError("Version de sauvegarde non prise en charge (v1 attendue).")
            data = object_fields(root, {field.name for field in fields(GameSnapshot)})
            heroes = []
            for entry in sequence(data["heroes"]):
                hero = object_fields(entry, {field.name for field in fields(HeroSave)})
                heroes.append(
                    HeroSave(
                        text(hero["id"]),
                        text(hero["class_id"]),
                        integer(hero["experience"]),
                        integer(hero["hp"]),
                        integer(hero["mp"]),
                        strings(hero["skills"]),
                        tuple(
                            (EquipmentSlot(text(slot)), text(item))
                            for slot, item in pairs(hero["equipment"])
                        ),
                    )
                )
            inventory = []
            for entry in sequence(data["inventory"]):
                stack = object_fields(entry, {"id", "quantity"})
                inventory.append(StackSave(text(stack["id"]), integer(stack["quantity"])))
            shops = []
            for entry in sequence(data["shops"]):
                shop = object_fields(entry, {"id", "stock"})
                shops.append(
                    ShopSave(
                        text(shop["id"]),
                        tuple((text(key), integer(value)) for key, value in pairs(shop["stock"])),
                    )
                )
            random = object_fields(data["random"], {"version", "values", "gaussian"})
            checkpoint = RandomCheckpoint(
                integer(random["version"]),
                tuple(integer(entry) for entry in sequence(random["values"])),
                number(random["gaussian"]) if random["gaussian"] is not None else None,
            )
            return GameSnapshot(
                integer(data["version"]),
                integer(data["content_version"]),
                position(data["position"]),
                position(data["origin"]),
                tuple(heroes),
                tuple(inventory),
                integer(data["gold"]),
                strings(data["opened_chests"]),
                strings(data["cleared_encounters"]),
                strings(data["visited_maps"]),
                strings(data["talked_to"]),
                strings(data["flags"]),
                tuple(
                    (text(key), QuestStatus(text(value))) for key, value in pairs(data["quests"])
                ),
                tuple(shops),
                number(data["play_seconds"]),
                checkpoint,
            )
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
            raise SaveError(f"Fichier de sauvegarde invalide : {error}") from error
