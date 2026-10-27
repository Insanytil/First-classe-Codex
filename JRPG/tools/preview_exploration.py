"""Capturer les trois cartes via la vraie boucle SDL, sans écran physique."""

import os
from pathlib import Path
from unittest.mock import patch


def main() -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    from JRPG.domain.world import MapPosition
    from JRPG.infrastructure.world_content import create_exploration_session
    from JRPG.presentation.adventure_scene import AdventureScene
    from JRPG.presentation.pygame_app import PygameApplication, WindowSettings

    folder = Path(__file__).resolve().parents[1] / "docs" / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    for identity, column, row in (("village", 8, 10), ("forest", 18, 11), ("ruins", 14, 10)):
        output = folder / (identity + ".png")
        session = create_exploration_session(
            position=MapPosition(identity, (column + 0.5) * 32, (row + 0.5) * 32)
        )
        scene = AdventureScene(session)

        def capture(output: Path = output) -> None:
            surface = pygame.display.get_surface()
            assert surface is not None
            pygame.image.save(surface, str(output))

        with (
            patch("pygame.display.get_desktop_sizes", return_value=[(1440, 1000)]),
            patch("pygame.event.get", side_effect=[[], [pygame.event.Event(pygame.QUIT)]]),
            patch("pygame.display.flip", side_effect=capture),
        ):
            PygameApplication(WindowSettings(), scene).run()
        print(output)


if __name__ == "__main__":
    main()
