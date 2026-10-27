"""Dépendances d'un affrontement, assemblées à la périphérie."""

from dataclasses import dataclass

from JRPG.application.battle_session import BattleSession
from JRPG.domain.combat.ai import ActionPolicy
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import Ability, Consumable, RandomSource


@dataclass(frozen=True, slots=True)
class BattleEncounter:
    battle: Battle
    session: BattleSession
    random: RandomSource
    ai: ActionPolicy
    abilities: tuple[Ability, ...]
    consumables: tuple[Consumable, ...]
