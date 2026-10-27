"""Objets-valeurs de caractéristiques et modificateurs signés."""

from dataclasses import dataclass, fields

from JRPG.domain.errors import DomainError


def require_integer(value: int, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise DomainError(f"Entier >= {minimum} attendu : {value!r}")


def require_text(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DomainError("Identifiant ou nom vide.")


@dataclass(frozen=True, slots=True)
class StatModifiers:
    hp: int = 0
    mp: int = 0
    strength: int = 0
    defense: int = 0
    magic: int = 0
    resistance: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0
    critical: int = 0

    def __post_init__(self) -> None:
        if any(type(getattr(self, field.name)) is not int for field in fields(self)):
            raise DomainError("Les modificateurs doivent être des entiers signés.")


@dataclass(frozen=True, slots=True)
class CharacterStats:
    hp: int
    mp: int
    strength: int
    defense: int
    magic: int
    resistance: int
    speed: int
    accuracy: int = 100
    evasion: int = 0
    critical: int = 0

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            require_integer(value, 1 if field.name == "hp" else 0)
            if field.name in {"accuracy", "evasion", "critical"} and value > 100:
                raise DomainError("Les pourcentages doivent être compris entre 0 et 100.")

    def modified(self, modifiers: StatModifiers, factor: int = 1) -> CharacterStats:
        require_integer(factor)
        values: dict[str, int] = {}
        for field in fields(self):
            value = getattr(self, field.name) + getattr(modifiers, field.name) * factor
            value = max(1 if field.name == "hp" else 0, value)
            values[field.name] = (
                min(100, value) if field.name in {"accuracy", "evasion", "critical"} else value
            )
        return CharacterStats(**values)
