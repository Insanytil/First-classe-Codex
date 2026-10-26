from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pour l'éditeur seulement : monster.py importe déjà hero.py
    from poo.characters import Monster

class Hero:
    BASE_HP = 600
    BASE_MP = 60
    DAMAGE_CAP = 9999
    FIRE_COST = 8
    POTION = 200
    def __init__(
            self,
            name: str = "",
            strength: int = 1,
            magic: int  = 1,
            defense: int = 1,
            resistance: int = 1,
            level: int = 1,
            potions: int = 3

    ):
        if min(strength, magic, defense, resistance, level) < 1:
            raise ValueError("Toutes les statistiques doivent au moins être égale ou supérieure à 1")
        self.name = name
        self._level: int = level
        self._strength: int = strength
        self._magic: int = magic
        self._defense: int = defense
        self._resistance: int = resistance
        self._max_hp: int = self.BASE_HP
        self._max_mp: int = self.BASE_MP
        self._current_xp: int = 0
        self._hp : int = self._max_hp
        self._mp : int = self._max_mp
        self._gil: int = 0

        self._potions: int = potions
    # ------- Getter and Setter ---------
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
    def max_hp(self) -> int:
        return self._max_hp
    @property
    def mp(self) -> int:
        return self._mp

    @mp.setter
    def mp(self, mp_val: int) -> None:
        self._mp = mp_val
    @property
    def max_mp(self):
        return self._max_mp
    @property
    def hp_ratio(self) -> float | int:
        return self.hp /  self.max_hp
    @property
    def is_alive(self) -> bool:
        return self._hp > 0
    @property
    def can_cast_fire(self) -> bool:
        if self._mp < Hero.FIRE_COST:
            return False
        else:
            return True

    @property
    def potions(self) -> int:
        return self._potions

    @potions.setter
    def potions(self, potions: int) -> None:
        self._potions = potions
    @property
    def can_drink_potion(self) -> bool:
        if self.potions > 0:
            return True
        else:
            return False
    @property
    def level(self) -> int:
        return self._level
    @level.setter
    def level(self, level: int) -> None:
        self._level = level

    @property
    def current_xp(self) -> int:
        return self._current_xp
    @current_xp.setter
    def current_xp(self, value: int) -> None:
        self._current_xp = value

    @property
    def next_xp_level_up(self):
        return self.level * 100

    @property
    def gil(self) -> int:
        return self._gil

    @gil.setter
    def gil(self, amount: int) -> None:
        self._gil = amount



   # --------- methods ------------------
    def take_damage(self, val: int)-> int:
        if not self.is_alive:
            return 0

        lost = min(val, self._hp)
        self._hp -= lost
        return lost

    def heal(self, val: int) -> int:
        if not self.is_alive:
            return 0
        gain = min(val, self._max_hp - self._hp)

        self._hp += gain
        return gain

    def attack(self, target: Monster | Hero) -> int:
        damage = self.strength * 10 - target.defense * 5
        damage = max(1, min(damage, Hero.DAMAGE_CAP))
        return target.take_damage(damage)

    def cast_fire(self, target: Monster | Hero) -> int:
        if self.can_cast_fire:
            self.mp = self.mp - self.FIRE_COST
            magic_dmg = self.magic * 12 - target.resistance * 5
            magic_dmg = max(1, min(magic_dmg, Hero.DAMAGE_CAP))
            return target.take_damage(magic_dmg)
        else: return 0

    def drink_potion(self):
        if self.can_drink_potion:
            self.potions -= 1
            return self.heal(self.POTION)
        else:
            return 0

    def add_potion(self, potions: int):
        self.potions += self.potions + potions

    def gain_xp(self, amount:int) -> int:
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        self.current_xp += amount
        levels_gained = 0

        while self.current_xp >= self.next_xp_level_up:
            self.current_xp -= self.next_xp_level_up
            self.level += 1
            levels_gained += 1

            self._max_hp += 60

            self._strength += 2
            self._magic += 2
            self._defense += 2
            self._resistance += 2

        return levels_gained

    def gain_gil(self, amount: int):
        if amount < 0:
            raise ValueError("Received Gil amount cannot be negative")
        self.gil += amount

    def rest(self) -> int:
        return self.heal(self._max_hp)


