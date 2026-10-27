"""Primitives strictes de validation aux frontières de contenu et persistance."""

from typing import cast

from JRPG.domain.errors import DomainError


class ContentError(DomainError):
    """Contenu manquant, mal formé ou référencé de manière incohérente."""


def record(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ContentError("Objet JSON attendu.")
    return cast(dict[str, object], value)


def sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ContentError("Liste JSON attendue.")
    return cast(list[object], value)


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentError("Texte non vide attendu.")
    return value


def integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ContentError("Entier positif ou nul attendu.")
    return value


def boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ContentError("Booléen attendu.")
    return value
