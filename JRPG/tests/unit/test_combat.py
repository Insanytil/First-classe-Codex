"""Contrats de phase 2 : commandes, effets, états, IA et résolution transactionnelle."""

from dataclasses import replace

import pytest

from JRPG.domain.combat.ai import BasicAI
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.effects import ApplyStatus, Damage, Heal, Revive
from JRPG.domain.combat.model import (
    Ability,
    Action,
    ActiveStatus,
    BattleCommand,
    BattleRuleError,
    BattleState,
    Combatant,
    Consumable,
    Element,
    EnemyDefinition,
    EventKind,
    InvalidTarget,
    Outcome,
    Resistance,
    Side,
    StatusDefinition,
    StatusKind,
    TargetLife,
    TargetRule,
    TargetSide,
)
from JRPG.domain.errors import DomainError, InsufficientMana, MissingItem
from JRPG.domain.items import ItemCategory, ItemDefinition, ItemQuantity
from JRPG.domain.stats import CharacterStats, StatModifiers

STATS = CharacterStats(100, 30, 20, 5, 16, 5, 20)
POTION = ItemDefinition("potion", "Potion", ItemCategory.CONSUMABLE)
CURE = Ability("cure", "Soins", 5, TargetRule(TargetSide.ALLY), (Heal(40),), True)
FIRE = Ability("fire", "Feu", 8, TargetRule(), (Damage(10, True, Element.FIRE),), True)


class FixedRandom:
    def __init__(self, *values: int) -> None:
        self.values = list(values)
        self.calls = 0

    def randint(self, minimum: int, maximum: int) -> int:
        self.calls += 1
        value = self.values.pop(0) if self.values else minimum
        assert minimum <= value <= maximum
        return value


def fighter(identity: str = "a", side: Side = Side.ALLIES) -> Combatant:
    return Combatant(identity, identity, side, STATS, STATS.hp, STATS.mp)


def ready(
    allies: tuple[Combatant, ...] = (),
    enemies: tuple[Combatant, ...] = (),
    abilities: tuple[Ability, ...] = (),
    consumables: tuple[Consumable, ...] = (),
    items: tuple[ItemQuantity, ...] = (),
) -> Battle:
    battle = Battle(
        "test",
        (*(allies or (fighter(),)), *(enemies or (fighter("z", Side.ENEMIES),))),
        abilities,
        consumables,
        items,
    )
    battle.start()
    battle.prepare_turn()
    return battle


def command(
    battle: Battle,
    action: Action,
    targets: tuple[str, ...] = (),
    ability_id: str = "",
    item_id: str = "",
) -> BattleCommand:
    assert battle.current is not None
    return BattleCommand(battle.current.id, battle.turn_id, action, targets, ability_id, item_id)


def snapshot(battle: Battle) -> tuple[object, ...]:
    return (
        battle.state,
        battle.turn_id,
        battle.combatants,
        battle.items,
        battle.journal,
        battle.outcome,
    )


def test_state_transitions_speed_ties_and_replay_protection() -> None:
    battle = Battle("b", (fighter("b"), fighter("a", Side.ENEMIES)))
    with pytest.raises(BattleRuleError):
        battle.prepare_turn()
    battle.start()
    with pytest.raises(BattleRuleError):
        battle.start()
    assert battle.prepare_turn().id == "a"
    attack = command(battle, Action.ATTACK, ("b",))
    result = battle.execute(attack, FixedRandom())
    assert result.transitions == (
        BattleState.RESOLVING,
        BattleState.TURN_END,
        BattleState.TURN_READY,
    )
    with pytest.raises(BattleRuleError):
        battle.execute(attack, FixedRandom())
    assert battle.prepare_turn().id == "b"
    battle.execute(command(battle, Action.PASS), FixedRandom())
    assert battle.prepare_turn().id == "a"
    before = snapshot(battle)
    with pytest.raises(BattleRuleError):
        battle.execute(attack, FixedRandom())
    assert snapshot(battle) == before


