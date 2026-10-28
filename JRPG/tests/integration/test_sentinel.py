"""Dernier défi : annonce, contre-jeu, récompenses et reprise après défaite."""

from dataclasses import replace

import pygame
import pytest

from JRPG.application.exploration import ExplorationSession
from JRPG.application.saves import SaveError
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import (
    Action,
    ActiveStatus,
    BattleCommand,
    BattleState,
    Outcome,
    Side,
    StatusDefinition,
    StatusKind,
)
from JRPG.domain.dialogues import StoryEffect, StoryOperation
from JRPG.domain.quests import QuestStatus
from JRPG.domain.world import MapPosition, WorldEvent, WorldEventKind
from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
from JRPG.infrastructure.world_content import create_exploration_session
from JRPG.presentation.battle_controller import BattleController, Playback
from JRPG.presentation.battle_scene import BattleScene
from tests.world_helpers import finish_battle


def prepared_session(seed: int = 7, *, accept: bool = True) -> ExplorationSession:
    session = create_exploration_session(
        seed=seed, position=MapPosition("ruins", 15.5 * 32, 3.5 * 32)
    )
    story = session.story
    assert story is not None
    for quest, facts in (
        (
            "road",
            (
                (WorldEventKind.MAP_ENTERED, "forest"),
                (WorldEventKind.ENCOUNTER_CLEARED, "forest_wolves"),
            ),
        ),
        (
            "sanctuary",
            (
                (WorldEventKind.FLAG_SET, "inscription_lue"),
                (WorldEventKind.ENCOUNTER_CLEARED, "ruins_guardians"),
            ),
        ),
    ):
        story.apply((StoryEffect(StoryOperation.ACCEPT_QUEST, quest),))
        for kind, identity in facts:
            session.world.state.record(kind, identity)
            story.observe(WorldEvent(kind, identity))
        story.apply((StoryEffect(StoryOperation.CLAIM_QUEST, quest),))
    if accept:
        story.apply((StoryEffect(StoryOperation.ACCEPT_QUEST, "sentinel"),))
    for hero in session.party.members:
        hero.gain_experience(120)
        hero.set_resources(hero.stats.hp, hero.stats.mp)
    return session


@pytest.mark.parametrize("seed", range(12))
def test_prepared_group_can_win_using_guard_and_existing_skills(seed: int) -> None:
    session = prepared_session(seed)
    session.interact()
    finish_battle(session, guard=True)
    result = session.finish_encounter()
    assert result.outcome == Outcome.VICTORY
    assert "ruins_sentinel" in session.world.state.cleared_encounters
    assert session.story is not None
    assert session.story.quests.status("sentinel") == QuestStatus.COMPLETED
    assert "adventure_complete" not in session.world.state.flags
    assert all(hero.hp > 0 for hero in session.party.members)
    assert result.rewards.gold == 120
    assert session.world.nearby() is None


def test_sealed_sentinel_requires_accepted_quest_without_consuming_rng() -> None:
    session = prepared_session(accept=False)
    mapper = GameSnapshotMapper()
    before = mapper.capture(session)
    result = session.interact()
    assert result is not None and result.encounter is None
    assert "scellée" in result.message
    assert session.active_encounter is None
    assert mapper.capture(session) == before


def test_defeat_preserves_challenge_and_retry_is_fresh() -> None:
    session = prepared_session()
    origin = session.world.origin
    session.interact()
    encounter = session.active_encounter
    assert encounter is not None
    finish_battle(session, lose=True)
    assert session.finish_encounter().outcome == Outcome.DEFEAT
    assert session.world.position == origin
    assert "ruins_sentinel" not in session.world.state.cleared_encounters
    assert all(
        hero.hp == hero.stats.hp and hero.mp == hero.stats.mp for hero in session.party.members
    )
    session.interact()
    retry = session.active_encounter
    assert retry is not None and retry is not encounter
    boss = next(f for f in retry.battle.combatants if f.side == Side.ENEMIES)
    assert boss.hp == boss.stats.hp and not boss.statuses


def test_charge_and_sweep_are_legal_alternating_actions_and_flee_is_disabled() -> None:
    session = prepared_session()
    session.interact()
    encounter = session.active_encounter
    assert encounter is not None
    battle = encounter.battle
    battle.start()
    boss_actions = []
    for _ in range(30):
        actor = battle.prepare_turn()
        if actor.side == Side.ALLIES:
            flee = BattleCommand(actor.id, battle.turn_id, Action.FLEE)
            assert battle.command_error(flee) == "Fuite interdite."
            command = next(c for c in battle.legal_commands() if c.action == Action.DEFEND)
        else:
            command = encounter.ai.choose(battle, encounter.random)
            boss_actions.append(command.ability_id)
            assert command in battle.legal_commands()
            if len(boss_actions) == 1:
                illegal = replace(
                    command,
                    ability_id="sentinel_cleave",
                    targets=tuple(f.id for f in battle.combatants if f.side == Side.ALLIES),
                )
                assert "préparation" in (battle.command_error(illegal) or "")
                before = battle.combatants, battle.journal
                with pytest.raises(ValueError):
                    battle.execute(illegal, encounter.random)
                assert (battle.combatants, battle.journal) == before
        battle.execute(command, encounter.random)
        if len(boss_actions) == 4:
            break
    assert boss_actions == ["sentinel_charge", "sentinel_cleave"] * 2


