"""Capturer le boss et son annonce avec les vraies scènes, sans installation."""

import os
from pathlib import Path


def main() -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    from JRPG.infrastructure.world_content import create_exploration_session
    from JRPG.presentation.battle_controller import BattleController, Playback
    from JRPG.presentation.battle_scene import BattleScene

    session = create_exploration_session()
    for hero in session.party.members:
        hero.gain_experience(300)
        hero.set_resources(hero.stats.hp, hero.stats.mp)
    encounter = session.encounter_factory.create(
        "preview_sentinel", ("boss",), session.party, session.inventory, session.wallet
    )
    scene = BattleScene(lambda: BattleController(encounter))
    folder = Path(__file__).resolve().parents[1] / "docs" / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    canvas = pygame.Surface((640, 360))
    overlay = pygame.Surface((640, 360), pygame.SRCALPHA)

    def capture(name: str) -> None:
        scene.draw_background(canvas)
        scene.draw_foreground(overlay)
        canvas.blit(overlay, (0, 0))
        pygame.image.save(canvas, str(folder / f"sentinel-{name}.png"))

    try:
        capture("ready")
        charged = False
        for _ in range(100):
            controller = scene.controller
            if controller.threat_hint and not charged:
                capture("charge")
                charged = True
            playback = controller.playback
            if playback is not None and playback.result.command.ability_id == "sentinel_cleave":
                scene.update(max(0.0, Playback.IMPACT - playback.elapsed))
                capture("impact")
                break
            if controller.accepting_input:
                controller.select(2 if charged else 5)
            scene.update(0.1)
        else:
            raise RuntimeError("La séquence d'attaque du boss n'a pas été capturée.")
        print(folder / "sentinel-charge.png")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
