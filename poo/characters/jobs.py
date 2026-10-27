"""Classes, compétences et équipement ; aucune dépendance au rendu."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    cost: int
    effect: str
    power: float
    animation: str
    description: str
    cooldown: int = 0


@dataclass(frozen=True)
class Job:
    id: str
    name: str
    description: str
    starter: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class Weapon:
    id: str
    name: str
    job: str
    family: str
    strength: int = 0
    magic: int = 0
    defense: int = 0
    resistance: int = 0
    price: int = 0

    @property
    def bonuses(self) -> str:
        values = ((self.strength, 'FOR'), (self.magic, 'MAG'),
                  (self.defense, 'DÉF'), (self.resistance, 'RÉS'))
        return ' · '.join(f'+{value} {label}' for value, label in values if value) or 'Arme de départ'


SKILLS = {s.id: s for s in (
    Skill('cleave', 'Frappe puissante', 6, 'physical', 1.65, 'slash', 'Une frappe physique à 165 %.'),
    Skill('whirlwind', 'Tourbillon', 12, 'physical_all', 1.1, 'slash', 'Frappe tous les ennemis.', 2),
    Skill('rally', 'Second souffle', 10, 'heal', 1, 'heal', 'Rend 160 PV + 4 × Force.', 2),
    Skill('fire', 'Feu', 8, 'magic', 1, 'fire', 'Projectile de feu : puissance magique.'),
    Skill('frost', 'Givre', 10, 'slow', .9, 'frost', 'Dégâts magiques ; prochaine riposte réduite de 35 %.', 1),
    Skill('storm', 'Tempête', 14, 'magic_all', 1.1, 'storm', 'Frappe tous les ennemis avec la magie.', 2),
    Skill('aim', 'Tir précis', 6, 'pierce', 1.5, 'shoot', 'Tir puissant qui ignore la moitié de la défense.'),
    Skill('venom', 'Flèche venimeuse', 8, 'poison', 1, 'shoot', 'Tir puis poison pendant trois tours.', 2),
    Skill('volley', 'Salve', 12, 'physical_all', 1, 'shoot', 'Une flèche sur chaque ennemi.', 2),
    Skill('smite', 'Châtiment', 8, 'holy', 1.2, 'smash', 'Combine Force et Magie dans une frappe sacrée.'),
    Skill('mend', 'Lumière curative', 10, 'heal', 1, 'heal', 'Rend 160 PV + 4 × Magie.', 1),
    Skill('aegis', 'Égide', 8, 'shield', 1, 'ward', 'Absorbe 100 + 6 × Résistance dégâts.', 2),
)}

JOBS = {j.id: j for j in (
    Job('warrior', 'Guerrier', 'Mêlée · dégâts physiques et endurance', 'iron_sword', ('cleave', 'whirlwind', 'rally')),
    Job('mage', 'Mage', 'Distance · magie, givre et attaques de zone', 'ash_staff', ('fire', 'frost', 'storm')),
    Job('ranger', 'Rôdeur', 'Distance · précision, poison et salves', 'oak_bow', ('aim', 'venom', 'volley')),
    Job('paladin', 'Paladin', 'Mêlée · lumière, soins et protection', 'steel_hammer', ('smite', 'mend', 'aegis')),
)}

WEAPONS = {w.id: w for w in (
    Weapon('iron_sword', 'Épée de fer', 'warrior', 'sword'),
    Weapon('dawn_sword', 'Lame de l’aurore', 'warrior', 'sword', strength=5, defense=2, price=90),
    Weapon('ash_staff', 'Bâton de frêne', 'mage', 'staff'),
    Weapon('astral_staff', 'Bâton astral', 'mage', 'staff', magic=5, resistance=2, price=90),
    Weapon('oak_bow', 'Arc de chêne', 'ranger', 'bow'),
    Weapon('sylvan_bow', 'Arc sylvestre', 'ranger', 'bow', strength=5, magic=2, price=90),
    Weapon('steel_hammer', 'Marteau d’acier', 'paladin', 'hammer'),
    Weapon('oath_hammer', 'Marteau du serment', 'paladin', 'hammer', strength=3, magic=3, defense=2, price=90),
)}


def job(identifier: str) -> Job:
    if identifier not in JOBS:
        raise ValueError('Classe inconnue.')
    return JOBS[identifier]
