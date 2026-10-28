"""Interaction et lecture animée de résultats ; aucune règle de dégâts ici."""

from dataclasses import dataclass
from enum import StrEnum

from JRPG.application.battle_session import SettlementResult
from JRPG.application.encounter import BattleEncounter
from JRPG.domain.combat.model import (
    Action,
    BattleActionResult,
    BattleCommand,
    BattleEvent,
    BattleState,
    EventKind,
    Side,
    StatusKind,
)
from JRPG.domain.errors import DomainError


class MenuMode(StrEnum):
    ACTION = "action"
    SKILL = "skill"
    ITEM = "item"
    TARGET = "target"


@dataclass(frozen=True, slots=True)
class MenuOption:
    label: str
    reason: str | None = None
    commands: tuple[BattleCommand, ...] = ()
    action: Action | None = None


@dataclass(slots=True)
class Playback:
    result: BattleActionResult
    elapsed: float = 0.0

    IMPACT = 0.24
    DURATION = 0.72


GROUPS = (
    (Action.ATTACK, "Attaquer"),
    (Action.SKILL, "Compétences"),
    (Action.DEFEND, "Défendre"),
    (Action.ITEM, "Objets"),
    (Action.FLEE, "Fuir"),
    (Action.PASS, "Passer"),
)


class BattleController:
    def __init__(self, encounter: BattleEncounter) -> None:
        self.encounter = encounter
        self.mode = MenuMode.ACTION
        self.selected = 0
        self.message = ""
        self.playback: Playback | None = None
        self.settlement: SettlementResult | None = None
        self.displayed = encounter.battle.combatants
        self._target_options: tuple[MenuOption, ...] = ()
        self._return_mode = MenuMode.ACTION
        self._enemy_elapsed = 0.0
        opponents = ", ".join(
            fighter.name for fighter in encounter.battle.combatants if fighter.side == Side.ENEMIES
        )
        self.log: tuple[str, ...] = (f"Adversaires : {opponents}.",)
        encounter.battle.start()
        self._advance()

    @property
    def accepting_input(self) -> bool:
        current = self.encounter.battle.current
        return self.playback is None and current is not None and current.side == Side.ALLIES

    @property
    def options(self) -> tuple[MenuOption, ...]:
        if not self.accepting_input:
            return ()
        if self.mode == MenuMode.TARGET:
            return self._target_options
        candidates = self.encounter.battle.candidate_commands()
        if self.mode == MenuMode.ACTION:
            groups: list[MenuOption] = []
            for action, label in GROUPS:
                variants = tuple(command for command in candidates if command.action == action)
                reason = self._reason(variants)
                groups.append(MenuOption(label, reason, variants, action))
            return tuple(groups)
        action = Action.SKILL if self.mode == MenuMode.SKILL else Action.ITEM
        grouped: dict[str, list[BattleCommand]] = {}
        for command in candidates:
            if command.action == action:
                key = command.ability_id if action == Action.SKILL else command.item_id
                grouped.setdefault(key, []).append(command)
        options: list[MenuOption] = []
        for key, commands in grouped.items():
            if action == Action.SKILL:
                ability = next(entry for entry in self.encounter.abilities if entry.id == key)
                label = f"{ability.name} · {ability.cost} PM"
            else:
                item = next(
                    entry.item for entry in self.encounter.consumables if entry.item.id == key
                )
                count = next(
                    (
                        stack.quantity
                        for stack in self.encounter.battle.items
                        if stack.item.id == key
                    ),
                    0,
                )
                label = f"{item.name} ×{count}"
            variants = tuple(commands)
            options.append(MenuOption(label, self._reason(variants), variants, action))
        return tuple(options)

    def _reason(self, commands: tuple[BattleCommand, ...]) -> str | None:
        if not commands:
            return "Aucun choix disponible."
        reasons = tuple(self.encounter.battle.command_error(command) for command in commands)
        return None if None in reasons else reasons[0]

    @property
    def target_ids(self) -> tuple[str, ...]:
        if self.mode != MenuMode.TARGET or not self.options:
            return ()
        return self.options[self.selected].commands[0].targets

    @property
    def focus_hint(self) -> str:
        options = self.options
        if options:
            option = options[self.selected]
            if option.reason:
                return option.reason
            if self.mode in {MenuMode.SKILL, MenuMode.ITEM, MenuMode.TARGET} and option.commands:
                command = option.commands[0]
                ability = next(
                    (entry for entry in self.encounter.abilities if entry.id == command.ability_id),
                    None,
                )
                if command.item_id:
                    consumable = next(
                        (
                            entry
                            for entry in self.encounter.consumables
                            if entry.item.id == command.item_id
                        ),
                        None,
                    )
                    ability = consumable.ability if consumable is not None else None
                if ability is not None and ability.description:
                    return ability.description
            return self.message
        return self.message

    def move(self, amount: int) -> None:
        options = self.options
        if options:
            self.selected = (self.selected + amount) % len(options)
            self.message = self._selection_hint()

    @property
    def threat_hint(self) -> str:
        charging = next(
            (
                fighter
                for fighter in self.displayed
                if fighter.side == Side.ENEMIES
                and fighter.hp
                and fighter.has_status(StatusKind.CHARGING)
            ),
            None,
        )
        return f"{charging.name} prépare sa frappe : défendez-vous !" if charging else ""

    def select(self, index: int) -> None:
        if self.accepting_input and 0 <= index < len(self.options):
            self.selected = index
            self.confirm()

    def back(self) -> None:
        if not self.accepting_input:
            return
        self.mode = self._return_mode if self.mode == MenuMode.TARGET else MenuMode.ACTION
        self.selected = 0
        self.message = self._selection_hint()

    def _selection_hint(self) -> str:
        return {
            MenuMode.ACTION: "Choisissez une action.",
            MenuMode.SKILL: "Choisissez une compétence.",
            MenuMode.ITEM: "Choisissez un objet.",
            MenuMode.TARGET: "Choisissez la cible puis validez.",
        }[self.mode]

    def confirm(self) -> None:
        if not self.accepting_input or not self.options:
            return
        option = self.options[self.selected]
        if option.reason is not None:
            self.message = option.reason
            return
        if self.mode == MenuMode.TARGET:
            self._submit(option.commands[0])
            return
        if self.mode == MenuMode.ACTION and option.action in {Action.SKILL, Action.ITEM}:
            self.mode = MenuMode.SKILL if option.action == Action.SKILL else MenuMode.ITEM
            self.selected = 0
            self.message = (
                "Choisissez une compétence."
                if self.mode == MenuMode.SKILL
                else "Choisissez un objet."
            )
            return
        self._return_mode = self.mode
        valid = tuple(
            command
            for command in option.commands
            if self.encounter.battle.command_error(command) is None
        )
        if valid[0].targets:
            names = {fighter.id: fighter.name for fighter in self.displayed}
            self._target_options = tuple(
                MenuOption(
                    " + ".join(names[identity] for identity in command.targets), commands=(command,)
                )
                for command in valid
            )
            self.mode = MenuMode.TARGET
            self.selected = 0
            self.message = "Choisissez la cible puis validez."
        else:
            self._submit(valid[0])

    def click_target(self, identity: str) -> None:
        if self.mode != MenuMode.TARGET:
            return
        for index, option in enumerate(self.options):
            if identity in option.commands[0].targets:
                self.select(index)
                return

    def _submit(self, command: BattleCommand) -> None:
        try:
            result = self.encounter.battle.execute(command, self.encounter.random)
        except DomainError as error:
            self.message = str(error)
            return
        self.playback = Playback(result)
        self.message = "Résolution de l'action…"
        names = {fighter.id: fighter.name for fighter in result.combatants}
        names.update({ability.id: ability.name for ability in self.encounter.abilities})
        self.log = (*self.log, *(describe_event(event, names) for event in result.events))[-80:]

    def update(self, elapsed: float) -> None:
        if elapsed < 0:
            raise ValueError("Le temps de présentation doit être positif.")
        if self.playback is not None:
            self.playback.elapsed += elapsed
            if self.playback.elapsed >= Playback.IMPACT:
                self.displayed = self.playback.result.combatants
            if self.playback.elapsed >= Playback.DURATION:
                self.playback = None
                self._advance()
        elif self.encounter.battle.current is not None and not self.accepting_input:
            self._enemy_elapsed += elapsed
            if self._enemy_elapsed >= 0.35:
                command = self.encounter.ai.choose(self.encounter.battle, self.encounter.random)
                self._submit(command)

    def _advance(self) -> None:
        battle = self.encounter.battle
        self.mode, self.selected = MenuMode.ACTION, 0
        self._enemy_elapsed = 0.0
        if battle.state == BattleState.FINISHED:
            self.settlement = self.encounter.session.settle(self.encounter.random)
            self.message = "Combat terminé. Appuyez sur R pour rejouer."
        else:
            actor = battle.prepare_turn()
            self.displayed = battle.combatants
            self.message = f"À {actor.name} de jouer."


