"""Contenu embarqué, références et accessibilité réelle des interactions."""

import json
from importlib.resources import files

import pytest

from JRPG.domain.combat.model import Outcome
from JRPG.domain.errors import DomainError
from JRPG.domain.items import ItemCategory, ItemDefinition
from JRPG.domain.world import MapPosition, World
from JRPG.infrastructure.training_encounter import create_combat_setup
from JRPG.infrastructure.world_content import (
    ContentError,
    JsonMapLoader,
    create_exploration_session,
)
from tests.world_helpers import finish_battle, walk_to


def loader() -> JsonMapLoader:
    factory = create_combat_setup().factory
    return JsonMapLoader(
        tuple(entry.item for entry in factory.consumables),
        frozenset(factory.enemies),
    )


def test_three_maps_all_interactions_and_return_keep_state() -> None:
    session = create_exploration_session()
    party, bag, wallet = session.party, session.inventory, session.wallet
    for identity in ("mira_village", "village_guard", "village_chest"):
        walk_to(session, identity)
        assert session.interact() is not None
    after_chest = bag.stacks, wallet.gold
    assert session.interact() is not None
    assert (bag.stacks, wallet.gold) == after_chest
    walk_to(session, "village_to_forest")
    session.interact()
    assert session.world.position.map_id == "forest"
    for identity in ("forest_traveler", "forest_chest"):
        walk_to(session, identity)
        session.interact()
    walk_to(session, "forest_to_ruins")
    session.interact()
    assert session.world.position.map_id == "ruins"
    for identity in ("ruins_scholar", "ruins_chest"):
        walk_to(session, identity)
        session.interact()
    walk_to(session, "ruins_to_forest")
    session.interact()
    walk_to(session, "forest_to_village")
    session.interact()
    assert session.world.state.visited_maps == frozenset({"village", "forest", "ruins"})
    assert session.world.state.opened_chests == frozenset(
        {"village_chest", "forest_chest", "ruins_chest"}
    )
    assert session.party is party and session.inventory is bag and session.wallet is wallet
    assert wallet.gold == 75
    walk_to(session, "village_chest")
    before = bag.stacks, wallet.gold
    session.interact()
    assert (bag.stacks, wallet.gold) == before


def test_encounter_victory_returns_resources_and_clears_only_that_encounter() -> None:
    session = create_exploration_session()
    walk_to(session, "village_to_forest")
    session.interact()
    walk_to(session, "forest_wolves")
    session.interact()
    with pytest.raises(DomainError):
        session.move(1, 0, 1)
    with pytest.raises(DomainError):
        session.interact()
    before = session.world.position
    finish_battle(session)
    result = session.finish_encounter()
    assert result.outcome == Outcome.VICTORY and session.world.position == before
    assert session.active_encounter is None
    assert session.wallet.gold == 30
    assert any(member.hp < member.stats.hp for member in session.party.members)
    assert "forest_wolves" in session.world.state.cleared_encounters
    assert not any(entry.id == "forest_wolves" for entry in session.world.visible_objects())
    with pytest.raises(DomainError):
        session.finish_encounter()
    assert session.wallet.gold == 30


@pytest.mark.parametrize("lose", [False, True])
def test_flee_or_defeat_does_not_clear_encounter_and_defeat_recovers_at_village(lose: bool) -> None:
    session = create_exploration_session()
    walk_to(session, "village_to_forest")
    session.interact()
    walk_to(session, "forest_wolves")
    session.interact()
    finish_battle(session, flee=not lose, lose=lose)
    result = session.finish_encounter()
    assert result.outcome == (Outcome.DEFEAT if lose else Outcome.FLED)
    assert not session.world.state.cleared_encounters and session.wallet.gold == 0
    assert session.world.position.map_id == ("village" if lose else "forest")
    if lose:
        assert all(
            member.hp == member.stats.hp and member.mp == member.stats.mp
            for member in session.party.members
        )
    else:
        assert session.interact() is not None
        assert session.active_encounter is not None


def test_bridge_is_walkable_but_river_and_tree_trunks_are_solid() -> None:
    session = create_exploration_session()
    assert session.world.walkable(MapPosition("forest", 19.5 * 32, 11.5 * 32))
    assert not session.world.walkable(MapPosition("forest", 19.5 * 32, 6.5 * 32))
    assert not session.world.walkable(MapPosition("forest", 12.5 * 32, 8.5 * 32))


@pytest.mark.parametrize(
    "broken",
    [
        "{",
        json.dumps({"version": 2}),
        json.dumps({"version": True}),
        json.dumps(
            {
                "version": 1,
                "ground": ["X"],
                "collision": ["0"],
                "objects": [],
                "decorations": [],
                "id": "x",
                "name": "X",
            }
        ),
        json.dumps(
            {
                "version": 1,
                "ground": ["."],
                "collision": ["00"],
                "objects": [],
                "decorations": [],
                "id": "x",
                "name": "X",
            }
        ),
        json.dumps(
            {
                "version": 1,
                "ground": ["."],
                "collision": ["0"],
                "objects": [
                    {
                        "id": "x",
                        "name": "X",
                        "kind": "encounter",
                        "x": 0,
                        "y": 0,
                        "enemies": ["unknown"],
                    }
                ],
                "decorations": [],
                "id": "x",
                "name": "X",
            }
        ),
    ],
)
def test_corrupt_content_is_rejected_with_explicit_errors(broken: str) -> None:
    with pytest.raises(ContentError, match="Carte invalide"):
        loader().decode(broken)


def test_unknown_item_and_inaccessible_portal_destination_fail_validation() -> None:
    source = (
        files("JRPG.infrastructure.content")
        .joinpath("maps", "village.json")
        .read_text(encoding="utf-8")
    )
    with pytest.raises(ContentError):
        loader().decode(source.replace('"potion"', '"unknown_item"'))
    maps = list(loader().load())
    maps[0] = loader().decode(source.replace('"map": "forest"', '"map": "missing"'))
    with pytest.raises(DomainError, match="destination inaccessible"):
        World(tuple(maps), MapPosition("village", 8.5 * 32, 10.5 * 32))


def test_chest_definition_conflict_preserves_inventory_money_and_open_flag() -> None:
    session = create_exploration_session()
    original = next(stack for stack in session.inventory.stacks if stack.item.id == "potion")
    session.inventory.remove(original.item, original.quantity)
    session.inventory.add(
        ItemDefinition("potion", "Définition contradictoire", ItemCategory.CONSUMABLE)
    )
    walk_to(session, "village_chest")
    before = session.inventory.stacks, session.wallet.gold, session.world.state.opened_chests
    with pytest.raises(DomainError):
        session.interact()
    assert (
        session.inventory.stacks,
        session.wallet.gold,
        session.world.state.opened_chests,
    ) == before
