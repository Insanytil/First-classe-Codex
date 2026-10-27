"""La trajectoire et la pose de contact restent synchronisées au même impact."""

import pytest

from JRPG.presentation.attack_animation import attack_pose, contact_frame


@pytest.mark.parametrize("contact", [4, 5])
def test_contact_pose_reaches_target_exactly_at_impact(contact: int) -> None:
    assert contact_frame(0, 0.24, 0.72, contact) == 0
    assert contact_frame(0.239, 0.24, 0.72, contact) < contact
    assert contact_frame(0.24, 0.24, 0.72, contact) == contact
    assert contact_frame(0.72, 0.24, 0.72, contact) == 7
    pose = attack_pose(0.24, 0.24, 0.72, (220, 95), (375, 75), jump=contact == 5)
    assert pose.x == pytest.approx(375)
    assert pose.y == pytest.approx(75)
    assert pose.ground_y == pytest.approx(75)


def test_jump_has_height_and_returns_to_start_without_drifting() -> None:
    pose = attack_pose(0.12, 0.24, 0.72, (220, 95), (375, 75), jump=True)
    assert pose.y < pose.ground_y
    for elapsed in (-1, 0, 0.72, 10):
        pose = attack_pose(elapsed, 0.24, 0.72, (220, 95), (375, 75), jump=True)
        assert pose.x == pytest.approx(220)
        assert pose.y == pytest.approx(95)
    with pytest.raises(ValueError):
        contact_frame(0, 0.24, 0.72, 8)
    with pytest.raises(ValueError):
        attack_pose(0, 0, 0.72, (0, 0), (1, 1))
