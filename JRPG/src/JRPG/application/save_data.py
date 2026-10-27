"""Instantanés typés : références au contenu, jamais définitions ou objets SDL."""

from dataclasses import dataclass

from JRPG.domain.items import EquipmentSlot
from JRPG.domain.quests import QuestStatus
from JRPG.domain.world import MapPosition


@dataclass(frozen=True, slots=True)
class RandomCheckpoint:
    version: int
    values: tuple[int, ...]
    gaussian: float | None = None


@dataclass(frozen=True, slots=True)
class HeroSave:
    id: str
    class_id: str
    experience: int
    hp: int
    mp: int
    skills: tuple[str, ...]
    equipment: tuple[tuple[EquipmentSlot, str], ...]


@dataclass(frozen=True, slots=True)
class StackSave:
    id: str
    quantity: int


@dataclass(frozen=True, slots=True)
class ShopSave:
    id: str
    stock: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class GameSnapshot:
    version: int
    content_version: int
    position: MapPosition
    origin: MapPosition
    heroes: tuple[HeroSave, ...]
    inventory: tuple[StackSave, ...]
    gold: int
    opened_chests: tuple[str, ...]
    cleared_encounters: tuple[str, ...]
    visited_maps: tuple[str, ...]
    talked_to: tuple[str, ...]
    flags: tuple[str, ...]
    quests: tuple[tuple[str, QuestStatus], ...]
    shops: tuple[ShopSave, ...]
    play_seconds: float
    random: RandomCheckpoint
