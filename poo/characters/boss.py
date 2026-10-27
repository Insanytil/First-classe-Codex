from poo.characters import Hero, Monster


class Gatekeeper(Monster):
    """Deux temps lisibles : préparation puis frappe lourde."""

    def __init__(self):
        super().__init__("Sentinelle", hp=1000, mp=0, strength=24,
                         magic=12, defense=16, resistance=12, level=4, xp=600, gil=150)
        self.charged = False

    @property
    def intent(self) -> str:
        return "FRAPPE LOURDE au prochain tour · défendez-vous !" if self.charged else "Se prépare à charger son arme"

    def attack(self, target: Hero | Monster) -> int:
        if not self.charged:
            self.charged = True
            return 0
        self.charged = False
        damage = max(1, self.strength * 18 - target.defense * 5)
        return target.take_damage(damage)