@pytest.mark.parametrize("targets", [(), ("a",), ("missing",), ("z", "z"), ("z", "a")])
def test_invalid_attack_targets_leave_everything_unchanged(targets: tuple[str, ...]) -> None:
    battle = ready()
    before = snapshot(battle)
    random = FixedRandom()
    with pytest.raises(InvalidTarget):
        battle.execute(command(battle, Action.ATTACK, targets), random)
    assert snapshot(battle) == before and random.calls == 0


def test_wrong_actor_and_extraneous_command_fields_are_rejected() -> None:
    battle = ready()
    attack = command(battle, Action.ATTACK, ("z",))
    invalid = (
        replace(attack, actor_id="z"),
        replace(attack, turn_id=99),
        replace(attack, ability_id="fire"),
        replace(attack, item_id="potion"),
        command(battle, Action.PASS, ("a",)),
    )
    before = snapshot(battle)
    for rejected in invalid:
        with pytest.raises(BattleRuleError):
            battle.execute(rejected, FixedRandom())
        assert snapshot(battle) == before


@pytest.mark.parametrize(
    ("effect", "target", "rolls", "expected", "kind", "critical"),
    [
        (Damage(), fighter("z"), (1, 100), 35, EventKind.DAMAGE, False),
        (Damage(), fighter("z"), (100,), 0, EventKind.MISS, False),
        (Damage(), replace(fighter("z"), defending=True), (1, 1), 35, EventKind.DAMAGE, True),
        (
            Damage(10, True, Element.FIRE),
            replace(fighter("z"), resistances=(Resistance(Element.FIRE, 0),)),
            (1, 100),
            0,
            EventKind.DAMAGE,
            False,
        ),
        (
            Damage(10, True, Element.FIRE),
            replace(fighter("z"), resistances=(Resistance(Element.FIRE, 50),)),
            (1, 100),
            18,
            EventKind.DAMAGE,
            False,
        ),
        (
            Damage(10, True, Element.FIRE),
            replace(fighter("z"), resistances=(Resistance(Element.FIRE, 150),)),
            (1, 100),
            55,
            EventKind.DAMAGE,
            False,
        ),
    ],
)
def test_damage_hit_critical_defend_and_elements(
    effect: Damage,
    target: Combatant,
    rolls: tuple[int, ...],
    expected: int,
    kind: EventKind,
    critical: bool,
) -> None:
    actor = replace(fighter(), base_stats=replace(STATS, accuracy=90, critical=20))
    after, events = effect.apply(actor, target, FixedRandom(*rolls))
    assert target.hp - after.hp == expected
    assert (events[0].kind, events[0].critical) == (kind, critical)


def test_defend_expires_at_next_own_turn_and_halves_damage() -> None:
    battle = ready()
    battle.execute(command(battle, Action.DEFEND), FixedRandom())
    battle.prepare_turn()
    battle.execute(command(battle, Action.ATTACK, ("a",)), FixedRandom())
    actor = battle.prepare_turn()
    assert (actor.hp, actor.defending) == (83, False)


def test_skill_cost_learning_and_mana_validation() -> None:
    actor = replace(fighter(), skills=(FIRE.id,), mp=7)
    battle = ready((actor,), abilities=(FIRE,))
    before = snapshot(battle)
    with pytest.raises(InsufficientMana):
        battle.execute(command(battle, Action.SKILL, ("z",), FIRE.id), FixedRandom())
    with pytest.raises(BattleRuleError):
        battle.execute(command(battle, Action.SKILL, ("z",), "unknown"), FixedRandom())
    assert snapshot(battle) == before
    battle = ready((replace(actor, mp=8),), abilities=(FIRE,))
    result = battle.execute(command(battle, Action.SKILL, ("z",), FIRE.id), FixedRandom())
    assert result.combatants[0].mp == 0
    assert result.events[0].kind == EventKind.MANA_SPENT


