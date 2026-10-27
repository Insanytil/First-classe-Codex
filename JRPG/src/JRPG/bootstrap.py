"""Point de composition ; les imports graphiques restent différés au lancement."""


def main() -> None:
    from JRPG.application.saves import SaveService
    from JRPG.infrastructure.game_snapshot import GameSnapshotMapper
    from JRPG.infrastructure.save_repository import JsonSaveRepository, default_save_directory
    from JRPG.infrastructure.world_content import create_exploration_session
    from JRPG.presentation.adventure_scene import AdventureScene
    from JRPG.presentation.pygame_app import PygameApplication, WindowSettings

    saves = SaveService(JsonSaveRepository(default_save_directory()), GameSnapshotMapper())
    scene = AdventureScene(create_exploration_session(), saves)
    PygameApplication(WindowSettings(), scene).run()


def battle_preview() -> None:
    """Point de composition de la bataille isolée, pour tests et aperçu."""
    from JRPG.infrastructure.training_encounter import create_training_encounter
    from JRPG.presentation.battle_controller import BattleController
    from JRPG.presentation.battle_scene import BattleScene
    from JRPG.presentation.pygame_app import PygameApplication, WindowSettings

    scene = BattleScene(lambda: BattleController(create_training_encounter()))
    PygameApplication(WindowSettings(title="JRPG — Combat"), scene).run()
