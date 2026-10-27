"""Règlement synchrone d'un combat : ressources, consommables et récompenses."""

from dataclasses import dataclass

from JRPG.domain.characters import Character
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import BattleRuleError, BattleState, Outcome, RandomSource, Side
from JRPG.domain.combat.rewards import RewardBundle, RewardTable
from JRPG.domain.items import EquipmentSlot, Inventory, ItemDefinition
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats
from JRPG.domain.wallet import Wallet


@dataclass(frozen=True, slots=True)
class CharacterSnapshot:
    stats: CharacterStats
    hp: int
    mp: int
    experience: int
    skills: tuple[str, ...]
    equipment: tuple[tuple[EquipmentSlot, ItemDefinition], ...]

    @classmethod
    def capture(cls, character: Character) -> CharacterSnapshot:
        return cls(
            character.stats,
            character.hp,
            character.mp,
            character.experience,
            character.skills,
            character.equipment,
        )


@dataclass(frozen=True, slots=True)
class SettlementResult:
    battle_id: str
    outcome: Outcome
    rewards: RewardBundle
    levels_gained: tuple[tuple[str, int], ...]


class BattleSession:
    """Prépare tous les changements avant publication ; idempotence en mémoire."""

    def __init__(
        self,
        battle: Battle,
        party: Party,
        inventory: Inventory,
        wallet: Wallet,
        rewards: RewardTable | None = None,
    ) -> None:
        if battle.state != BattleState.INITIALIZING:
            raise BattleRuleError("Créer la session avant de démarrer le combat.")
        allies = {
            fighter.id: fighter for fighter in battle.combatants if fighter.side == Side.ALLIES
        }
        if set(allies) != {member.id for member in party.members}:
            raise BattleRuleError("Les alliés ne correspondent pas à l'équipe.")
        for member in party.members:
            fighter = allies[member.id]
            if (
                fighter.base_stats,
                fighter.permanent_modifiers,
                fighter.hp,
                fighter.mp,
                fighter.skills,
            ) != (
                member.base_stats,
                member.equipment_modifiers,
                member.hp,
                member.mp,
                member.skills,
            ):
                raise BattleRuleError("Instantané de personnage incohérent.")
        if battle.initial_items != inventory.stacks:
            raise BattleRuleError("Le combat doit recevoir un instantané complet du sac.")
        self._battle = battle
        self._party = party
        self._members = party.members
        self._snapshots = tuple(CharacterSnapshot.capture(member) for member in self._members)
        self._inventory = inventory
        self._wallet = wallet
        self._initial_gold = wallet.gold
        self._rewards = rewards if rewards is not None else RewardTable()
        self._result: SettlementResult | None = None

    def settle(self, random: RandomSource) -> SettlementResult:
        if self._result is not None:
            return self._result
        battle = self._battle
        if battle.state != BattleState.FINISHED or battle.outcome is None or battle.settled:
            raise BattleRuleError("Combat non terminé ou déjà soldé par une autre session.")
        if (
            self._party.members != self._members
            or self._inventory.stacks != battle.initial_items
            or self._wallet.gold != self._initial_gold
            or tuple(CharacterSnapshot.capture(member) for member in self._members)
            != self._snapshots
        ):
            raise BattleRuleError("L'état du groupe a changé pendant le combat.")
        rewards = (
            self._rewards.roll(random) if battle.outcome == Outcome.VICTORY else RewardBundle()
        )
        # Le même échange est validé sur une copie, puis exécuté sans point d'échec métier restant.
        final_items = (*battle.items, *rewards.items)
        candidate = Inventory(self._inventory.stacks)
        candidate.exchange(candidate.stacks, final_items)
        fighters = {fighter.id: fighter for fighter in battle.combatants}
        self._inventory.exchange(self._inventory.stacks, candidate.stacks)
        levels: list[tuple[str, int]] = []
        for member in self._members:
            fighter = fighters[member.id]
            # Les maxima temporaires et les altérations ne survivent pas au combat.
            member.set_resources(min(member.stats.hp, fighter.hp), min(member.stats.mp, fighter.mp))
            if rewards.experience:
                levels.append((member.id, member.gain_experience(rewards.experience)))
        self._wallet.credit(rewards.gold)
        battle.mark_settled()
        self._result = SettlementResult(battle.id, battle.outcome, rewards, tuple(levels))
        return self._result
