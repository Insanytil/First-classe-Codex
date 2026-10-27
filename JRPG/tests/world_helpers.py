"""Trajets de test : aucun algorithme de pathfinding ajouté au jeu."""

from collections import deque
from math import hypot

from JRPG.application.exploration import ExplorationSession
from JRPG.domain.combat.model import Action, BattleCommand, BattleState, Side
from JRPG.domain.world import MapPosition, World


def walk_to(session: ExplorationSession, identity: str) -> None:
    """Le test calcule un trajet ; le jeu n'implémente pas de pathfinding automatique."""
    world = session.world
    target = next(entry for entry in world.visible_objects() if entry.id == identity)
    start = int(world.position.x // 32), int(world.position.y // 32)
    paths: deque[tuple[tuple[int, int], tuple[tuple[int, int], ...]]] = deque([(start, ())])
    seen = {start}
    while paths:
        (x, y), path = paths.popleft()
        center = ((x + 0.5) * 32, (y + 0.5) * 32)
        nearest = min(
            world.visible_objects(),
            key=lambda entry: (
                hypot(entry.center[0] - center[0], entry.center[1] - center[1]),
                entry.id,
            ),
        )
        if (
            nearest == target
            and hypot(target.center[0] - center[0], target.center[1] - center[1])
            <= World.INTERACTION_RANGE
        ):
            for dx, dy in path:
                session.move(dx, dy, 32 / World.SPEED)
            assert world.nearby() == target
            return
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cell = x + dx, y + dy
            if cell in seen or min(cell) < 0:
                continue
            point = MapPosition(world.position.map_id, (cell[0] + 0.5) * 32, (cell[1] + 0.5) * 32)
            if world.walkable(point):
                seen.add(cell)
                paths.append((cell, (*path, (dx, dy))))
    raise AssertionError(f"Interaction inaccessible : {identity}")


def finish_battle(session: ExplorationSession, flee: bool = False, lose: bool = False) -> None:
    encounter = session.active_encounter
    assert encounter is not None
    battle = encounter.battle
    battle.start()
    for _ in range(250):
        actor = battle.prepare_turn()
        if actor.side == Side.ALLIES:
            if flee:
                choice = BattleCommand(actor.id, battle.turn_id, Action.FLEE)
            elif lose:
                choice = BattleCommand(actor.id, battle.turn_id, Action.PASS)
            else:
                choice = next(
                    entry for entry in battle.legal_commands() if entry.action == Action.ATTACK
                )
        elif lose:
            choice = next(
                entry for entry in battle.legal_commands() if entry.action == Action.ATTACK
            )
        else:
            choice = encounter.ai.choose(battle, encounter.random)
        battle.execute(choice, encounter.random)
        if battle.state == BattleState.FINISHED:
            return
    raise AssertionError("Combat non terminé.")
