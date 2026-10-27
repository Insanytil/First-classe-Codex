"""État d'interaction de l'exploration, sans Pygame ni règles de collision."""

from dataclasses import dataclass
from math import isfinite

from JRPG.application.encounter import BattleEncounter
from JRPG.application.exploration import ExplorationSession
from JRPG.application.progression import Conversation
from JRPG.domain.errors import DomainError
from JRPG.domain.world import MapPosition, ObjectKind


@dataclass(frozen=True, slots=True)
class Camera:
    x: float
    y: float

    @classmethod
    def follow(
        cls, position: MapPosition, map_size: tuple[int, int], viewport: tuple[int, int]
    ) -> Camera:
        offsets = []
        for value, size, span in zip((position.x, position.y), map_size, viewport, strict=True):
            offsets.append(
                max(0, min(value - span / 2, size - span)) if size >= span else (size - span) / 2
            )
        return cls(*offsets)

    def project(self, x: float, y: float) -> tuple[int, int]:
        return round(x - self.x), round(y - self.y)


class ExplorationController:
    def __init__(self, session: ExplorationSession) -> None:
        self.session = session
        self.dialogue = ""
        self.speaker = ""
        self.conversation: Conversation | None = None
        self.dialogue_selected = 0
        self.shop_requested: str | None = None
        self.message = (
            f"Explorez {session.world.current_map.name}. Approchez les passages puis utilisez E."
        )
        self._toast = 5.0
        self.walk_phase = 0.0
        self.facing = (0.0, 1.0)

    def update(self, dx: float, dy: float, elapsed: float) -> None:
        if not isfinite(elapsed) or elapsed < 0:
            raise ValueError("Temps de présentation invalide.")
        self._toast = max(0, self._toast - elapsed)
        if self._toast == 0:
            self.message = ""
        if self.dialogue or self.session.active_encounter is not None:
            return
        before = self.session.world.position
        self.session.move(dx, dy, elapsed)
        if self.session.world.position != before:
            self.walk_phase += elapsed
            self.facing = dx, dy

    def interact(self) -> BattleEncounter | None:
        if self.dialogue:
            if self.conversation is not None:
                self.choose_dialogue(self.dialogue_selected)
            else:
                self.close_dialogue()
            return None
        result = self.session.interact()
        if result is None:
            self.message, self._toast = "Approchez un personnage, un coffre ou un passage.", 2.5
            return None
        if result.subject.kind in {ObjectKind.NPC, ObjectKind.CHEST}:
            self.dialogue, self.speaker = result.message, result.subject.name
            story = self.session.story
            definition = story.dialogue_for(result.subject.id) if story is not None else None
            if (
                result.subject.kind == ObjectKind.NPC
                and definition is not None
                and story is not None
            ):
                self.conversation = Conversation(story, definition)
                node = self.conversation.node
                assert node is not None
                self.dialogue = node.text
                self.dialogue_selected = 0
        else:
            self.message, self._toast = result.message, 3.0
        return result.encounter

    def close_dialogue(self) -> None:
        self.dialogue, self.speaker = "", ""
        self.conversation = None
        self.dialogue_selected = 0

    def move_dialogue(self, amount: int) -> None:
        if self.conversation is not None and self.conversation.choices:
            self.dialogue_selected = (self.dialogue_selected + amount) % len(
                self.conversation.choices
            )

    def choose_dialogue(self, index: int) -> None:
        conversation = self.conversation
        if conversation is None or not 0 <= index < len(conversation.choices):
            return
        try:
            result = conversation.choose(conversation.choices[index].id)
        except DomainError as error:
            self.message, self._toast = str(error), 4.0
            return
        self.shop_requested = result.shop_id
        node = conversation.node
        if node is None:
            self.close_dialogue()
        else:
            self.dialogue = (result.notice + " " if result.notice else "") + node.text
            self.dialogue_selected = 0
        if result.notice:
            self.message, self._toast = result.notice, 5.0

    def after_combat(self) -> None:
        result = self.session.finish_encounter()
        messages = {
            "victory": "Victoire ! Cette rencontre ne réapparaîtra plus.",
            "fled": "Le groupe s'est replié. Vous pouvez revenir affronter ces ennemis.",
            "defeat": f"Le groupe est de retour : {self.session.world.current_map.name}.",
        }
        self.message, self._toast = messages[result.outcome], 5.0
