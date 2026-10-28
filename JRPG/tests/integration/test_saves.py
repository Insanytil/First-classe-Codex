"""Sauvegardes réelles en répertoire de test : round-trip, corruption et remplacement sûr."""

import json
from pathlib import Path

import pytest

from JRPG.application.exploration import ExplorationSession
from JRPG.application.progression import Conversation
from JRPG.application.saves import SaveError, SaveService
from JRPG.domain.items import EquipmentSlot
from JRPG.domain.quests import QuestStatus
from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
from JRPG.infrastructure.save_codec import SaveCodec
from JRPG.infrastructure.save_repository import JsonSaveRepository
from JRPG.infrastructure.world_content import create_exploration_session
from tests.world_helpers import finish_battle, walk_to


def speak(session: ExplorationSession, npc: str, choice: str) -> Conversation:
    walk_to(session, npc)
    session.interact()
    assert session.story is not None
    definition = session.story.dialogue_for(npc)
    assert definition is not None
    conversation = Conversation(session.story, definition)
    conversation.choose(choice)
    return conversation


def test_round_trip_preserves_complete_state_and_rng(tmp_path: Path) -> None:
    session = create_exploration_session()
    story = session.story
    assert story is not None
    session.wallet.credit(100)
    story.shops["oren"].buy("steel_sword", 1, session.inventory, session.wallet)
    hero = session.party.members[0]
    hero.equip(session.inventory, story.content.item("steel_sword"), EquipmentSlot.WEAPON)
    hero.lose_hp(17)
    hero.spend_mana(3)
    hero.gain_experience(130)
    session.party.move("nox", 0)
    session.advance_time(123.5)
    speak(session, "mira_village", "accept_road")
    walk_to(session, "village_chest")
    session.interact()
    mapper = GameSnapshotMapper()
    before = mapper.capture(session)
    saves = SaveService(JsonSaveRepository(tmp_path), mapper)
    for slot in range(1, 4):
        saves.save(slot, session)
        restored = saves.load(slot)
        assert mapper.capture(restored) == before
        assert restored is not session and restored.party is not session.party
        first = session.encounter_factory.create(
            "probe", ("wolf",), session.party, session.inventory, session.wallet
        )
        second = restored.encounter_factory.create(
            "probe", ("wolf",), restored.party, restored.inventory, restored.wallet
        )
        assert [first.random.randint(1, 100) for _ in range(5)] == [
            second.random.randint(1, 100) for _ in range(5)
        ]
        session.encounter_factory.restore_checkpoint(before.random)
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "slot-1.json",
        "slot-2.json",
        "slot-3.json",
    ]


def test_full_adventure_save_load_then_finish_does_not_duplicate_rewards(tmp_path: Path) -> None:
    session = create_exploration_session()
    speak(session, "mira_village", "accept_road")
    walk_to(session, "village_chest")
    session.interact()
    walk_to(session, "village_to_forest")
    session.interact()
    speak(session, "forest_traveler", "accept")
    walk_to(session, "forest_chest")
    session.interact()
    speak(session, "forest_traveler", "claim")
    walk_to(session, "forest_wolves")
    session.interact()
    finish_battle(session)
    session.finish_encounter()
    assert session.story is not None
    assert session.story.quests.status("road") == QuestStatus.COMPLETED
    saves = SaveService(JsonSaveRepository(tmp_path), GameSnapshotMapper())
    saves.save(2, session)
    session = saves.load(2)
    walk_to(session, "forest_to_village")
    session.interact()
    conversation = speak(session, "mira_village", "claim_road")
    gold = session.wallet.gold
    with pytest.raises(ValueError):
        conversation.choose("claim_road")
    assert session.wallet.gold == gold
    conversation.choose("accept_sanctuary")
    conversation.choose("rest")
    conversation.choose("leave")
    assert session.story is not None
    shop = session.story.shops["oren"]
    shop.buy("steel_sword", 1, session.inventory, session.wallet)
    hero = next(member for member in session.party.members if member.id == "ari")
    hero.equip(session.inventory, session.story.content.item("steel_sword"), EquipmentSlot.WEAPON)
    walk_to(session, "village_to_forest")
    session.interact()
    walk_to(session, "forest_to_ruins")
    session.interact()
    speak(session, "ruins_scholar", "read")
    walk_to(session, "ruins_chest")
    session.interact()
    walk_to(session, "ruins_guardians")
    session.interact()
    finish_battle(session)
    result = session.finish_encounter()
    assert result.outcome == "victory"
    assert session.story.quests.status("sanctuary") == QuestStatus.COMPLETED
    walk_to(session, "ruins_to_forest")
    session.interact()
    walk_to(session, "forest_to_village")
    session.interact()
    conversation = speak(session, "mira_village", "claim_sanctuary")
    assert "adventure_complete" not in session.world.state.flags
    assert session.story.quests.status("sanctuary") == QuestStatus.REWARDED
    assert session.inventory.quantity("bronze_ring") == 1
    conversation.choose("accept_sentinel")
    conversation.choose("tactics")
    conversation.choose("continue")
    conversation.choose("rest")
    walk_to(session, "village_to_forest")
    session.interact()
    walk_to(session, "forest_to_ruins")
    session.interact()
    walk_to(session, "ruins_sentinel")
    session.interact()
    finish_battle(session, guard=True)
    assert session.finish_encounter().outcome == "victory"
    walk_to(session, "ruins_to_forest")
    session.interact()
    walk_to(session, "forest_to_village")
    session.interact()
    speak(session, "mira_village", "claim_sentinel")
    assert "adventure_complete" in session.world.state.flags
    assert session.inventory.quantity("sylve_sigil") == 1
    saves.save(3, session)
    restored = saves.load(3)
    assert restored.story is not None
    before = (
        restored.wallet.gold,
        restored.inventory.stacks,
        tuple(member.experience for member in restored.party.members),
    )
    with pytest.raises(ValueError):
        speak(restored, "mira_village", "claim_sentinel")
    assert (
        restored.wallet.gold,
        restored.inventory.stacks,
        tuple(member.experience for member in restored.party.members),
    ) == before
    assert dict(restored.story.shops["oren"].stock)["steel_sword"] == 0
    assert restored.world.state.cleared_encounters == frozenset(
        {"forest_wolves", "ruins_guardians", "ruins_sentinel"}
    )