def test_guard_reduces_the_sweep_damage_by_half() -> None:
    damages = []
    for defend in (False, True):
        session = prepared_session()
        session.interact()
        encounter = session.active_encounter
        assert encounter is not None
        battle = encounter.battle
        battle.start()
        for _ in range(12):
            actor = battle.prepare_turn()
            if actor.side == Side.ALLIES:
                action = Action.DEFEND if defend else Action.PASS
                command = next(c for c in battle.legal_commands() if c.action == action)
            else:
                command = encounter.ai.choose(battle, encounter.random)
            result = battle.execute(command, encounter.random)
            if command.ability_id == "sentinel_cleave":
                damages.append(
                    {f.id: f.stats.hp - f.hp for f in result.combatants if f.side == Side.ALLIES}
                )
                break
        assert battle.state == BattleState.TURN_READY
    assert damages[0]
    assert damages[1] == {identity: damage // 2 for identity, damage in damages[0].items()}


def test_charging_is_visible_during_the_response_round() -> None:
    pygame.font.init()
    session = prepared_session()
    session.interact()
    encounter = session.active_encounter
    assert encounter is not None
    controller = BattleController(encounter)
    scene = BattleScene(lambda: controller)
    for _ in range(20):
        if controller.accepting_input:
            controller.select(5)
        scene.update(Playback.DURATION)
        if controller.threat_hint:
            break
    assert "défendez-vous" in controller.threat_hint
    assert any(f.has_status(StatusKind.CHARGING) for f in controller.displayed)
    scene.draw_foreground(pygame.Surface((640, 360), pygame.SRCALPHA))
    assert any("Préparation du grand balayage" in line for line in controller.log)


@pytest.mark.parametrize("version", [1, 2])
def test_previous_content_is_rejected_with_new_game_guidance(version: int) -> None:
    mapper = GameSnapshotMapper()
    snapshot = mapper.capture(create_exploration_session())
    assert snapshot.content_version == 3
    with pytest.raises(SaveError, match="nouvelle partie"):
        mapper.restore(replace(snapshot, content_version=version))


def test_victory_can_be_loaded_before_claim_and_final_reward_is_unique() -> None:
    session = prepared_session()
    session.interact()
    finish_battle(session, guard=True)
    session.finish_encounter()
    mapper = GameSnapshotMapper()
    restored = mapper.restore(mapper.capture(session))
    assert restored.story is not None
    assert restored.story.quests.status("sentinel") == QuestStatus.COMPLETED
    assert all(obj.id != "ruins_sentinel" for obj in restored.world.visible_objects())
    claim = StoryEffect(StoryOperation.CLAIM_QUEST, "sentinel")
    restored.story.apply((claim, StoryEffect(StoryOperation.SET_FLAG, "adventure_complete")))
    assert restored.inventory.quantity("sylve_sigil") == 1
    before = mapper.capture(restored)
    with pytest.raises(ValueError):
        restored.story.apply((claim,))
    assert mapper.capture(restored) == before


def test_lost_turn_expires_charge_and_requires_new_preparation() -> None:
    session = prepared_session()
    session.interact()
    encounter = session.active_encounter
    assert encounter is not None
    fighters = encounter.battle.combatants
    boss = next(f for f in fighters if f.side == Side.ENEMIES)
    charged = replace(
        boss,
        base_stats=replace(boss.base_stats, speed=100),
        statuses=(
            ActiveStatus(StatusDefinition("sentinel_charge", StatusKind.CHARGING, 2), 1),
            ActiveStatus(StatusDefinition("sleep", StatusKind.SLEEP, 1), 1),
        ),
    )
    battle = Battle(
        "interrupted",
        tuple(charged if f.id == boss.id else f for f in fighters),
        encounter.abilities,
    )
    battle.start()
    assert battle.prepare_turn().id == boss.id
    command = encounter.ai.choose(battle, encounter.random)
    assert command.action == Action.PASS
    battle.execute(command, encounter.random)
    for _ in range(5):
        actor = battle.prepare_turn()
        if actor.id == boss.id:
            assert not actor.has_status(StatusKind.CHARGING)
            assert encounter.ai.choose(battle, encounter.random).ability_id == "sentinel_charge"
            break
        battle.execute(
            next(c for c in battle.legal_commands() if c.action == Action.PASS), encounter.random
        )
    else:
        pytest.fail("La Sentinelle n'a pas retrouvé son tour.")
