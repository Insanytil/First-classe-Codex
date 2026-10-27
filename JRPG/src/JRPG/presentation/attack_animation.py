"""Trajectoires inspirées de poo ; la présentation ne résout aucune action."""

from dataclasses import dataclass
from math import pi, sin


@dataclass(frozen=True, slots=True)
class AttackPose:
    x: float
    y: float
    ground_y: float


def contact_frame(elapsed: float, impact: float, duration: float, contact: int = 4) -> int:
    if not 0 < impact < duration or not 1 <= contact <= 6:
        raise ValueError("Paramètres de synchronisation invalides.")
    if elapsed <= impact:
        return min(contact, int(max(0.0, elapsed) / impact * contact))
    return min(7, contact + int((elapsed - impact) / (duration - impact) * (8 - contact)))


def attack_pose(
    elapsed: float,
    impact: float,
    duration: float,
    start: tuple[int, int],
    target: tuple[int, int],
    *,
    jump: bool = False,
) -> AttackPose:
    if not 0 < impact < duration:
        raise ValueError("Paramètres de trajectoire invalides.")
    elapsed = min(duration, max(0.0, elapsed))
    if elapsed <= impact:
        progress = elapsed / impact
        approach = max(0.0, (progress - 0.18) / 0.82)
        travel = approach * approach * (3 - 2 * approach)
        lift = sin(progress * pi) * 35 if jump else 0.0
    else:
        progress = (elapsed - impact) / (duration - impact)
        travel = 1 - progress * progress * (3 - 2 * progress)
        lift = sin(progress * pi) * 10 if jump else 0.0
    x = start[0] + (target[0] - start[0]) * travel
    ground_y = start[1] + (target[1] - start[1]) * travel
    return AttackPose(x, ground_y - lift, ground_y)