@pytest.mark.parametrize("kind", [StatusKind.SLEEP, StatusKind.PARALYSIS])
def test_control_status_forces_pass_then_expires(kind: StatusKind) -> None:
    status = StatusDefinition("control", kind, 1)
    actor = replace(fighter(), statuses=(ActiveStatus(status, 1),))
    battle = ready((actor,))
    assert {entry.action for entry in battle.legal_commands()} == {Action.PASS}
    with pytest.raises(BattleRuleError):
        battle.execute(command(battle, Action.ATTACK, ("z",)), FixedRandom())
    result = battle.execute(command(battle, Action.PASS), FixedRandom())
    assert result.combatants[0].statuses == ()


def test_silence_rejects_magic_but_allows_physical_skill() -> None:
    physical = replace(FIRE, id="strike", magical=False)
    silence = StatusDefinition("silence", StatusKind.SILENCE, 2)
    actor = replace(fighter(), skills=(FIRE.id, physical.id), statuses=(ActiveStatus(silence, 2),))
    battle = ready((actor,), abilities=(FIRE, physical))
    with pytest.raises(BattleRuleError):
        battle.execute(command(battle, Action.SKILL, ("z",), FIRE.id), FixedRandom())
    battle.execute(command(battle, Action.SKILL, ("z",), physical.id), FixedRandom())


@pytest.mark.parametrize("kind", [StatusKind.POISON, StatusKind.BURN])
def test_damage_over_time_can_finish_battle(kind: StatusKind) -> None:
    status = StatusDefinition("dot", kind, 2, 999)
    enemy = replace(fighter("0", Side.ENEMIES), statuses=(ActiveStatus(status, 2),))
    battle = ready(enemies=(enemy,))
    result = battle.execute(command(battle, Action.PASS), FixedRandom())
    assert battle.outcome == Outcome.VICTORY
    assert any(event.kind == EventKind.ENEMY_DEFEATED for event in result.events)
    assert result.combatants[1].statuses == ()


def test_status_refresh_buffs_debuffs_and_resource_clamp() -> None:
    status = StatusDefinition(
        "buff", StatusKind.MODIFIER, 2, modifiers=StatModifiers(hp=50, strength=5)
    )
    effect = ApplyStatus(status)
    original = fighter()
    buffed, _ = effect.apply(original, original, FixedRandom())
    assert (buffed.stats.hp, buffed.hp, buffed.stats.strength) == (150, 100, 25)
    buffed = replace(buffed, hp=150, statuses=(ActiveStatus(status, 1),))
    refreshed, _ = effect.apply(original, buffed, FixedRandom())
    assert len(refreshed.statuses) == 1 and refreshed.statuses[0].remaining == 2
    battle = ready((replace(refreshed, statuses=(ActiveStatus(status, 1),)),))
    result = battle.execute(command(battle, Action.PASS), FixedRandom())
    assert (result.combatants[0].hp, result.combatants[0].stats.hp) == (100, 100)
    debuff = replace(status, id="debuff", modifiers=StatModifiers(strength=-999))
    reduced, _ = ApplyStatus(debuff).apply(original, original, FixedRandom())
    assert reduced.stats.strength == 0
    unchanged, events = ApplyStatus(status, 0).apply(original, original, FixedRandom(1))
    assert unchanged == original and not events


def test_heal_revive_and_ko_turn_exclusion() -> None:
    revive = Ability(
        "revive", "Vie", 10, TargetRule(TargetSide.ALLY, TargetLife.KO), (Revive(25),), True
    )
    actor = replace(fighter(), skills=(CURE.id, revive.id), hp=20)
    dead = replace(fighter("b"), hp=0)
    battle = ready((actor, dead), abilities=(CURE, revive))
    with pytest.raises(InvalidTarget):
        battle.execute(command(battle, Action.SKILL, ("b",), CURE.id), FixedRandom())
    result = battle.execute(command(battle, Action.SKILL, ("b",), revive.id), FixedRandom())
    assert result.combatants[1].hp == 25
    assert result.events[-1].kind == EventKind.REVIVED
    battle = ready((actor, dead), abilities=(CURE, revive))
    battle.execute(command(battle, Action.SKILL, ("a",), CURE.id), FixedRandom())
    assert battle.combatants[0].hp == 60
    assert battle.prepare_turn().id == "z"