def describe_event(event: BattleEvent, names: dict[str, str]) -> str:
    actor, target = (
        names.get(event.actor_id, event.actor_id),
        names.get(event.target_id, event.target_id),
    )
    if event.kind == EventKind.DAMAGE:
        label = "critique " if event.critical else ""
        return f"{target} : −{event.amount} PV ({label}{event.status_id or actor})."
    if event.kind == EventKind.HEAL:
        return f"{target} récupère {event.amount} PV."
    if event.kind == EventKind.MANA_RESTORED:
        return f"{target} récupère {event.amount} PM."
    if event.kind == EventKind.REVIVED:
        return f"{target} revient avec {event.amount} PV."
    if event.kind == EventKind.MISS:
        return f"{actor} manque {target}."
    if event.kind == EventKind.MANA_SPENT:
        return f"{actor} dépense {event.amount} PM."
    if event.kind == EventKind.STATUS_APPLIED:
        return f"{target} : {names.get(event.status_id, event.status_id)}."
    if event.kind == EventKind.STATUS_EXPIRED:
        return f"{target} : fin de {names.get(event.status_id, event.status_id)}."
    labels = {
        EventKind.ENEMY_DEFEATED: f"{target} est vaincu.",
        EventKind.KNOCKED_OUT: f"{target} est KO.",
        EventKind.DEFENDED: f"{actor} se protège.",
        EventKind.PASSED: f"{actor} passe son tour.",
        EventKind.FLEE_FAILED: "La fuite échoue.",
        EventKind.BATTLE_WON: "Victoire !",
        EventKind.BATTLE_LOST: "L'équipe est vaincue.",
        EventKind.FLED: "Vous avez quitté le combat.",
    }
    return labels[event.kind]
