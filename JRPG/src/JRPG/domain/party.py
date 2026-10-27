"""Groupe actif ordonné ; la première place désigne le leader."""

from collections.abc import Iterable

from JRPG.domain.characters import Character
from JRPG.domain.errors import DomainError
from JRPG.domain.stats import require_integer


class Party:
    MAX_MEMBERS = 4

    def __init__(self, members: Iterable[Character] = ()) -> None:
        self._members: tuple[Character, ...] = ()
        for member in members:
            self.add(member)

    @property
    def members(self) -> tuple[Character, ...]:
        return self._members

    @property
    def leader(self) -> Character | None:
        return self._members[0] if self._members else None

    @property
    def all_knocked_out(self) -> bool:
        return bool(self._members) and all(member.is_knocked_out for member in self._members)

    def add(self, member: Character) -> None:
        if len(self._members) >= self.MAX_MEMBERS:
            raise DomainError("Équipe complète.")
        if any(existing.id == member.id for existing in self._members):
            raise DomainError("Identité déjà présente dans l'équipe.")
        self._members = (*self._members, member)

    def remove(self, character_id: str) -> None:
        self._find(character_id)
        self._members = tuple(member for member in self._members if member.id != character_id)

    def move(self, character_id: str, index: int) -> None:
        require_integer(index)
        if index >= len(self._members):
            raise DomainError("Position hors de l'équipe.")
        member = self._find(character_id)
        candidate = [existing for existing in self._members if existing.id != character_id]
        candidate.insert(index, member)
        self._members = tuple(candidate)

    def _find(self, character_id: str) -> Character:
        for member in self._members:
            if member.id == character_id:
                return member
        raise DomainError("Personnage absent de l'équipe.")
