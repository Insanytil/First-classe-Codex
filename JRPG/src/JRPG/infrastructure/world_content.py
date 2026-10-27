"""Lecture et validation des cartes JSON embarquées ; aucun code évalué."""

import json
from importlib.resources import files

from JRPG.application.exploration import ExplorationSession
from JRPG.application.progression import AdventureProgress
from JRPG.domain.errors import DomainError
from JRPG.domain.items import EquipmentSlot, ItemDefinition, ItemQuantity
from JRPG.domain.world import (
    Decoration,
    DecorationKind,
    MapDefinition,
    MapObject,
    MapPosition,
    ObjectKind,
    Tile,
    World,
)
from JRPG.infrastructure.adventure_content import load_adventure_content
from JRPG.infrastructure.training_encounter import create_combat_setup
from JRPG.infrastructure.validation import ContentError as ContentError
from JRPG.infrastructure.validation import boolean, integer, record, sequence, text


class JsonMapLoader:
    def __init__(self, items: tuple[ItemDefinition, ...], enemies: frozenset[str]) -> None:
        self._items = {entry.id: entry for entry in items}
        self._enemies = enemies

    def decode(self, source: str) -> MapDefinition:
        try:
            data = record(json.loads(source))
            if integer(data["version"]) != 1:
                raise ContentError("Version de carte inconnue.")
            ground_rows = [text(row) for row in sequence(data["ground"])]
            ground = tuple(tuple(Tile(cell) for cell in row) for row in ground_rows)
            collision_rows = [text(row) for row in sequence(data["collision"])]
            if len(collision_rows) != len(ground_rows) or any(
                len(row) != len(ground_rows[index]) or set(row) - {"0", "1"}
                for index, row in enumerate(collision_rows)
            ):
                raise ContentError("Grille de collision incompatible.")
            blocked = frozenset(
                (x, y)
                for y, row in enumerate(collision_rows)
                for x, cell in enumerate(row)
                if cell == "1"
            )
            objects = tuple(self._object(record(entry)) for entry in sequence(data["objects"]))
            decorations = tuple(
                self._decoration(record(entry)) for entry in sequence(data["decorations"])
            )
            return MapDefinition(
                text(data["id"]), text(data["name"]), ground, blocked, objects, decorations
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ContentError(f"Carte invalide : {error}") from error

    def _object(self, data: dict[str, object]) -> MapObject:
        destination = None
        if "destination" in data:
            target = record(data["destination"])
            destination = MapPosition(
                text(target["map"]),
                (integer(target["x"]) + 0.5) * 32,
                (integer(target["y"]) + 0.5) * 32,
            )
        items: list[ItemQuantity] = []
        for entry in sequence(data.get("items", [])):
            stack = record(entry)
            key = text(stack["id"])
            if key not in self._items:
                raise ContentError(f"Objet inconnu : {key}")
            items.append(ItemQuantity(self._items[key], integer(stack["quantity"])))
        enemies = tuple(text(entry) for entry in sequence(data.get("enemies", [])))
        if any(key not in self._enemies for key in enemies):
            raise ContentError("Référence d'ennemi inconnue.")
        return MapObject(
            text(data["id"]),
            text(data["name"]),
            ObjectKind(text(data["kind"])),
            integer(data["x"]),
            integer(data["y"]),
            boolean(data.get("solid", True)),
            text(data["message"]) if "message" in data else "",
            destination,
            tuple(items),
            integer(data.get("gold", 0)),
            enemies,
        )

    @staticmethod
    def _decoration(data: dict[str, object]) -> Decoration:
        return Decoration(
            integer(data["x"]),
            integer(data["y"]),
            DecorationKind(text(data["kind"])),
            boolean(data.get("foreground", True)),
        )

    def load(self) -> tuple[MapDefinition, ...]:
        maps: list[MapDefinition] = []
        for name in ("village", "forest", "ruins"):
            try:
                source = (
                    files("JRPG.infrastructure.content")
                    .joinpath("maps", name + ".json")
                    .read_text(encoding="utf-8")
                )
                maps.append(self.decode(source))
            except (OSError, DomainError) as error:
                raise ContentError(f"{name}.json : {error}") from error
        return tuple(maps)


def create_exploration_session(
    seed: int = 7, position: MapPosition | None = None
) -> ExplorationSession:
    setup = create_combat_setup(seed)
    content = load_adventure_content(tuple(entry.item for entry in setup.factory.consumables))
    starters = {
        "guerrier": "iron_sword",
        "mage": "oak_staff",
        "soigneur": "healing_wand",
        "voleur": "twin_daggers",
    }
    for member in setup.party.members:
        # Croissance déclarée dans le catalogue des personnages de démonstration.
        item = content.item(starters[member.definition.character_class.id])
        setup.inventory.add(item)
        member.equip(setup.inventory, item, EquipmentSlot.WEAPON)
    loader = JsonMapLoader(content.items, frozenset(setup.factory.enemies))
    maps = loader.load()
    world = World(
        maps, position if position is not None else MapPosition("village", 8.5 * 32, 10.5 * 32)
    )
    content.validate_world(world)
    story = AdventureProgress(content, world.state, setup.party, setup.inventory, setup.wallet)
    return ExplorationSession(
        world, setup.party, setup.inventory, setup.wallet, setup.factory, story
    )