def test_multiple_targets_require_complete_valid_set() -> None:
    storm = replace(FIRE, id="storm", targeting=TargetRule(multiple=True))
    battle = ready(
        (replace(fighter(), skills=(storm.id,)),),
        (fighter("z", Side.ENEMIES), fighter("y", Side.ENEMIES)),
        (storm,),
    )
    with pytest.raises(InvalidTarget):
        battle.execute(command(battle, Action.SKILL, ("z",), storm.id), FixedRandom())
    result = battle.execute(command(battle, Action.SKILL, ("z", "y"), storm.id), FixedRandom())
    assert [entry.hp for entry in result.combatants[1:]] == [63, 63]
    assert result.combatants[0].mp == 22


def test_consumable_validation_and_single_consumption() -> None:
    potion = Consumable(POTION, replace(CURE, cost=0))
    actor = replace(fighter(), hp=20)
    battle = ready((actor,), consumables=(potion,), items=(ItemQuantity(POTION, 1),))
    before = snapshot(battle)
    with pytest.raises(InvalidTarget):
        battle.execute(command(battle, Action.ITEM, ("z",), item_id=POTION.id), FixedRandom())
    assert snapshot(battle) == before
    battle.execute(command(battle, Action.ITEM, ("a",), item_id=POTION.id), FixedRandom())
    assert battle.items == () and battle.combatants[0].hp == 60
    battle.prepare_turn()
    with pytest.raises(BattleRuleError):
        battle.execute(command(battle, Action.ITEM, ("z",), item_id=POTION.id), FixedRandom())
    battle.execute(command(battle, Action.PASS), FixedRandom())
    battle.prepare_turn()
    with pytest.raises(MissingItem):
        battle.execute(command(battle, Action.ITEM, ("a",), item_id=POTION.id), FixedRandom())


def test_rng_failure_during_resolution_does_not_publish_partial_costs_or_damage() -> None:
    class BrokenRandom:
        calls = 0

        def randint(self, minimum: int, maximum: int) -> int:
            self.calls += 1
            if self.calls > 2:
                raise RuntimeError("rng failure")
            return minimum

    double = replace(FIRE, id="double", effects=(Damage(), Damage()))
    battle = ready((replace(fighter(), skills=(double.id,)),), abilities=(double,))
    before = snapshot(battle)
    with pytest.raises(RuntimeError, match="rng failure"):
        battle.execute(command(battle, Action.SKILL, ("z",), double.id), BrokenRandom())
    assert snapshot(battle) == before


def test_flee_success_failure_and_boss_restriction() -> None:
    battle = ready()
    assert battle.execute(command(battle, Action.FLEE), FixedRandom(1)).outcome == Outcome.FLED
    with pytest.raises(BattleRuleError):
        battle.prepare_turn()
    battle = ready()
    result = battle.execute(command(battle, Action.FLEE), FixedRandom(100))
    assert result.outcome is None and result.events[0].kind == EventKind.FLEE_FAILED
    boss = Battle("boss", (fighter(), fighter("z", Side.ENEMIES)), allow_flee=False)
    boss.start()
    boss.prepare_turn()
    with pytest.raises(BattleRuleError):
        boss.execute(command(boss, Action.FLEE), FixedRandom())


def test_basic_ai_uses_the_same_legal_commands_and_can_lose() -> None:
    enemy = replace(fighter("0", Side.ENEMIES), base_stats=replace(STATS, strength=999))
    battle = ready(enemies=(enemy,))
    choice = BasicAI().choose(battle, FixedRandom())
    assert choice in battle.legal_commands()
    result = battle.execute(choice, FixedRandom())
    assert result.outcome == Outcome.DEFEAT
    assert any(event.kind == EventKind.KNOCKED_OUT for event in result.events)


