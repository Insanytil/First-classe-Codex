"""Contrôle statique des imports absolus et relatifs des couches."""

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "src" / "JRPG"
ALLOWED = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "application", "infrastructure"},
    "presentation": {"domain", "application", "presentation"},
}
PURE_FORBIDDEN = {"json", "pathlib", "os", "io", "time", "datetime", "random", "socket"}


def violations(source: str, package: str, layer: str) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = importlib.util.resolve_name("." * node.level + module, package)
            imports.append(module)
            imports.extend(f"{module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            imports.append("dynamic_import")
    errors: list[str] = []
    for module in imports:
        parts = module.split(".")
        root = parts[0]
        if root == "JRPG":
            if len(parts) < 2 or parts[1] not in ALLOWED[layer]:
                errors.append(module)
        elif layer in {"domain", "application"} and (
            root not in sys.stdlib_module_names or root in PURE_FORBIDDEN
        ):
            errors.append(module)
        elif root == "poo":
            errors.append(module)
    return errors


def test_layer_boundaries() -> None:
    errors: list[str] = []
    for layer in ALLOWED:
        for path in (SOURCE / layer).rglob("*.py"):
            relative = path.relative_to(SOURCE.parent).with_suffix("")
            package = ".".join(relative.parts[:-1])
            errors.extend(
                f"{path.relative_to(SOURCE)}: {module}"
                for module in violations(path.read_text(encoding="utf-8"), package, layer)
            )
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize(
    ("source", "package", "layer"),
    [
        ("import pygame", "JRPG.domain", "domain"),
        ("from pygame import Surface", "JRPG.application", "application"),
        ("from ..presentation import pygame_app", "JRPG.domain", "domain"),
        ("from JRPG import bootstrap", "JRPG.application", "application"),
        ("import json", "JRPG.domain", "domain"),
        ("import poo", "JRPG.presentation", "presentation"),
        ('__import__("pygame")', "JRPG.domain", "domain"),
    ],
)
def test_guard_rejects_forbidden_imports(source: str, package: str, layer: str) -> None:
    assert violations(source, package, layer)


def test_inner_layers_import_without_pygame() -> None:
    code = """
import importlib.abc
import sys
class BlockPygame(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] == "pygame":
            raise ImportError("Pygame interdit dans ce processus")
sys.meta_path.insert(0, BlockPygame())
import JRPG.domain
import JRPG.application
import JRPG.bootstrap
import pkgutil
for package in (JRPG.domain, JRPG.application):
    for module in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        __import__(module.name)
from JRPG.domain.characters import Character, CharacterDefinition, ClassDefinition
from JRPG.domain.stats import CharacterStats
actor = Character(CharacterDefinition("hero", "Hero", ClassDefinition(
    "warrior", "Warrior", CharacterStats(100, 20, 10, 10, 10, 10, 10)
)))
actor.gain_experience(100)
assert actor.level == 2
from JRPG.domain.combat.battle import Battle
from JRPG.domain.combat.model import Action, BattleCommand, Combatant, EnemyDefinition, Outcome
from JRPG.infrastructure.random_source import SeededRandom
from JRPG.application.battle_session import BattleSession
from JRPG.domain.party import Party
from JRPG.domain.items import Inventory
from JRPG.domain.wallet import Wallet
opponent = EnemyDefinition("slime", "Slime", CharacterStats(1, 0, 0, 0, 0, 0, 0))
battle = Battle("smoke", (Combatant.from_character(actor), opponent.spawn("slime-1")))
session = BattleSession(battle, Party([actor]), Inventory(), Wallet())
battle.start()
battle.prepare_turn()
battle.execute(
    BattleCommand(actor.id, battle.turn_id, Action.ATTACK, ("slime-1",)), SeededRandom(1)
)
assert session.settle(SeededRandom(1)).outcome == Outcome.VICTORY
assert "pygame" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True, timeout=10)
