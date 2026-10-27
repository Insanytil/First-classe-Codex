"""Découpage et temps du prologue, indépendants du rendu graphique."""
from dataclasses import dataclass

DUEL_DURATION = 3.8


@dataclass(frozen=True)
class ProloguePage:
    speaker: str
    text: str
    scene: str
    minimum_duration: float = 0


PROLOGUE_PAGES = (
    ProloguePage('Cloud', 'Nibelheim… Les mêmes toits, le même château d’eau. Mais ce feu… Il ne reste plus personne dans la rue.', 'village'),
    ProloguePage('Une voix dans les flammes', 'Cloud ! Le réacteur ! Il nous attend là-haut !', 'fire'),
    ProloguePage('Sephiroth', 'Tu as traversé les flammes pour venir jusqu’à moi. Regarde bien ce monde, Cloud. Il appartient déjà aux cendres.', 'reveal'),
    ProloguePage('Le choc des lames', 'Cloud lève son épée. L’aile noire masque les flammes. Un seul coup de katana brise son élan.', 'duel', DUEL_DURATION),
    ProloguePage('Sephiroth', 'Tu n’es qu’une marionnette. Et pourtant… tu t’accroches encore.', 'defeat'),
    ProloguePage('Cinq ans plus tard', 'Au camp des voyageurs de Dalmasca, un aventurier s’éveille avec le souvenir d’un village en flammes. Votre histoire commence ici.', 'morning'),
)
