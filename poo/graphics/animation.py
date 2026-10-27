"""Trajectoires et poses, calculées sans Pygame pour rester testables."""
from dataclasses import dataclass
import math


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    ground_y: float
    scale_x: float = 1.0
    scale_y: float = 1.0


def attack_pose(kind: str, progress: float, start: tuple[float, float], target: tuple[float, float], contact: float = .55) -> Pose:
    """Anticipation, approche, contact et retour à la position d'origine."""
    p = clamp(progress)
    sx, sy = start
    tx, ty = target
    if kind not in ('slash', 'smash', 'claw', 'jump', 'heavy', 'enemy'):
        return Pose(sx, sy, sy)
    travel_start = .18
    arrival = contact - .10 if kind != 'jump' else contact
    if p < travel_start:
        back = math.sin(p / travel_start * math.pi) * 12
        x = sx - math.copysign(back, tx - sx)
        if kind == 'jump':
            squash = math.sin(p / travel_start * math.pi)
            return Pose(x, sy, sy, 1 + squash * .22, 1 - squash * .25)
        return Pose(x, sy, sy)
    if p <= contact:
        travel = ease((p - travel_start) / (arrival - travel_start))
        x, ground = sx + (tx - sx) * travel, sy + (ty - sy) * travel
        if kind == 'jump':
            flight = clamp((p - travel_start) / (contact - travel_start))
            height = math.sin(math.pi * flight) * 140
            return Pose(x, ground - height, ground, .93, 1.12)
        return Pose(x, ground, ground)
    returning = clamp((p - contact) / (1 - contact))
    travel = ease(returning)
    x, ground = tx + (sx - tx) * travel, ty + (sy - ty) * travel
    if kind == 'jump':
        squash = max(0, 1 - returning * 7)
        hop = math.sin(math.pi * returning) * 38
        return Pose(x, ground - hop, ground, 1 + squash * .25, 1 - squash * .35)
    return Pose(x, ground, ground)


def frame_at(progress: float, count: int) -> int:
    return min(count - 1, int(clamp(progress) * count))


def action_frame_at(kind: str, progress: float, impact_ratio: float) -> int:
    """La pose de contact tombe exactement sur l'instant des dégâts."""
    contact_frame = 5 if kind in ('jump', 'shoot') else 4
    progress = clamp(progress)
    if progress <= impact_ratio:
        return min(contact_frame, int(progress / impact_ratio * contact_frame + 1e-9))
    return min(7, contact_frame + int((progress - impact_ratio) / (1 - impact_ratio) * (8 - contact_frame)))