@pytest.mark.parametrize("slot", [0, 4, -1, True])
def test_invalid_slot_is_rejected_before_writing(slot: int, tmp_path: Path) -> None:
    repo = JsonSaveRepository(tmp_path)
    with pytest.raises(SaveError):
        repo.write(slot, GameSnapshotMapper().capture(create_exploration_session()))
    assert not list(tmp_path.iterdir())


def test_atomic_replace_failure_preserves_previous_save_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = JsonSaveRepository(tmp_path)
    mapper = GameSnapshotMapper()
    session = create_exploration_session()
    repository.write(1, mapper.capture(session))
    old = (tmp_path / "slot-1.json").read_bytes()
    session.wallet.credit(100)

    def fail(source: object, destination: object) -> None:
        raise OSError("replacement refused")

    monkeypatch.setattr("JRPG.infrastructure.save_repository.os.replace", fail)
    with pytest.raises(SaveError, match="Écriture"):
        repository.write(1, mapper.capture(session))
    assert (tmp_path / "slot-1.json").read_bytes() == old
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize(
    "damage",
    [
        "version",
        "missing",
        "unknown_item",
        "hp",
        "quantity",
        "random",
        "quest",
        "flags",
        "premature_ending",
        "content_version",
        "hero",
        "class",
        "skill",
        "stock",
        "pile_duplicate",
        "marker",
        "position",
        "equipment",
        "gold",
        "time",
    ],
)
def test_corruption_is_rejected_without_mutating_current_game(damage: str, tmp_path: Path) -> None:
    session = create_exploration_session()
    mapper = GameSnapshotMapper()
    before = mapper.capture(session)
    raw = json.loads(SaveCodec().encode(before))
    if damage == "version":
        raw["version"] = 99
    elif damage == "missing":
        del raw["origin"]
    elif damage == "unknown_item":
        raw["inventory"][0]["id"] = "ghost"
    elif damage == "hp":
        raw["heroes"][0]["hp"] = 99999
    elif damage == "quantity":
        raw["inventory"][0]["quantity"] = 0
    elif damage == "random":
        raw["random"]["values"] = []
    elif damage == "quest":
        raw["quests"][0][1] = "rewarded"
    elif damage == "flags":
        raw["flags"] = ["unknown_flag"]
    elif damage == "premature_ending":
        raw["flags"] = ["adventure_complete"]
    elif damage == "content_version":
        raw["content_version"] = 99
    elif damage == "hero":
        raw["heroes"][0]["id"] = "ghost"
    elif damage == "class":
        raw["heroes"][0]["class_id"] = "ghost"
    elif damage == "skill":
        raw["heroes"][0]["skills"] = ["ghost"]
    elif damage == "stock":
        raw["shops"][0]["stock"] = []
    elif damage == "pile_duplicate":
        raw["inventory"].append(raw["inventory"][0].copy())
    elif damage == "marker":
        raw["opened_chests"] = ["ghost"]
    elif damage == "position":
        raw["position"]["x"] = 0
    elif damage == "equipment":
        raw["heroes"][0]["equipment"][0][0] = "head"
    elif damage == "gold":
        raw["gold"] = True
    else:
        raw["play_seconds"] = -1
    (tmp_path / "slot-1.json").write_text(json.dumps(raw), encoding="utf-8")
    saves = SaveService(JsonSaveRepository(tmp_path), mapper)
    with pytest.raises(SaveError):
        saves.load(1)
    assert mapper.capture(session) == before


def test_missing_file_and_malformed_json_are_explicit_errors(tmp_path: Path) -> None:
    saves = SaveService(JsonSaveRepository(tmp_path), GameSnapshotMapper())
    with pytest.raises(SaveError, match="Lecture"):
        saves.load(1)
    (tmp_path / "slot-1.json").write_text("{", encoding="utf-8")
    with pytest.raises(SaveError, match="invalide"):
        saves.load(1)


def test_mid_battle_save_is_rejected(tmp_path: Path) -> None:
    session = create_exploration_session()
    walk_to(session, "village_to_forest")
    session.interact()
    walk_to(session, "forest_wolves")
    session.interact()
    with pytest.raises(SaveError):
        SaveService(JsonSaveRepository(tmp_path), GameSnapshotMapper()).save(1, session)
    assert not list(tmp_path.iterdir())
