"""Brouillon de personnage : budget et validation indépendants du rendu."""
from dataclasses import dataclass, field

from poo.characters import Hero

BASE_STAT = 10
POINT_BUDGET = 20
NAME_LIMIT = 18
STAT_KEYS = ('strength', 'magic', 'defense', 'resistance')
STAT_LABELS = (
    ('strength', 'Force', 'Puissance des attaques physiques'),
    ('magic', 'Magie', 'Puissance des sorts'),
    ('defense', 'Défense', 'Protection contre les attaques physiques'),
    ('resistance', 'Résistance', 'Protection contre la magie'),
)
HAIR_COLORS = (
    ('Blond', (192, 162, 91)),
    ('Châtain', (118, 79, 54)),
    ('Brun', (60, 44, 40)),
    ('Roux', (181, 83, 49)),
    ('Argent', (190, 202, 209)),
    ('Noir', (30, 35, 43)),
    ('Bleu', (71, 121, 174)),
    ('Violet', (143, 92, 164)),
)
DEFAULT_HAIR = HAIR_COLORS[0][1]


@dataclass
class CharacterDraft:
    name: str = ''
    hair_color: tuple[int, int, int] = DEFAULT_HAIR
    points: dict[str, int] = field(default_factory=lambda: dict.fromkeys(STAT_KEYS, 0))
    class_id: str = 'warrior'

    @property
    def remaining(self) -> int:
        return POINT_BUDGET - sum(self.points.values())

    def value(self, stat: str) -> int:
        return BASE_STAT + self.points[stat]

    def adjust(self, stat: str, delta: int) -> bool:
        if stat not in STAT_KEYS or type(delta) is not int or delta not in (-1, 1):
            return False
        if delta > 0 and self.remaining <= 0:
            return False
        if self.points[stat] + delta < 0:
            return False
        self.points[stat] += delta
        return True

    def reset_points(self) -> None:
        self.points = dict.fromkeys(STAT_KEYS, 0)

    def build(self) -> Hero:
        if set(self.points) != set(STAT_KEYS) or any(type(value) is not int or value < 0 for value in self.points.values()):
            raise ValueError('La répartition des caractéristiques est invalide.')
        if self.remaining != 0:
            raise ValueError(f'Répartissez exactement les {POINT_BUDGET} points avant de partir.')
        if not isinstance(self.hair_color, tuple) or len(self.hair_color) != 3 or any(type(value) is not int or not 0 <= value <= 255 for value in self.hair_color):
            raise ValueError('La couleur de cheveux est invalide.')
        if len(self.name.strip()) > NAME_LIMIT:
            raise ValueError(f'Le nom doit contenir au maximum {NAME_LIMIT} lettres.')
        return Hero(name=self.name, class_id=self.class_id, **{stat: self.value(stat) for stat in STAT_KEYS})
