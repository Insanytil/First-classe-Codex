"""Machine à états synchrone : validation, résolution locale puis publication."""

from dataclasses import replace

from JRPG.domain.combat.effects import ApplyStatus, Damage, with_statuses
from JRPG.domain.combat.model import (
    Ability,
    Action,
    ActiveStatus,
    BattleActionResult,
    BattleCommand,
    BattleEvent,
    BattleRuleError,
    BattleState,
    Combatant,
    Consumable,
    EventKind,
    InvalidTarget,
    Outcome,
    RandomSource,
    Side,
    StatusDefinition,
    StatusKind,
    TargetLife,
    TargetRule,
    TargetSide,
)
from JRPG.domain.errors import InsufficientMana, MissingItem
from JRPG.domain.items import Inventory, ItemQuantity
from JRPG.domain.stats import require_integer, require_text

BASIC_ATTACK = Ability("attack", "Attaquer", 0, TargetRule(), (Damage(),))


class Battle:
    def __init__(
        self,
        battle_id: str,
        combatants: tuple[Combatant, ...],
        abilities: tuple[Ability, ...] = (),
        consumables: tuple[Consumable, ...] = (),
        items: tuple[ItemQuantity, ...] = (),
        allow_flee: bool = True,
        flee_chance: int = 50,
    ) -> None:
        require_text(battle_id)
        require_integer(flee_chance)
        if flee_chance > 100:
            raise BattleRuleError("Probabilité de fuite invalide.")
        if len({fighter.id for fighter in combatants}) != len(combatants):
            raise BattleRuleError("Identité de combattant dupliquée.")
        for side in Side:
            if not any(fighter.side == side and fighter.hp for fighter in combatants):
                raise BattleRuleError("Chaque camp doit avoir un combattant conscient.")
        self._abilities = {ability.id: ability for ability in abilities}
        self._consumables = {entry.item.id: entry for entry in consumables}
        if len(self._abilities) != len(abilities) or len(self._consumables) != len(consumables):
            raise BattleRuleError("Définition de combat dupliquée.")
        if any(skill not in self._abilities for fighter in combatants for skill in fighter.skills):
            raise BattleRuleError("Compétence connue sans définition.")
        status_definitions = [
            status.definition for fighter in combatants for status in fighter.statuses
        ]
        for ability in (*abilities, *(entry.ability for entry in consumables)):
            status_definitions.extend(
                effect.status for effect in ability.effects if isinstance(effect, ApplyStatus)
            )
        known_statuses: dict[str, StatusDefinition] = {}
        for status in status_definitions:
            if status.id in known_statuses and known_statuses[status.id] != status:
                raise BattleRuleError("Définitions d'état contradictoires.")
            known_statuses[status.id] = status
        bag = Inventory(items)
        for entry in bag.stacks:
            if entry.item.id in self._consumables:
                if self._consumables[entry.item.id].item != entry.item:
                    raise BattleRuleError("Définition de consommable contradictoire.")
        self._id = battle_id
        self._fighters = {fighter.id: fighter for fighter in combatants}
        self._items = bag.stacks
        self._initial_items = bag.stacks
        self._allow_flee = allow_flee
        self._flee_chance = flee_chance
        self._state = BattleState.INITIALIZING
        self._outcome: Outcome | None = None
        self._active_id = ""
        self._turn_id = 0
        self._queue: tuple[str, ...] = ()
        self._journal: tuple[BattleEvent, ...] = ()
        self._settled = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> BattleState:
        return self._state

    @property
    def outcome(self) -> Outcome | None:
        return self._outcome

    @property
    def turn_id(self) -> int:
        return self._turn_id

    @property
    def combatants(self) -> tuple[Combatant, ...]:
        return tuple(self._fighters.values())

    @property
    def items(self) -> tuple[ItemQuantity, ...]:
        return self._items

    @property
    def initial_items(self) -> tuple[ItemQuantity, ...]:
        return self._initial_items

    @property
    def journal(self) -> tuple[BattleEvent, ...]:
        return self._journal

    @property
    def current(self) -> Combatant | None:
        return (
            self._fighters[self._active_id] if self._state == BattleState.AWAITING_ACTION else None
        )

    @property
    def settled(self) -> bool:
        return self._settled

    def mark_settled(self) -> None:
        if self._state != BattleState.FINISHED or self._settled:
            raise BattleRuleError("Combat non terminé ou déjà soldé.")
        self._settled = True

    def start(self) -> None:
        self._require_state(BattleState.INITIALIZING)
        self._state = BattleState.TURN_READY

    def prepare_turn(self) -> Combatant:
        self._require_state(BattleState.TURN_READY)
        queue = tuple(identity for identity in self._queue if self._fighters[identity].hp)
        if not queue:
            queue = tuple(
                fighter.id
                for fighter in sorted(
                    (fighter for fighter in self.combatants if fighter.hp),
                    key=lambda fighter: (-fighter.stats.speed, fighter.id),
                )
            )
        self._active_id, *remaining = queue
        self._queue = tuple(remaining)
        self._fighters[self._active_id] = replace(self._fighters[self._active_id], defending=False)
        self._turn_id += 1
        self._state = BattleState.AWAITING_ACTION
        return self._fighters[self._active_id]

    def _require_state(self, expected: BattleState) -> None:
        if self._state != expected:
            raise BattleRuleError(f"État attendu : {expected}, actuel : {self._state}")

    def _targets(self, actor: Combatant, rule: TargetRule) -> tuple[Combatant, ...]:
        return tuple(
            fighter
            for fighter in self.combatants
            if (
                (
                    fighter.id == actor.id
                    if rule.side == TargetSide.SELF
                    else (fighter.side == actor.side) == (rule.side == TargetSide.ALLY)
                )
                and (fighter.hp > 0) == (rule.life == TargetLife.ALIVE)
            )
        )

    def _validate(self, command: BattleCommand) -> Ability | None:
        self._require_state(BattleState.AWAITING_ACTION)
        actor = self._fighters[self._active_id]
        if command.actor_id != actor.id or command.turn_id != self._turn_id or not actor.hp:
            raise BattleRuleError("Acteur ou identifiant de tour invalide.")
        if actor.has_status(StatusKind.SLEEP) or actor.has_status(StatusKind.PARALYSIS):
            if command.action != Action.PASS:
                raise BattleRuleError("L'acteur ne peut que perdre son tour.")
        if command.action != Action.SKILL and command.ability_id:
            raise BattleRuleError("Compétence inattendue.")
        if command.action != Action.ITEM and command.item_id:
            raise BattleRuleError("Objet inattendu.")
        ability: Ability | None = None
        if command.action == Action.ATTACK:
            ability = BASIC_ATTACK
        elif command.action == Action.SKILL:
            if command.ability_id not in actor.skills:
                raise BattleRuleError("Compétence non apprise.")
            ability = self._abilities[command.ability_id]
            if ability.magical and actor.has_status(StatusKind.SILENCE):
                raise BattleRuleError("La magie est interdite par le silence.")
            if actor.mp < ability.cost:
                raise InsufficientMana(actor.id)
        elif command.action == Action.ITEM:
            if actor.side != Side.ALLIES or command.item_id not in self._consumables:
                raise BattleRuleError("Objet indisponible dans ce contexte.")
            if not any(stack.item.id == command.item_id for stack in self._items):
                raise MissingItem(command.item_id)
            ability = self._consumables[command.item_id].ability
        elif command.action == Action.FLEE:
            if not self._allow_flee or actor.side != Side.ALLIES:
                raise BattleRuleError("Fuite interdite.")
        if ability is None:
            if command.targets:
                raise InvalidTarget("Cette action ne cible personne.")
        else:
            candidates = {fighter.id for fighter in self._targets(actor, ability.targeting)}
            targets = set(command.targets)
            if not targets or len(targets) != len(command.targets) or not targets <= candidates:
                raise InvalidTarget("Cibles absentes, dupliquées ou incompatibles.")
            if ability.targeting.multiple:
                if targets != candidates:
                    raise InvalidTarget("Toutes les cibles valides doivent être sélectionnées.")
            elif len(targets) != 1:
                raise InvalidTarget("Une seule cible attendue.")
        return ability

    def candidate_commands(self) -> tuple[BattleCommand, ...]:
        """Choix structurés, y compris indisponibles, sans reproduire les règles en UI."""
        self._require_state(BattleState.AWAITING_ACTION)
        actor = self._fighters[self._active_id]
        commands: list[BattleCommand] = []
        options = [(Action.ATTACK, BASIC_ATTACK, "", "")]
        options.extend((Action.SKILL, self._abilities[key], key, "") for key in actor.skills)
        options.extend(
            (Action.ITEM, entry.ability, "", key) for key, entry in self._consumables.items()
        )
        for action, ability, skill_id, item_id in options:
            targets = tuple(fighter.id for fighter in self._targets(actor, ability.targeting))
            selections = (
                (targets,) if ability.targeting.multiple else tuple((key,) for key in targets)
            )
            for selection in selections or ((),):
                command = BattleCommand(
                    actor.id, self._turn_id, action, selection, skill_id, item_id
                )
                commands.append(command)
        for action in (Action.DEFEND, Action.PASS, Action.FLEE):
            command = BattleCommand(actor.id, self._turn_id, action)
            commands.append(command)
        return tuple(commands)

    def command_error(self, command: BattleCommand) -> str | None:
        """Validation publique en lecture seule ; execute valide à nouveau avant mutation."""
        try:
            self._validate(command)
        except InsufficientMana:
            return "PM insuffisants."
        except MissingItem:
            return "Objet épuisé."
        except BattleRuleError as error:
            return str(error)
        return None

    def legal_commands(self) -> tuple[BattleCommand, ...]:
        return tuple(
            command for command in self.candidate_commands() if self.command_error(command) is None
        )

    def execute(self, command: BattleCommand, random: RandomSource) -> BattleActionResult:
        ability = self._validate(command)
        candidate = self._fighters.copy()
        bag = Inventory(self._items)
        actor = candidate[self._active_id]
        events: list[BattleEvent] = []
        fled = False
        if ability is not None:
            actor = replace(actor, mp=actor.mp - ability.cost)
            candidate[actor.id] = actor
            if ability.cost:
                events.append(BattleEvent(EventKind.MANA_SPENT, actor.id, amount=ability.cost))
            if command.action == Action.ITEM:
                bag.remove(self._consumables[command.item_id].item)
            for target_id in command.targets:
                for effect in ability.effects:
                    target, produced = effect.apply(
                        candidate[actor.id], candidate[target_id], random
                    )
                    candidate[target_id] = target
                    events.extend(produced)
        elif command.action == Action.DEFEND:
            candidate[actor.id] = replace(actor, defending=True)
            events.append(BattleEvent(EventKind.DEFENDED, actor.id))
        elif command.action == Action.PASS:
            events.append(BattleEvent(EventKind.PASSED, actor.id))
        elif command.action == Action.FLEE:
            fled = random.randint(1, 100) <= self._flee_chance
            if not fled:
                events.append(BattleEvent(EventKind.FLEE_FAILED, actor.id))
        if not fled:
            candidate[actor.id], tick_events = self._end_turn(candidate[actor.id])
            events.extend(tick_events)
        for identity, fighter in tuple(candidate.items()):
            if not fighter.hp:
                candidate[identity] = replace(with_statuses(fighter, ()), defending=False)
            if self._fighters[identity].hp and not fighter.hp:
                kind = (
                    EventKind.ENEMY_DEFEATED
                    if fighter.side == Side.ENEMIES
                    else EventKind.KNOCKED_OUT
                )
                events.append(BattleEvent(kind, actor.id, identity))
        outcome = self._result(candidate, fled)
        if outcome is not None:
            kind = {
                Outcome.VICTORY: EventKind.BATTLE_WON,
                Outcome.DEFEAT: EventKind.BATTLE_LOST,
                Outcome.FLED: EventKind.FLED,
            }[outcome]
            events.append(BattleEvent(kind, actor.id))
        final = BattleState.FINISHED if outcome else BattleState.TURN_READY
        # Résoudre avant publication : une exception laisse le combat intact.
        result = BattleActionResult(
            command,
            tuple(events),
            (BattleState.RESOLVING, BattleState.TURN_END, final),
            tuple(candidate.values()),
            outcome,
        )
        self._fighters, self._items = candidate, bag.stacks
        self._state, self._outcome = final, outcome
        self._journal += result.events
        return result

    @staticmethod
    def _end_turn(actor: Combatant) -> tuple[Combatant, tuple[BattleEvent, ...]]:
        statuses: list[ActiveStatus] = []
        events: list[BattleEvent] = []
        hp = actor.hp
        for status in actor.statuses:
            if status.definition.kind in {StatusKind.POISON, StatusKind.BURN}:
                damage = min(hp, status.definition.potency)
                hp -= damage
                events.append(
                    BattleEvent(
                        EventKind.DAMAGE, actor.id, actor.id, damage, status_id=status.definition.id
                    )
                )
            if status.remaining > 1:
                statuses.append(replace(status, remaining=status.remaining - 1))
            else:
                events.append(
                    BattleEvent(
                        EventKind.STATUS_EXPIRED, actor.id, actor.id, status_id=status.definition.id
                    )
                )
        return with_statuses(replace(actor, hp=hp), tuple(statuses)), tuple(events)

    @staticmethod
    def _result(fighters: dict[str, Combatant], fled: bool) -> Outcome | None:
        if fled:
            return Outcome.FLED
        if not any(fighter.hp for fighter in fighters.values() if fighter.side == Side.ALLIES):
            return Outcome.DEFEAT
        if not any(fighter.hp for fighter in fighters.values() if fighter.side == Side.ENEMIES):
            return Outcome.VICTORY
        return None
