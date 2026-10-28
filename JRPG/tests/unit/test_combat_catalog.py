"""Catalogue strict et nouveaux effets réutilisables, sans Pygame."""

import json
from dataclasses import replace
from importlib.resources import files

import pytest

from JRPG.domain.combat.effects import CureStatuses, RestoreMana
from JRPG.domain.combat.model import (
    ActiveStatus,
    Combatant,
    EventKind,
    Side,
    StatusDefinition,
    StatusKind,
)
from JRPG.domain.stats import CharacterStats, StatModifiers
from JRPG.infrastructure.combat_content import decode_combat, load_combat_catalog
from JRPG.infrastructure.validation import ContentError


class NoRandom:
    def randint(self, minimum: int, maximum: int) -> int:
        raise AssertionError("Un soin ne doit pas consommer le RNG.")


@pytest.mark.parametrize(
    "path,value",
    [
        (("version",), 99),
        (("heroes", 0, "stats", "hp"), True),
        (("heroes", 0, "skills"), ["ghost"]),
        (("statuses", 0, "duration"), 0),
        (("abilities", 0, "cost"), True),
        (("abilities", 0, "effects", 0, "kind"), "eval"),
        (("abilities", 5, "effects", 1, "status"), "ghost"),
        (("abilities", 0, "required_status"), "ghost"),
        (("enemies", 0, "profile"), "ghost"),
        (("enemies", 0, "skills"), ["ghost"]),
        (("consumables", 0, "ability", "cost"), 1),
        (("heroes",), []),
        (("profiles", 0, "guaranteed", 0, "id"), "ghost"),
        (("statuses", 1, "id"), "venom"),
        (("abilities", 1, "id"), "strike"),
    ],
)
def test_invalid_catalog_is_rejected(path: tuple[str | int, ...], value: object) -> None:
    source = (
        files("JRPG.infrastructure.content").joinpath("combat.json").read_text(encoding="utf-8")
    )
    data = json.loads(source)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ContentError):
        decode_combat(json.dumps(data))


def test_twelve_hero_skills_are_real_and_boss_skills_do_not_inflate_count() -> None:
    catalog = load_combat_catalog()
    skills = {skill for hero in catalog.heroes for skill in hero.skills}
    assert len(skills) == 12
    assert all(len(hero.skills) == 3 for hero in catalog.heroes)
    assert not {"sentinel_charge", "sentinel_cleave"} & skills
    assert skills <= {ability.id for ability in catalog.abilities}
    assert len(catalog.enemies) == 6 and len(catalog.consumables) == 5


def target() -> Combatant:
    return Combatant(
        "hero", "Héros", Side.ALLIES, CharacterStats(100, 20, 10, 10, 10, 10, 10), 30, 3
    )


def test_restore_mana_clamps_and_does_not_revive_or_consume_rng() -> None:
    hero = target()
    updated, events = RestoreMana(25).apply(hero, hero, NoRandom())
    assert updated.mp == 20 and updated.hp == 30
    assert events[0].kind == EventKind.MANA_RESTORED and events[0].amount == 17
    fallen = replace(hero, hp=0)
    assert RestoreMana(25).apply(hero, fallen, NoRandom()) == (fallen, ())


def test_cure_preserves_beneficial_effects_and_antidote_only_removes_poison() -> None:
    hero = replace(
        target(),
        statuses=(
            ActiveStatus(StatusDefinition("venom", StatusKind.POISON, 3, 7), 2),
            ActiveStatus(StatusDefinition("silence", StatusKind.SILENCE, 2), 2),
            ActiveStatus(
                StatusDefinition(
                    "buff", StatusKind.MODIFIER, 3, modifiers=StatModifiers(defense=5)
                ),
                3,
            ),
        ),
    )
    cured, events = CureStatuses(frozenset({StatusKind.POISON})).apply(hero, hero, NoRandom())
    assert [status.definition.id for status in cured.statuses] == ["silence", "buff"]
    assert cured.stats.defense == 15 and cured.hp == hero.hp
    assert len(events) == 1 and events[0].status_id == "venom"
    with pytest.raises(ValueError):
        CureStatuses(frozenset())
