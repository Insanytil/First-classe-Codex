"""Captures du nouveau bestiaire, de Tala et des consommables depuis les scènes."""

import os
from pathlib import Path


def main() -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    from JRPG.domain.world import MapPosition
    from JRPG.infrastructure.world_content import create_exploration_session
    from JRPG.presentation.adventure_scene import AdventureScene
    from JRPG.presentation.battle_controller import BattleController
    from JRPG.presentation.battle_scene import BattleScene
    from JRPG.presentation.game_menu import MenuPage

    folder = Path(__file__).resolve().parents[1] / "docs" / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((640, 360))
    canvas, overlay = pygame.Surface((640, 360)), pygame.Surface((640, 360), pygame.SRCALPHA)
    try:
        session = create_exploration_session()
        encounter = session.encounter_factory.create(
            "preview_catalog",
            ("wisp", "briar", "raven"),
            session.party,
            session.inventory,
            session.wallet,
        )
        battle = BattleScene(lambda: BattleController(encounter))
        battle.draw_background(canvas)
        battle.draw_foreground(overlay)
        canvas.blit(overlay, (0, 0))
        pygame.image.save(canvas, str(folder / "bestiary.png"))
        session = create_exploration_session(position=MapPosition("village", 11.5 * 32, 14.5 * 32))
        scene = AdventureScene(session)
        scene.controller.interact()
        scene.update(0.5)
        scene.draw_background(canvas)
        scene.draw_foreground(overlay)
        canvas.blit(overlay, (0, 0))
        pygame.image.save(canvas, str(folder / "tala.png"))
        scene.controller.close_dialogue()
        assert session.story is not None
        for identity in ("ether", "high_potion", "antidote"):
            session.inventory.add(session.story.content.item(identity))
        scene.menus.open(MenuPage.INVENTORY)
        scene.menus.move(
            next(index for index, entry in enumerate(scene.menus.entries) if entry.id == "ether")
        )
        scene.draw_background(canvas)
        scene.draw_foreground(overlay)
        canvas.blit(overlay, (0, 0))
        pygame.image.save(canvas, str(folder / "consumables.png"))
        print(folder / "bestiary.png")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
