"""Politique basique injectable ; aucune mutation ni validation privilégiée."""

from dataclasses import dataclass
from typing import Protocol

from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import Action, BattleCommand, RandomSource
from JRPG.domain.errors import DomainError
from JRPG.domain.stats import require_text


class ActionPolicy(Protocol):
    def choose(self, battle: Battle, random: RandomSource) -> BattleCommand: ...


class BasicAI:
    def choose(self, battle: Battle, random: RandomSource) -> BattleCommand:
        legal = battle.legal_commands()
        offensive = tuple(
            command for command in legal if command.action in {Action.ATTACK, Action.SKILL}
        )
        choices = offensive or tuple(command for command in legal if command.action == Action.PASS)
        return choices[random.randint(0, len(choices) - 1)]


@dataclass(frozen=True, slots=True)
class TelegraphPattern:
    preparation: str
    attack: str
    status: str

    def __post_init__(self) -> None:
        for identity in (self.preparation, self.attack, self.status):
            require_text(identity)
        if self.preparation == self.attack:
            raise DomainError("La préparation doit être distincte de l'attaque.")


class TelegraphedAI:
    """Alterner préparation/frappe à partir de l'état réel, sans compteur caché.

    Les autres combattants et les tours empêchés utilisent la politique de repli.
    Une interruption qui efface la charge impose une nouvelle préparation.
    """

    def __init__(self, pattern: TelegraphPattern, fallback: ActionPolicy | None = None) -> None:
        self._pattern = pattern
        self._fallback = fallback if fallback is not None else BasicAI()

    def choose(self, battle: Battle, random: RandomSource) -> BattleCommand:
        actor = battle.current
        pattern = self._pattern
        if actor is not None and {pattern.preparation, pattern.attack} <= set(actor.skills):
            charged = any(entry.definition.id == pattern.status for entry in actor.statuses)
            preferred = pattern.attack if charged else pattern.preparation
            choices = tuple(
                command
                for command in battle.legal_commands()
                if command.action == Action.SKILL and command.ability_id == preferred
            )
            if choices:
                return choices[random.randint(0, len(choices) - 1)]
            # Ne jamais laisser le repli déclencher une frappe non annoncée.
            safe = tuple(
                command
                for command in battle.legal_commands()
                if command.action != Action.SKILL or command.ability_id != pattern.attack
            )
            if safe:
                return safe[random.randint(0, len(safe) - 1)]
        return self._fallback.choose(battle, random)
