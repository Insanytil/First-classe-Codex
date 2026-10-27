"""Combat animé piloté par update(dt), sans pause bloquante."""
from dataclasses import dataclass, field

from poo.characters import Hero, Monster
from poo.characters.jobs import SKILLS


@dataclass
class Motion:
    kind: str
    actor: int  # -1 : héros, sinon index ennemi
    target: int
    elapsed: float = 0.0
    duration: float | None = None
    impact_applied: bool = field(default=False, init=False)
    skill_id: str | None = None

    def __post_init__(self):
        if self.duration is None:
            self.duration = {'slash': 1.15, 'claw': 1.05, 'jump': 1.35,
                             'heavy': 1.45, 'charge': .9, 'fire': 1.1,
                             'heal': .9, 'guard': .6, 'shoot': 1.1, 'smash': 1.3,
                             'arcane': 1.1, 'frost': 1.2, 'storm': 1.4, 'ward': 1.0}.get(self.kind, .65)

    @property
    def impact_ratio(self) -> float:
        return {'jump': .62, 'heavy': .66, 'charge': .85,
                'heal': .42, 'guard': .35}.get(self.kind, .55)

    @property
    def contact_time(self) -> float:
        return self.duration * self.impact_ratio

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)


class Battle:
    def __init__(self, hero: Hero, monsters: list[Monster]):
        self.hero = hero
        self.monsters = monsters
        self.target = 0
        self.motion: Motion | None = None
        self.queue: list[Motion] = []
        self.log = ['Choisissez une action. TAB ou fleches : changer de cible.']
        self.result: bool | None = None
        self.turn = 1
        self.rewarded = False
        self.cooldowns: dict[str, int] = {}
        self.poison: dict[int, int] = {}
        self.chilled: set[int] = set()

    @property
    def actions(self):
        primary, second, third = self.hero.job.skills
        basic = {'sword': 'Attaquer', 'staff': 'Trait arcanique', 'bow': 'Tirer', 'hammer': 'Frapper'}[self.hero.weapon.family]
        return (('1', basic + ' · +4 PM', None), ('2', SKILLS[primary].name, primary),
                ('3', f'Potion ({self.hero.potions})', None), ('4', 'Garde', None),
                ('5', SKILLS[second].name, second), ('6', SKILLS[third].name, third))

    def unavailable(self, action: str) -> str:
        if action not in {key for key, _, _ in self.actions}:
            return 'Action inconnue.'
        if action == '3' and not self.hero.can_drink_potion:
            return 'Plus de potions.'
        skill_id = next(skill for key, _, skill in self.actions if key == action)
        if skill_id:
            if self.hero.mp < SKILLS[skill_id].cost:
                return 'Pas assez de PM.'
            remaining = self.cooldowns.get(skill_id, 0)
            if remaining:
                return f'Compétence disponible dans {remaining} tour(s).'
            if SKILLS[skill_id].effect == 'heal' and self.hero.hp == self.hero.max_hp:
                return 'Vos PV sont déjà au maximum.'
        return ''

    def cycle(self, step: int = 1) -> None:
        alive = [i for i, m in enumerate(self.monsters) if m.is_alive]
        if alive:
            position = alive.index(self.target) if self.target in alive else 0
            self.target = alive[(position + step) % len(alive)]

    def choose(self, action: str) -> bool:
        if self.motion or self.result is not None:
            return False
        if action not in {key for key, _, _ in self.actions}:
            return False
        reason = self.unavailable(action)
        if reason:
            self.log.append(reason)
            return False
        self.hero.defending = action == '4'
        skill_id = next(skill for key, _, skill in self.actions if key == action)
        basic = {'sword': 'slash', 'staff': 'arcane', 'bow': 'shoot', 'hammer': 'smash'}[self.hero.weapon.family]
        kind = SKILLS[skill_id].animation if skill_id else {'1': basic, '3': 'heal', '4': 'guard'}[action]
        self.motion = Motion(kind, -1, self.target, skill_id=skill_id)
        self.queue = [Motion(self.enemy_motion(monster), i, -1)
                      for i, monster in enumerate(self.monsters)]
        return True

    @staticmethod
    def enemy_motion(monster: Monster) -> str:
        if monster.name == 'WolferInn':
            return 'claw'
        if monster.name == 'Flandwich':
            return 'jump'
        if hasattr(monster, 'charged'):
            return 'heavy' if monster.charged else 'charge'
        return 'enemy'

    def _impact(self, motion: Motion) -> None:
        if motion.actor == -1:
            target = self.monsters[motion.target]
            if motion.skill_id:
                self._skill(motion)
            elif motion.kind == 'heal':
                self.log.append(f'Potion : +{self.hero.drink_potion()} PV.')
            elif motion.kind == 'guard':
                self.log.append('Vous levez votre garde. Degats recus divises par deux.')
            else:
                if self.hero.class_id == 'mage':
                    damage = target.take_damage(max(1, min(Hero.DAMAGE_CAP, self.hero.magic * 10 - target.resistance * 5)))
                else:
                    damage = self.hero.attack(target)
                self.hero.restore_mp(4)
                self.log.append(f'{self.hero.name} frappe {target.name} : {damage} dégâts. +4 PM.')
        else:
            monster = self.monsters[motion.actor]
            if motion.actor in self.chilled:
                # Appliquer la réduction avant garde/bouclier, sans modifier le monstre.
                class ChilledTarget:
                    DAMAGE_CAP = Hero.DAMAGE_CAP
                    defense = self.hero.defense
                    resistance = self.hero.resistance
                    def take_damage(_, amount):
                        return self.hero.take_damage(round(amount * .65))
                damage = monster.attack(ChilledTarget())
                if motion.kind != 'charge':
                    self.chilled.discard(motion.actor)
            else:
                damage = monster.attack(self.hero)
            self.log.append(f'{monster.name} charge son arme !' if motion.kind == 'charge' else f'{monster.name} : {damage} dégâts.')

    def _skill(self, motion: Motion) -> None:
        skill = SKILLS[motion.skill_id]
        hero = self.hero
        hero.mp -= skill.cost
        self.cooldowns[skill.id] = skill.cooldown + 1 if skill.cooldown else 0
        if skill.effect == 'heal':
            stat = hero.strength if skill.id == 'rally' else hero.magic
            self.log.append(f'{skill.name} : +{hero.heal(160 + stat * 4)} PV.')
            return
        if skill.effect == 'shield':
            hero.shield = max(hero.shield, 100 + hero.resistance * 6)
            self.log.append(f'Égide : {hero.shield} dégâts absorbables.')
            return
        targets = range(len(self.monsters)) if skill.effect.endswith('_all') else (motion.target,)
        for index in targets:
            target = self.monsters[index]
            if not target.is_alive:
                continue
            if skill.effect in ('magic', 'magic_all', 'slow'):
                base = hero.magic * 12 * skill.power - target.resistance * 5
            elif skill.effect == 'holy':
                base = (hero.strength + hero.magic) * 6 * skill.power - target.resistance * 4
            else:
                base = hero.strength * 10 * skill.power - target.defense * (2.5 if skill.effect == 'pierce' else 5)
            damage = target.take_damage(max(1, min(Hero.DAMAGE_CAP, round(base))))
            self.log.append(f'{skill.name} · {target.name} : {damage} dégâts.')
            if target.is_alive and skill.effect == 'poison':
                self.poison[index] = 3
            if target.is_alive and skill.effect == 'slow':
                self.chilled.add(index)

    def _poison_tick(self):
        for index, turns in list(self.poison.items()):
            monster = self.monsters[index]
            if monster.is_alive:
                amount = monster.take_damage(18 + self.hero.magic * 2)
                self.log.append(f'Poison · {monster.name} : {amount} dégâts.')
            if turns <= 1 or not monster.is_alive:
                del self.poison[index]
            else:
                self.poison[index] = turns - 1

    def _finish(self) -> bool:
        if not self.hero.is_alive:
            self.result = False
        elif not any(monster.is_alive for monster in self.monsters):
            self.result = True
            if not self.rewarded:
                xp, gil = sum(m.xp for m in self.monsters), sum(m.gil for m in self.monsters)
                levels = self.hero.gain_xp(xp)
                self.hero.gain_gil(gil)
                self.log.append(f'VICTOIRE ! +{xp} XP, +{gil} gils, +{levels} niveau(x).')
                self.rewarded = True
        if self.result is not None:
            self.hero.defending = False
            self.hero.shield = 0
            self.queue.clear()
            return True
        return False

    def update(self, dt: float) -> None:
        if not self.motion or self.result is not None:
            return
        self.motion.elapsed += max(0, dt)
        if not self.motion.impact_applied and self.motion.elapsed >= self.motion.contact_time:
            self.motion.impact_applied = True
            self._impact(self.motion)
        # Le contact ne coupe pas l'animation : recul et retour terminent le geste.
        if self.motion.elapsed < self.motion.duration:
            return
        self.motion = None
        if self._finish():
            return
        while self.queue:
            candidate = self.queue.pop(0)
            if self.monsters[candidate.actor].is_alive:
                self.motion = candidate
                return
        self.hero.defending = False
        self._poison_tick()
        if self._finish():
            return
        self.cooldowns = {key: max(0, turns - 1) for key, turns in self.cooldowns.items()}
        self.turn += 1
        if not self.monsters[self.target].is_alive:
            self.cycle()
