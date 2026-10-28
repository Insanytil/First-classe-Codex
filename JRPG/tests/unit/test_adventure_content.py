"""Références et opérations déclaratives inconnues rejetées au chargement."""

from importlib.resources import files

import pytest

from JRPG.infrastructure.adventure_content import decode_adventure
from JRPG.infrastructure.training_encounter import create_combat_setup
from JRPG.infrastructure.validation import ContentError


@pytest.mark.parametrize(
    "old,new",
    [
        ('"accept_quest"', '"execute_python"'),
        ('"quest": "road"', '"quest": "ghost"'),
        ('"item": "potion"', '"item": "ghost"'),
        ('"next": "root"', '"next": "missing"'),
        ('"operation": "rest"', '"operation": "__import__"'),
        ('"quest": "sentinel"', '"quest": "missing_sentinel"'),
    ],
)
def test_invalid_story_references_do_not_compile(old: str, new: str) -> None:
    setup = create_combat_setup()
    source = (
        files("JRPG.infrastructure.content").joinpath("adventure.json").read_text(encoding="utf-8")
    )
    assert old in source
    with pytest.raises(ContentError):
        decode_adventure(
            source.replace(old, new), tuple(entry.item for entry in setup.factory.consumables)
        )
