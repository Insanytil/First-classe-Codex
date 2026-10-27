"""Politique basique injectable ; aucune mutation ni validation privilégiée."""

from typing import Protocol

from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import Action, BattleCommand, RandomSource


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
