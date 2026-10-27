"""État et règles du premier chapitre, indépendants de l'affichage."""
from dataclasses import dataclass, field

from poo.characters import Hero


@dataclass
class Chapter:
    completed: set[str] = field(default_factory=set)
    rescued: bool = False

    @property
    def gate_unlocked(self) -> bool:
        return {"road", "ruins"} <= self.completed


def buy_potion(hero: Hero) -> bool:
    if hero.gil < 25:
        return False
    hero.gil -= 25
    hero.add_potion(1)
    return True


def camp_rest(hero: Hero) -> None:
    """Le camp est un refuge : repos gratuit et restauration des PM."""
    hero.rest()
    hero.mp = hero.max_mp
