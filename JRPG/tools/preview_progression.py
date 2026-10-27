"""Aperçus des dialogues et menus via la boucle réelle ; aucune sauvegarde utilisateur."""

import os
from pathlib import Path
from unittest.mock import patch


def main() -> None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    from JRPG.application.saves import SaveService
    from JRPG.domain.world import MapPosition
    from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
    from JRPG.infrastructure.save_repository import JsonSaveRepository
    from JRPG.infrastructure.world_content import create_exploration_session
    from JRPG.presentation.adventure_scene import AdventureScene
    from JRPG.presentation.game_menu import MenuPage
    from JRPG.presentation.pygame_app import PygameApplication, WindowSettings

    root = Path(__file__).resolve().parents[1]
    folder = root / "docs" / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    for name in (
        "dialogue",
        "inventory",
        "equipment",
        "characters",
        "quests",
        "shop",
        "save_slots",
    ):
        session = create_exploration_session(position=MapPosition("village", 8.5 * 32, 8.5 * 32))
        assert session.story is not None
        session.wallet.credit(100)
        for identity in ("steel_sword", "travel_cloak", "bronze_ring"):
            session.inventory.add(session.story.content.item(identity))
        # Le dépôt n'est que consulté pour les étiquettes d'emplacements vides.
        saves = SaveService(JsonSaveRepository(root / ".preview-slots"), GameSnapshotMapper())
        scene = AdventureScene(session, saves)
        if name == "dialogue":
            scene.controller.interact()
        elif name == "equipment":
            scene.menus.open(MenuPage.EQUIPMENT_HERO)
            scene.menus.choose(0)
            scene.menus.choose(0)
            scene.menus.selected = next(
                index
                for index, entry in enumerate(scene.menus.entries)
                if entry.id == "steel_sword"
            )
        elif name == "shop":
            scene.menus.open_shop("oren")
            scene.menus.choose(0)
            scene.menus.selected = 2
        else:
            pages = {
                "inventory": MenuPage.INVENTORY,
                "characters": MenuPage.CHARACTERS,
                "quests": MenuPage.QUESTS,
                "save_slots": MenuPage.SAVE,
            }
            scene.menus.open(pages[name])
        output = folder / (name + ".png")

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
