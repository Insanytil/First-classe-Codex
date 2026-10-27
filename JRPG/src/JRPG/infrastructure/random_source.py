"""Adaptateur pseudo-aléatoire local, sans modifier le générateur global."""

from math import isfinite
from random import Random

from JRPG.application.save_data import RandomCheckpoint
from JRPG.domain.errors import DomainError


class SeededRandom:
    def __init__(self, seed: int | None = None) -> None:
        self._random = Random(seed)

    def randint(self, minimum: int, maximum: int) -> int:
        return self._random.randint(minimum, maximum)

    def checkpoint(self) -> RandomCheckpoint:
        version, values, gaussian = self._random.getstate()
        return RandomCheckpoint(version, tuple(values), gaussian)

    def restore_checkpoint(self, checkpoint: RandomCheckpoint) -> None:
        if (
            type(checkpoint.version) is not int
            or any(type(value) is not int or value < 0 for value in checkpoint.values)
            or checkpoint.gaussian is not None
            and not isfinite(checkpoint.gaussian)
        ):
            raise DomainError("État aléatoire invalide.")
        try:
            candidate = Random()
            native = candidate.getstate()
            if checkpoint.version != native[0] or len(checkpoint.values) != len(native[1]):
                raise DomainError("État aléatoire incompatible.")
            candidate.setstate((checkpoint.version, tuple(checkpoint.values), checkpoint.gaussian))
        except (ValueError, TypeError, OverflowError, IndexError) as error:
            raise DomainError("État aléatoire incompatible.") from error
        self._random = candidate
