"""Boutiques à prix et stocks explicites, sans accès à la présentation."""

from dataclasses import dataclass

from JRPG.domain.errors import DomainError
from JRPG.domain.items import Inventory, ItemDefinition, ItemQuantity
from JRPG.domain.stats import require_integer, require_text
from JRPG.domain.wallet import Wallet


@dataclass(frozen=True, slots=True)
class ShopOffer:
    item: ItemDefinition
    buy_price: int
    sell_price: int
    initial_stock: int

    def __post_init__(self) -> None:
        for amount in (self.buy_price, self.sell_price, self.initial_stock):
            require_integer(amount)
        if self.sell_price > self.buy_price:
            raise DomainError("Le prix de vente dépasse le prix d'achat.")


@dataclass(frozen=True, slots=True)
class ShopDefinition:
    id: str
    name: str
    offers: tuple[ShopOffer, ...]

    def __post_init__(self) -> None:
        require_text(self.id)
        require_text(self.name)
        object.__setattr__(self, "offers", tuple(self.offers))
        if len({entry.item.id for entry in self.offers}) != len(self.offers):
            raise DomainError("Offre dupliquée.")


class Shop:
    def __init__(
        self,
        identity: str,
        name: str,
        offers: tuple[ShopOffer, ...],
        stock: tuple[tuple[str, int], ...] | None = None,
    ) -> None:
        require_text(identity)
        require_text(name)
        self._id, self._name = identity, name
        self._entries = tuple(offers)
        self._offers = {offer.item.id: offer for offer in offers}
        if len(self._offers) != len(offers):
            raise DomainError("Offre dupliquée.")
        self._stock = {entry.item.id: entry.initial_stock for entry in offers}
        if stock is not None:
            values = dict(stock)
            if len(values) != len(stock) or set(values) != set(self._stock):
                raise DomainError("Stock incomplet ou dupliqué.")
            for quantity in values.values():
                require_integer(quantity)
            self._stock = values

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def offers(self) -> tuple[ShopOffer, ...]:
        return self._entries

    @property
    def stock(self) -> tuple[tuple[str, int], ...]:
        return tuple(sorted(self._stock.items()))

    def offer(self, item_id: str) -> ShopOffer:
        if item_id not in self._offers:
            raise DomainError("Le marchand ne négocie pas cet objet.")
        return self._offers[item_id]

    def buy(self, item_id: str, quantity: int, inventory: Inventory, wallet: Wallet) -> None:
        stack = ItemQuantity(self.offer(item_id).item, quantity)
        cost = self.offer(item_id).buy_price * quantity
        if self._stock[item_id] < quantity:
            raise DomainError("Stock insuffisant.")
        if wallet.gold < cost:
            raise DomainError("Fonds insuffisants.")
        candidate = Inventory(inventory.stacks)
        candidate.add(stack.item, quantity)
        inventory.add(stack.item, quantity)
        wallet.debit(cost)
        self._stock[item_id] -= quantity

    def sell(self, item_id: str, quantity: int, inventory: Inventory, wallet: Wallet) -> None:
        offer = self.offer(item_id)
        candidate = Inventory(inventory.stacks)
        candidate.remove(offer.item, quantity)
        inventory.remove(offer.item, quantity)
        wallet.credit(offer.sell_price * quantity)
        self._stock[item_id] += quantity
