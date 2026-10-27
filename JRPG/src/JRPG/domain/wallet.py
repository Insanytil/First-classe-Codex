"""Monnaie du groupe ; le commerce sera introduit avec ses cas d'utilisation."""

from JRPG.domain.errors import DomainError
from JRPG.domain.stats import require_integer


class Wallet:
    def __init__(self, gold: int = 0) -> None:
        require_integer(gold)
        self._gold = gold

    @property
    def gold(self) -> int:
        return self._gold

    def credit(self, amount: int) -> None:
        require_integer(amount)
        self._gold += amount

    def debit(self, amount: int) -> None:
        require_integer(amount)
        if amount > self._gold:
            raise DomainError("Fonds insuffisants.")
        self._gold -= amount
