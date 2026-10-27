from __future__ import annotations

from typing import TYPE_CHECKING
from poo.characters.jobs import WEAPONS, job

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
            potions: int = 3,
            class_id: str = 'warrior'

    ):
        if min(strength, magic, defense, resistance, level) < 1:
            raise ValueError("Toutes les statistiques doivent au moins être égale ou supérieure à 1")
        if potions < 0:
            raise ValueError("Le nombre de potions doit être positif ou nul")
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
        self.defending = False
        self.class_id = job(class_id).id
        self.weapons = {self.job.starter}
        self.weapon_id = self.job.starter
        self.shield = 0

    @property
    def job(self):
        return job(self.class_id)

    @property
    def weapon(self):
        return WEAPONS[self.weapon_id]

    def equip(self, weapon_id: str) -> bool:
        if weapon_id not in self.weapons or weapon_id not in WEAPONS:
            return False
        if WEAPONS[weapon_id].job != self.class_id:
            return False
        self.weapon_id = weapon_id
        return True

    def buy_weapon(self, weapon_id: str) -> bool:
        weapon = WEAPONS.get(weapon_id)
        if weapon is None or weapon.job != self.class_id or weapon_id in self.weapons or self.gil < weapon.price:
            return False
        self.gil -= weapon.price
        self.weapons.add(weapon_id)
        return True

    def restore_mp(self, amount: int) -> None:
        self.mp = min(self.max_mp, self.mp + max(0, amount))
    # ------- Getter and Setter ---------
    @property
    def name(self) -> str:
        return self._name
    @name.setter
    def name(self, name_value: str) -> None:
        value = name_value.strip()

        if not value:
            raise ValueError("Le nom ne peut pas être vide")

        if len(value) < 3:
            raise ValueError("Le nom doit contenir au moins 3 lettres")

        if any(char.isdigit() for char in value):
            raise ValueError("Le nom ne doit pas contenir de chiffres")
        if not value.isalpha():
            raise ValueError("Le nom doit contenir uniquement des lettres")

        self._name = value
    @property
    def strength(self) -> int:
        return self._strength + self.weapon.strength
    @property
    def magic(self) -> int:
        return self._magic + self.weapon.magic
    @property
    def defense(self) -> int:
        return self._defense + self.weapon.defense
    @property
    def resistance(self) -> int:
        return self._resistance + self.weapon.resistance
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

        if val < 0:
            raise ValueError("Les dégâts doivent être positifs ou nuls")
        if self.defending:
            val = max(1, val // 2) if val else 0
        absorbed = min(self.shield, val)
        self.shield -= absorbed
        val -= absorbed
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
        if potions < 0:
            raise ValueError("Le nombre de potions doit être positif ou nul")
        self.potions += potions

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


