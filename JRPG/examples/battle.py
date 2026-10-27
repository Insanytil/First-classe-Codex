"""Combat complet reproductible, sans fenêtre ni import Pygame."""

from JRPG.application.battle_session import BattleSession
from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition
from JRPG.domain.combat.ai import BasicAI
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.effects import Damage
from JRPG.domain.combat.model import (
    Ability,
    BattleState,
    Combatant,
    Element,
    EnemyDefinition,
    TargetRule,
)
from JRPG.domain.combat.rewards import LootEntry, RewardTable
from JRPG.domain.items import Inventory, ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.party import Party
from JRPG.domain.stats import CharacterStats
from JRPG.domain.wallet import Wallet
from JRPG.infrastructure.random_source import SeededRandom


def main() -> None:
    fire = Ability("fire", "Feu", 8, TargetRule(), (Damage(8, True, Element.FIRE),), True)
    job = ClassDefinition("mage", "Mage", CharacterStats(160, 40, 16, 8, 24, 12, 20))
    hero = Character(CharacterDefinition("hero", "Ari", job))
    hero.learn_skill(fire.id)
    wolf = EnemyDefinition("wolf", "Loup", CharacterStats(55, 0, 12, 5, 0, 5, 12))
    potion = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)
    inventory, wallet = Inventory(), Wallet()
    battle = Battle(
        "demo-1",
        (Combatant.from_character(hero), wolf.spawn("wolf-1"), wolf.spawn("wolf-2")),
        (fire,),
    )
    rewards = RewardTable(
        120, 25, (ItemQuantity(potion, 1),), (LootEntry(1), LootEntry(1, ItemQuantity(potion, 1)))
    )
    session = BattleSession(battle, Party([hero]), inventory, wallet, rewards)
    random, policy = SeededRandom(7), BasicAI()
    battle.start()
    for _ in range(200):
        battle.prepare_turn()
        result = battle.execute(policy.choose(battle, random), random)
        for event in result.events:
            print(f"{event.kind}: {event.actor_id} -> {event.target_id} ({event.amount})")
        if battle.state == BattleState.FINISHED:
            break
    else:
        raise RuntimeError("La démonstration dépasse 200 tours.")
    settlement = session.settle(random)
    print(f"Résultat : {settlement.outcome}, XP {hero.experience}, or {wallet.gold}")
    print(
        f"PV {hero.hp}/{hero.stats.hp}, PM {hero.mp}/{hero.stats.mp}, "
        f"potions {inventory.quantity('potion')}"
    )
    assert session.settle(random) is settlement


if __name__ == "__main__":
    main()
