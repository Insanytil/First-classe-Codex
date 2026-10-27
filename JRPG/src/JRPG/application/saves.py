"""Ports de sauvegarde et chargement sans remplacer une partie avant validation."""

from typing import Protocol

from JRPG.application.exploration import ExplorationSession
from JRPG.application.save_data import GameSnapshot
from JRPG.domain.errors import DomainError


class SaveError(DomainError):
    """Fichier absent, corrompu, incompatible ou non inscriptible."""


class SaveRepository(Protocol):
    def write(self, slot: int, snapshot: GameSnapshot) -> None: ...
    def read(self, slot: int) -> GameSnapshot: ...
    def exists(self, slot: int) -> bool: ...


class SnapshotMapper(Protocol):
    def capture(self, session: ExplorationSession) -> GameSnapshot: ...
    def restore(self, snapshot: GameSnapshot) -> ExplorationSession: ...


class SaveService:
    def __init__(self, repository: SaveRepository, mapper: SnapshotMapper) -> None:
        self._repository, self._mapper = repository, mapper

    def save(self, slot: int, session: ExplorationSession) -> None:
        self._repository.write(slot, self._mapper.capture(session))

    def load(self, slot: int) -> ExplorationSession:
        return self._mapper.restore(self._repository.read(slot))

    def exists(self, slot: int) -> bool:
        return self._repository.exists(slot)
