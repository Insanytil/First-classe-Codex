"""Exporter une vraie frame de la boucle graphique via SDL dummy, sans écran."""

import os
from pathlib import Path
from unittest.mock import patch


def main() -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    from JRPG.bootstrap import battle_preview as launch

    output = Path(__file__).resolve().parents[1] / "docs" / "previews" / "battle.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    def capture() -> None:
        surface = pygame.display.get_surface()
        assert surface is not None
        pygame.image.save(surface, str(output))

    with (
        patch("pygame.display.get_desktop_sizes", return_value=[(1440, 1000)]),
        patch("pygame.event.get", side_effect=[[], [pygame.event.Event(pygame.QUIT)]]),
        patch("pygame.display.flip", side_effect=capture),
    ):
        launch()
    print(output)


if __name__ == "__main__":
    main()
