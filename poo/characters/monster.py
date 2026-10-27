from __future__ import annotations

from poo.characters import Hero


class Monster:
    BASE_HP = 600
    BASE_MP = 60
    DAMAGE_CAP = 9999
    def __init__(
            self,
            name: str = "",
            strength: int = 1,
            magic: int  = 1,
            defense: int = 1,
            resistance: int = 1,
            level: int = 1,
            xp: int = 0,
            gil: int = 0,
            hp: int = BASE_HP,
            mp: int = BASE_MP

    ):
        if min(strength, magic, defense, resistance, level) < 1:
            raise ValueError("Toutes les statistiques doivent au moins être égale ou supérieure à 1")
        if hp <= 0 or mp < 0 or xp < 0 or gil < 0:
            raise ValueError("PV doit être positif ; PM, XP et gils doivent être positifs ou nuls")
        self.name = name
        self._level: int = level
        self._strength: int = strength
        self._magic: int = magic
        self._defense: int = defense
        self._resistance: int = resistance
        self._max_hp: int = hp
        self._max_mp: int = mp

        self._hp = self._max_hp
        self._mp = self._max_mp
        self._xp: int = xp
        self._gil : int = gil

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name_value: str) -> None:
        value = name_value.strip()

        if not value:
            raise ValueError("Name must not be empty")

        if len(value) < 3:
            raise ValueError("Name must not be less than 3 characters")

        if any(char.isdigit() for char in value):
            raise ValueError("Name must not contain digit")
        if not value.isalpha():
            raise ValueError("Name must only contain alphanumeric characters")

        self._name = value

    @property
    def level(self) -> int:
        return self._level


    @property
    def strength(self) -> int:
        return self._strength
    @property
    def magic(self) -> int:
        return self._magic
    @property
    def defense(self) -> int:
        return self._defense
    @property
    def resistance(self) -> int:
        return self._resistance
    @property
    def hp(self) -> int:
        return self._hp
    @property
    def mp(self) -> int:
        return self._mp

    @property
    def xp(self) -> int:
        return self._xp

    @property
    def gil(self) -> int:
        return self._gil
    @property
    def hp_ratio(self) -> float | int:
        return self._hp /  self._max_hp
    @property
    def is_alive(self) -> bool:
        return self._hp > 0
    @property
    def max_hp(self) -> int:
        return self._max_hp

    @property
    def max_mp(self):
        return self._max_mp
    def take_damage(self, val: int)-> int:
        if not self.is_alive:
            return 0

        if val < 0:
            raise ValueError("Les dégâts doivent être positifs ou nuls")
        lost = min(val, self._hp)
        self._hp -= lost
        return lost

    def heal(self, val: int) -> int:
        if not self.is_alive:
            return 0
        if val < 0:
            raise ValueError("Les soins doivent être positifs ou nuls")
        gain = min(val, self._max_hp - self._hp)

        self._hp += gain
        return gain

    def attack(self, target: Hero | Monster) -> int:
        damage = self.strength * 10 - target.defense * 5
        damage = max(1, min(damage, target.DAMAGE_CAP))
        damage = target.take_damage(damage)
        return damage
