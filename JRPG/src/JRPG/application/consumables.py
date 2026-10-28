"""Usage hors combat : réutiliser les effets sûrs et transférer une seule unité."""

from dataclasses import replace

from JRPG.application.exploration import ExplorationSession
from JRPG.domain.characters import Character
from JRPG.domain.combat.effects import Heal, RestoreMana, Revive
from JRPG.domain.combat.model import Combatant, Consumable, TargetLife, TargetSide
from JRPG.domain.errors import DomainError
from JRPG.domain.items import Inventory


class NoRandom:
    def randint(self, minimum: int, maximum: int) -> int:
        raise DomainError("Cet effet nécessite un combat.")


def usable_outside_combat(definition: Consumable) -> bool:
    ability = definition.ability
    return (
        ability.targeting.side != TargetSide.ENEMY
        and not ability.targeting.multiple
        and all(isinstance(effect, (Heal, Revive, RestoreMana)) for effect in ability.effects)
    )


def use_consumable(session: ExplorationSession, item_id: str, character_id: str) -> None:
    if session.active_encounter is not None:
        raise DomainError("Utilisez les commandes du combat.")
    definition = next(
        (entry for entry in session.encounter_factory.consumables if entry.item.id == item_id), None
    )
    member = next((entry for entry in session.party.members if entry.id == character_id), None)
    if definition is None or member is None:
        raise DomainError("Objet ou personnage inconnu.")
    ability = definition.ability
    if not usable_outside_combat(definition):
        raise DomainError("Objet inutilisable hors combat.")
    if member.is_knocked_out != (ability.targeting.life == TargetLife.KO):
        raise DomainError("Cible incompatible avec cet objet.")
    candidate = Inventory(session.inventory.stacks)
    candidate.remove(definition.item)
    actor = Combatant.from_character(member)
    target = actor
    for effect in ability.effects:
        target, _ = effect.apply(actor, target, NoRandom())
    state = replace(member.snapshot(), hp=target.hp, mp=target.mp)
    Character.from_state(member.definition, state, member.progression)
    session.inventory.remove(definition.item)
    member.apply_state(state)
