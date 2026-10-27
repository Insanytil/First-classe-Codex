"""Ennemis du premier chapitre, indépendants de l’interface."""
from poo.characters import Monster


def flan() -> Monster:
    return Monster("Flandwich", strength=14, magic=1, defense=18,
                   resistance=4, xp=150, gil=50, mp=0, hp=300)


def wolf() -> Monster:
    return Monster("WolferInn", hp=280, mp=0, strength=16, magic=1,
                   defense=6, resistance=8, level=2, xp=200, gil=60)
