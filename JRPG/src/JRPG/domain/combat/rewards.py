"""Récompenses déclaratives et tirages pondérés, indépendants du règlement."""

from dataclasses import dataclass

from JRPG.domain.combat.model import RandomSource
from JRPG.domain.items import ItemQuantity
from JRPG.domain.stats import require_integer


@dataclass(frozen=True, slots=True)
class LootEntry:
    weight: int
    stack: ItemQuantity | None = None

    def __post_init__(self) -> None:
        require_integer(self.weight, 1)


@dataclass(frozen=True, slots=True)
class RewardBundle:
    experience: int = 0
    gold: int = 0
    items: tuple[ItemQuantity, ...] = ()

    def __post_init__(self) -> None:
        require_integer(self.experience)
        require_integer(self.gold)
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class RewardTable:
    experience: int = 0
    gold: int = 0
    guaranteed: tuple[ItemQuantity, ...] = ()
    weighted: tuple[LootEntry, ...] = ()
    rolls: int = 1

    def __post_init__(self) -> None:
        require_integer(self.experience)
        require_integer(self.gold)
        require_integer(self.rolls)
        object.__setattr__(self, "guaranteed", tuple(self.guaranteed))
        object.__setattr__(self, "weighted", tuple(self.weighted))

    def roll(self, random: RandomSource) -> RewardBundle:
        items = list(self.guaranteed)
        for _ in range(self.rolls if self.weighted else 0):
            draw = random.randint(1, sum(entry.weight for entry in self.weighted))
            for entry in self.weighted:
                draw -= entry.weight
                if draw <= 0:
                    if entry.stack is not None:
                        items.append(entry.stack)
                    break
        return RewardBundle(self.experience, self.gold, tuple(items))
