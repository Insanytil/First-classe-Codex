"""Reconstruction depuis un catalogue connu ; aucune définition lue depuis le save."""

from math import isfinite

from JRPG.application.exploration import ExplorationSession
from JRPG.application.progression import AdventureProgress
from JRPG.application.save_data import GameSnapshot, HeroSave, ShopSave, StackSave
from JRPG.application.saves import SaveError
from JRPG.domain.characters import Character, CharacterState
from JRPG.domain.economy import Shop
from JRPG.domain.errors import DomainError
from JRPG.domain.items import Inventory, ItemQuantity
from JRPG.domain.party import Party
from JRPG.domain.quests import QuestBook
from JRPG.domain.wallet import Wallet
from JRPG.domain.world import World, WorldState
from JRPG.infrastructure.world_content import create_exploration_session


class GameSnapshotMapper:
    VERSION = 1
    CONTENT_VERSION = 1

    def capture(self, session: ExplorationSession) -> GameSnapshot:
        if session.active_encounter is not None or session.story is None:
            raise SaveError("Sauvegarde disponible uniquement pendant l'exploration.")
        state = session.world.state
        return GameSnapshot(
            self.VERSION,
            self.CONTENT_VERSION,
            session.world.position,
            session.world.origin,
            tuple(
                HeroSave(
                    member.id,
                    member.definition.character_class.id,
                    member.experience,
                    member.hp,
                    member.mp,
                    member.skills,
                    tuple((slot, item.id) for slot, item in member.equipment),
                )
                for member in session.party.members
            ),
            tuple(StackSave(stack.item.id, stack.quantity) for stack in session.inventory.stacks),
            session.wallet.gold,
            tuple(sorted(state.opened_chests)),
            tuple(sorted(state.cleared_encounters)),
            tuple(sorted(state.visited_maps)),
            tuple(sorted(state.talked_to)),
            tuple(sorted(state.flags)),
            session.story.quests.states,
            tuple(ShopSave(key, shop.stock) for key, shop in sorted(session.story.shops.items())),
            session.play_seconds,
            session.encounter_factory.checkpoint(),
        )

    def restore(self, snapshot: GameSnapshot) -> ExplorationSession:
        try:
            if snapshot.version != self.VERSION or snapshot.content_version != self.CONTENT_VERSION:
                raise SaveError("Version de sauvegarde ou de contenu non prise en charge.")
            if not isfinite(snapshot.play_seconds) or snapshot.play_seconds < 0:
                raise SaveError("Durée de jeu invalide.")
            fresh = create_exploration_session()
            assert fresh.story is not None
            content = fresh.story.content
            for identifiers in (
                snapshot.opened_chests,
                snapshot.cleared_encounters,
                snapshot.visited_maps,
                snapshot.talked_to,
                snapshot.flags,
            ):
                if len(set(identifiers)) != len(identifiers):
                    raise SaveError("Marqueur de monde dupliqué.")
            if not {snapshot.position.map_id, snapshot.origin.map_id} <= set(snapshot.visited_maps):
                raise SaveError("Position hors des cartes visitées.")
            state = WorldState(
                frozenset(snapshot.opened_chests),
                frozenset(snapshot.cleared_encounters),
                visited_maps=frozenset(snapshot.visited_maps),
                talked_to=frozenset(snapshot.talked_to),
                flags=frozenset(snapshot.flags),
            )
            world = World(fresh.world.maps, snapshot.position, state)
            world.set_origin(snapshot.origin)
            content.validate_world(world)
            templates = {member.id: member for member in fresh.party.members}
            members = []
            known_skills = {entry.id for entry in fresh.encounter_factory.abilities}
            for saved in snapshot.heroes:
                if saved.id not in templates:
                    raise SaveError("Personnage inconnu.")
                template = templates[saved.id]
                if (
                    saved.class_id != template.definition.character_class.id
                    or not set(saved.skills) <= known_skills
                ):
                    raise SaveError("Classe ou compétence inconnue.")
                equipment = tuple((slot, content.item(key)) for slot, key in saved.equipment)
                members.append(
                    Character.from_state(
                        template.definition,
                        CharacterState(
                            saved.experience, saved.hp, saved.mp, saved.skills, equipment
                        ),
                        template.progression,
                    )
                )
            party = Party(members)
            if len({stack.id for stack in snapshot.inventory}) != len(snapshot.inventory):
                raise SaveError("Pile de sac dupliquée.")
            inventory = Inventory(
                ItemQuantity(content.item(stack.id), stack.quantity) for stack in snapshot.inventory
            )
            wallet = Wallet(snapshot.gold)
            progress = AdventureProgress(content, state, party, inventory, wallet)
            progress.quests = QuestBook(content.quests, state, snapshot.quests)
            content.validate_flags(progress.quests, state.flags)
            if len({shop.id for shop in snapshot.shops}) != len(snapshot.shops) or {
                shop.id for shop in snapshot.shops
            } != set(progress.shops):
                raise SaveError("Boutiques sauvegardées incohérentes.")
            for saved_shop in snapshot.shops:
                definition = next(entry for entry in content.shops if entry.id == saved_shop.id)
                progress.shops[saved_shop.id] = Shop(
                    definition.id, definition.name, definition.offers, saved_shop.stock
                )
            fresh.encounter_factory.restore_checkpoint(snapshot.random)
            session = ExplorationSession(
                world, party, inventory, wallet, fresh.encounter_factory, progress
            )
            session.play_seconds = snapshot.play_seconds
            return session
        except (DomainError, KeyError, ValueError, TypeError) as error:
            raise SaveError(f"Partie invalide : {error}") from error