def test_enemy_definition_separates_instances_and_rejects_duplicate_battle_ids() -> None:
    wolf = EnemyDefinition("wolf", "Loup", STATS)
    first, second = wolf.spawn("wolf-1"), wolf.spawn("wolf-2")
    assert first.id != second.id and first.hp == second.hp
    with pytest.raises(BattleRuleError):
        Battle("bad", (fighter(), first, first))
    with pytest.raises(BattleRuleError):
        Battle("bad", (fighter(),))
    with pytest.raises(BattleRuleError):
        Battle("bad", (replace(fighter(), skills=("missing",)), first))


def test_invalid_content_is_rejected() -> None:
    with pytest.raises(DomainError):
        Damage(-1)
    with pytest.raises(DomainError):
        ApplyStatus(StatusDefinition("s", StatusKind.SLEEP, 1), 101)
    with pytest.raises(DomainError):
        Consumable(POTION, CURE)
    with pytest.raises(DomainError):
        replace(fighter(), hp=101)
    with pytest.raises(DomainError):
        StatusDefinition("s", StatusKind.SLEEP, 0)


def test_lethal_composite_does_not_heal_or_apply_states_to_a_corpse() -> None:
    status = StatusDefinition("burn", StatusKind.BURN, 2, 5)
    combo = replace(FIRE, id="combo", effects=(Damage(999), ApplyStatus(status), Heal(10)))
    battle = ready((replace(fighter(), skills=(combo.id,)),), abilities=(combo,))
    result = battle.execute(command(battle, Action.SKILL, ("z",), combo.id), FixedRandom())
    assert result.outcome == Outcome.VICTORY
    assert result.combatants[1].hp == 0 and result.combatants[1].statuses == ()
    assert sum(event.kind == EventKind.ENEMY_DEFEATED for event in result.events) == 1
    assert not any(
        event.kind in {EventKind.HEAL, EventKind.STATUS_APPLIED} for event in result.events
    )


def test_revive_has_no_effect_on_living_target_and_clears_guard_when_reviving() -> None:
    actor = fighter()
    after, events = Revive(20).apply(actor, actor, FixedRandom())
    assert after == actor and not events
    corpse = replace(actor, hp=0, defending=True)
    revived, _ = Revive(20).apply(actor, corpse, FixedRandom())
    assert revived.hp == 20 and not revived.defending
    after, events = Damage().apply(actor, corpse, FixedRandom())
    assert after == corpse and not events


def test_conflicting_status_definitions_are_rejected_at_battle_creation() -> None:
    status = StatusDefinition("burn", StatusKind.BURN, 2, 5)
    first = replace(FIRE, effects=(ApplyStatus(status),))
    second = replace(FIRE, id="other", effects=(ApplyStatus(replace(status, potency=10)),))
    with pytest.raises(BattleRuleError):
        ready(abilities=(first, second))
    affected, _ = ApplyStatus(status).apply(fighter(), fighter(), FixedRandom())
    with pytest.raises(DomainError):
        ApplyStatus(replace(status, potency=10)).apply(fighter(), affected, FixedRandom())


def test_composed_effects_read_the_updated_caster_state() -> None:
    buff = StatusDefinition("might", StatusKind.MODIFIER, 2, modifiers=StatModifiers(strength=10))
    # Ciblage personnel volontaire : l'auto-dégât utilise la force augmentée.
    combo = Ability(
        "risky", "Rituel", 0, TargetRule(TargetSide.SELF), (ApplyStatus(buff), Damage())
    )
    actor = replace(fighter(), skills=(combo.id,))
    battle = ready((actor,), abilities=(combo,))
    result = battle.execute(command(battle, Action.SKILL, ("a",), combo.id), FixedRandom())
    assert result.combatants[0].hp == 45


def test_equipment_and_temporary_modifiers_are_combined_before_clamping() -> None:
    actor = replace(fighter(), permanent_modifiers=StatModifiers(strength=-50))
    assert actor.stats.strength == 0
    status = StatusDefinition(
        "blessing", StatusKind.MODIFIER, 2, modifiers=StatModifiers(strength=45)
    )
    after, _ = ApplyStatus(status).apply(actor, actor, FixedRandom())
    assert after.stats.strength == 15
