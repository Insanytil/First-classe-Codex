"""Captures animées des vraies scènes SDL, consultables dans un navigateur hors ligne."""

import os
from pathlib import Path


def main() -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    from JRPG.domain.world import MapPosition
    from JRPG.infrastructure.training_encounter import create_training_encounter
    from JRPG.infrastructure.world_content import create_exploration_session
    from JRPG.presentation.adventure_scene import AdventureScene
    from JRPG.presentation.battle_controller import BattleController, Playback
    from JRPG.presentation.battle_scene import BattleScene

    folder = Path(__file__).resolve().parents[1] / "docs" / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    try:
        for identity, column, row in (("village", 19, 15), ("forest", 18, 11), ("ruins", 14, 10)):
            session = create_exploration_session(
                position=MapPosition(identity, (column + 0.5) * 32, (row + 0.5) * 32)
            )
            scene = AdventureScene(session)
            strip = pygame.Surface((640, 360 * 8))
            canvas, overlay = (
                pygame.Surface((640, 360)),
                pygame.Surface((640, 360), pygame.SRCALPHA),
            )
            for index in range(8):
                scene.draw_background(canvas)
                scene.draw_foreground(overlay)
                canvas.blit(overlay, (0, 0))
                strip.blit(canvas, (0, index * 360))
                scene.update(0.25)
            pygame.image.save(strip, str(folder / f"living-{identity}.png"))

        for kind in ("wolf", "slime"):
            battle_scene = BattleScene(lambda: BattleController(create_training_encounter()))
            controller = battle_scene.controller
            for _ in range(50):
                current = controller.encounter.battle.current
                if (
                    controller.playback is None
                    and current is not None
                    and current.id.startswith(kind + "-")
                ):
                    battle_scene.update(0.35)
                    break
                if controller.accepting_input:
                    controller.select(5)
                battle_scene.update(Playback.DURATION)
            playback = controller.playback
            if playback is None or not playback.result.command.actor_id.startswith(kind + "-"):
                raise RuntimeError(f"Aucune attaque {kind} disponible pour la capture.")
            strip = pygame.Surface((640, 360 * 8))
            canvas, overlay = (
                pygame.Surface((640, 360)),
                pygame.Surface((640, 360), pygame.SRCALPHA),
            )
            previous = 0.0
            for index, moment in enumerate((0.0, 0.08, 0.16, 0.24, 0.32, 0.44, 0.56, 0.70)):
                battle_scene.update(moment - previous)
                previous = moment
                battle_scene.draw_background(canvas)
                battle_scene.draw_foreground(overlay)
                canvas.blit(overlay, (0, 0))
                strip.blit(canvas, (0, index * 360))
                if index == 3:
                    pygame.image.save(canvas, str(folder / f"{kind}-contact.png"))
            pygame.image.save(strip, str(folder / f"attack-{kind}.png"))
        print(folder / "animations.html")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
