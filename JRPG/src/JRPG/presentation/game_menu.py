"""Menus de groupe et de commerce ; les mutations restent des opérations métier."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from JRPG.application.consumables import use_consumable
from JRPG.application.exploration import ExplorationSession
from JRPG.application.saves import SaveService
from JRPG.domain.characters import Character
from JRPG.domain.errors import DomainError
from JRPG.domain.items import EquipmentSlot, ItemCategory
from JRPG.domain.quests import QuestStatus


class MenuPage(StrEnum):
    MAIN = "main"
    INVENTORY = "inventory"
    ITEM_TARGET = "item_target"
    EQUIPMENT_HERO = "equipment_hero"
    EQUIPMENT_SLOT = "equipment_slot"
    EQUIPMENT_ITEM = "equipment_item"
    CHARACTERS = "characters"
    PARTY = "party"
    QUESTS = "quests"
    SHOP = "shop"
    BUY = "buy"
    SELL = "sell"
    SAVE = "save"
    LOAD = "load"


QUEST_LABELS = {
    QuestStatus.LOCKED: "Verrouillée",
    QuestStatus.AVAILABLE: "Disponible",
    QuestStatus.ACTIVE: "En cours",
    QuestStatus.COMPLETED: "À remettre",
    QuestStatus.REWARDED: "Terminée",
}
CATEGORY_LABELS = {
    ItemCategory.CONSUMABLE: "Consommable",
    ItemCategory.WEAPON: "Arme",
    ItemCategory.ARMOR: "Armure",
    ItemCategory.ACCESSORY: "Accessoire",
    ItemCategory.QUEST: "Objet de quête",
    ItemCategory.MATERIAL: "Matériau",
    ItemCategory.SPECIAL: "Objet spécial",
}
SLOT_LABELS = {
    EquipmentSlot.WEAPON: "Arme",
    EquipmentSlot.OFF_HAND: "Main secondaire",
    EquipmentSlot.HEAD: "Tête",
    EquipmentSlot.BODY: "Corps",
    EquipmentSlot.ACCESSORY_1: "Accessoire 1",
    EquipmentSlot.ACCESSORY_2: "Accessoire 2",
}


@dataclass(frozen=True, slots=True)
class MenuEntry:
    id: str
    label: str
    details: tuple[str, ...] = ()
    reason: str | None = None


class GameMenu:
    def __init__(
        self,
        session: ExplorationSession,
        saves: SaveService | None,
        on_load: Callable[[ExplorationSession], None],
    ) -> None:
        self.session, self.saves, self._on_load = session, saves, on_load
        self.opened = False
        self.page = MenuPage.MAIN
        self.selected = 0
        self.message = ""
        self._parents: list[MenuPage] = []
        self._hero = ""
        self._item = ""
        self._slot = EquipmentSlot.WEAPON
        self.shop_id = ""

    def open(self, page: MenuPage = MenuPage.MAIN) -> None:
        if self.session.active_encounter is not None:
            raise DomainError("Le menu est fermé pendant le combat.")
        self.opened = True
        self.page, self.selected = page, 0
        self.message = ""
        self._parents = [] if page == MenuPage.MAIN else [MenuPage.MAIN]

    def open_shop(self, identity: str) -> None:
        self.shop_id = identity
        self.open(MenuPage.SHOP)

    def close(self) -> None:
        self.opened = False

    def _enter(self, page: MenuPage) -> None:
        self._parents.append(self.page)
        self.page, self.selected = page, 0
        self.message = ""

    def back(self) -> None:
        if self._parents:
            self.page, self.selected = self._parents.pop(), 0
            self.message = ""
        else:
            self.close()

    def move(self, amount: int) -> None:
        if self.entries:
            self.selected = (self.selected + amount) % len(self.entries)
            self.message = ""

    def _member(self, identity: str) -> Character:
        for member in self.session.party.members:
            if member.id == identity:
                return member
        raise DomainError("Personnage inconnu.")

    @property
    def title(self) -> str:
        return {
            MenuPage.MAIN: "Groupe",
            MenuPage.INVENTORY: "Inventaire",
            MenuPage.ITEM_TARGET: "Utiliser sur…",
            MenuPage.EQUIPMENT_HERO: "Équipements",
            MenuPage.EQUIPMENT_SLOT: "Emplacements",
            MenuPage.EQUIPMENT_ITEM: "Équiper",
            MenuPage.CHARACTERS: "Personnages",
            MenuPage.PARTY: "Ordre du groupe",
            MenuPage.QUESTS: "Journal des quêtes",
            MenuPage.SHOP: "Boutique",
            MenuPage.BUY: "Acheter",
            MenuPage.SELL: "Vendre",
            MenuPage.SAVE: "Sauvegarder",
            MenuPage.LOAD: "Charger",
        }[self.page]

    @property
    def entries(self) -> tuple[MenuEntry, ...]:
        story = self.session.story
        if self.page == MenuPage.MAIN:
            return tuple(
                MenuEntry(page.value, label)
                for page, label in (
                    (MenuPage.INVENTORY, "Inventaire"),
                    (MenuPage.EQUIPMENT_HERO, "Équipements"),
                    (MenuPage.CHARACTERS, "Personnages"),
                    (MenuPage.PARTY, "Équipe / leader"),
                    (MenuPage.QUESTS, "Quêtes"),
                    (MenuPage.SAVE, "Sauvegarder"),
                    (MenuPage.LOAD, "Charger"),
                )
            )
        if self.page in {
            MenuPage.CHARACTERS,
            MenuPage.EQUIPMENT_HERO,
            MenuPage.PARTY,
            MenuPage.ITEM_TARGET,
        }:
            rows = []
            for index, member in enumerate(self.session.party.members):
                stats = member.stats
                rows.append(
                    MenuEntry(
                        member.id,
                        f"{index + 1}. {member.definition.name} · niv. {member.level}",
                        (
                            member.definition.character_class.name,
                            f"XP : {member.experience}",
                            f"PV {member.hp}/{stats.hp}   PM {member.mp}/{stats.mp}",
                            f"Force {stats.strength}   Défense {stats.defense}",
                            f"Magie {stats.magic}   Résistance {stats.resistance}",
                            f"Vitesse {stats.speed}   Précision {stats.accuracy}%",
                            f"Esquive {stats.evasion}%   Critique {stats.critical}%",
                            "Compétences : "
                            + ", ".join(
                                ability.name
                                for ability in self.session.encounter_factory.abilities
                                if ability.id in member.skills
                            ),
                            "Entrée : devenir leader" if self.page == MenuPage.PARTY else "",
                        ),
                    )
                )
            return tuple(rows)
        if self.page == MenuPage.INVENTORY:
            return tuple(
                MenuEntry(
                    stack.item.id,
                    f"{stack.item.name} ×{stack.quantity}",
                    (
                        CATEGORY_LABELS[stack.item.category],
                        "Entrée : utiliser"
                        if stack.item.category == ItemCategory.CONSUMABLE
                        else "Voir le menu Équipements.",
                    ),
                    None
                    if stack.item.category == ItemCategory.CONSUMABLE
                    else "Cet objet s'équipe via Équipements.",
                )
                for stack in sorted(
                    self.session.inventory.stacks, key=lambda entry: entry.item.name
                )
            )
        if self.page == MenuPage.EQUIPMENT_SLOT:
            equipment = dict(self._member(self._hero).equipment)
            return tuple(
                MenuEntry(
                    slot.value,
                    f"{SLOT_LABELS[slot]} : "
                    f"{equipment[slot].name if slot in equipment else 'vide'}",
                )
                for slot in EquipmentSlot
            )
        if self.page == MenuPage.EQUIPMENT_ITEM:
            member = self._member(self._hero)
            entries = [
                MenuEntry(
                    "unequip",
                    "Retirer l'équipement",
                    reason=None if self._slot in dict(member.equipment) else "Emplacement vide.",
                )
            ]
            for stack in self.session.inventory.stacks:
                item = stack.item
                if self._slot not in item.slots:
                    continue
                reason = member.equipment_error(item, self._slot)
                details: tuple[str, ...] = ("Classe incompatible.",)
                if reason is None:
                    before, after = member.stats, member.stats_with_equipment(self._slot, item)
                    details = tuple(
                        f"{name} : {getattr(before, key)} -> {getattr(after, key)}"
                        for name, key in (
                            ("PV max", "hp"),
                            ("PM max", "mp"),
                            ("Force", "strength"),
                            ("Défense", "defense"),
                            ("Magie", "magic"),
                            ("Résistance", "resistance"),
                            ("Vitesse", "speed"),
                        )
                    )
                entries.append(
                    MenuEntry(item.id, f"{item.name} ×{stack.quantity}", details, reason)
                )
            return tuple(entries)
        if self.page == MenuPage.QUESTS and story is not None:
            return tuple(
                MenuEntry(
                    quest.id,
                    f"{quest.name} · {QUEST_LABELS[story.quests.status(quest.id)]}",
                    (
                        quest.description,
                        *(
                            f"{objective.description} : "
                            f"{story.quests.progress(objective)}/{objective.required}"
                            for objective in quest.objectives
                        ),
                    ),
                )
                for quest in story.quests.definitions
            )
        if self.page == MenuPage.SHOP:
            return (
                MenuEntry(MenuPage.BUY.value, "Acheter"),
                MenuEntry(MenuPage.SELL.value, "Vendre"),
            )
        if self.page in {MenuPage.BUY, MenuPage.SELL} and story is not None:
            shop = story.shops[self.shop_id]
            stock = dict(shop.stock)
            entries = []
            for offer in shop.offers:
                owned = self.session.inventory.quantity(offer.item.id)
                if self.page == MenuPage.SELL and not owned:
                    continue
                price = offer.buy_price if self.page == MenuPage.BUY else offer.sell_price
                reason = None
                if self.page == MenuPage.BUY:
                    reason = (
                        "Stock épuisé."
                        if not stock[offer.item.id]
                        else "Fonds insuffisants."
                        if self.session.wallet.gold < price
                        else None
                    )
                entries.append(
                    MenuEntry(
                        offer.item.id,
                        f"{offer.item.name} · {price} pièces",
                        (
                            f"Stock : {stock[offer.item.id]}",
                            f"Dans le sac : {owned}",
                            "Entrée : acheter une unité"
                            if self.page == MenuPage.BUY
                            else "Entrée : vendre une unité",
                        ),
                        reason,
                    )
                )
            return tuple(entries)
        if self.page in {MenuPage.SAVE, MenuPage.LOAD}:
            return tuple(
                MenuEntry(
                    str(slot),
                    f"Emplacement {slot} · "
                    f"{'occupé' if self.saves and self.saves.exists(slot) else 'vide'}",
                    (
                        "Entrée : enregistrer ici"
                        if self.page == MenuPage.SAVE
                        else "Entrée : charger cette partie",
                    ),
                    "Sauvegarde indisponible."
                    if self.saves is None
                    else "Emplacement vide."
                    if self.page == MenuPage.LOAD and not self.saves.exists(slot)
                    else None,
                )
                for slot in range(1, 4)
            )
        return ()

    def choose(self, index: int | None = None) -> None:
        if not self.opened:
            return
        if index is not None:
            if not 0 <= index < len(self.entries):
                return
            self.selected = index
        entries = self.entries
        if not entries:
            self.message = "Aucun choix disponible."
            return
        self.selected = min(self.selected, len(entries) - 1)
        entry = entries[self.selected]
        if entry.reason:
            self.message = entry.reason
            return
        try:
            if self.session.active_encounter is not None:
                raise DomainError("Menu indisponible en combat.")
            self._choose(entry)
        except DomainError as error:
            self.message = str(error)
        if self.entries:
            self.selected = min(self.selected, len(self.entries) - 1)

    def _choose(self, entry: MenuEntry) -> None:
        story = self.session.story
        if self.page == MenuPage.MAIN or self.page == MenuPage.SHOP:
            self._enter(MenuPage(entry.id))
        elif self.page == MenuPage.INVENTORY:
            self._item = entry.id
            self._enter(MenuPage.ITEM_TARGET)
        elif self.page == MenuPage.ITEM_TARGET:
            use_consumable(self.session, self._item, entry.id)
            self.back()
            self.message = "Objet utilisé."
        elif self.page == MenuPage.EQUIPMENT_HERO:
            self._hero = entry.id
            self._enter(MenuPage.EQUIPMENT_SLOT)
        elif self.page == MenuPage.EQUIPMENT_SLOT:
            self._slot = EquipmentSlot(entry.id)
            self._enter(MenuPage.EQUIPMENT_ITEM)
        elif self.page == MenuPage.EQUIPMENT_ITEM and story is not None:
            member = self._member(self._hero)
            if entry.id == "unequip":
                member.unequip(self.session.inventory, self._slot)
            else:
                member.equip(self.session.inventory, story.content.item(entry.id), self._slot)
            self.back()
            self.message = "Équipement mis à jour."
        elif self.page == MenuPage.PARTY:
            self.session.party.move(entry.id, 0)
            self.selected = 0
            self.message = "Leader modifié."
        elif self.page == MenuPage.QUESTS:
            self.message = "Parlez au donneur de quête pour accepter ou recevoir sa récompense."
        elif self.page in {MenuPage.BUY, MenuPage.SELL} and story is not None:
            shop = story.shops[self.shop_id]
            if self.page == MenuPage.BUY:
                shop.buy(entry.id, 1, self.session.inventory, self.session.wallet)
            else:
                shop.sell(entry.id, 1, self.session.inventory, self.session.wallet)
            self.message = "Transaction effectuée."
        elif self.page == MenuPage.SAVE and self.saves is not None:
            self.saves.save(int(entry.id), self.session)
            self.message = f"Partie sauvegardée dans l'emplacement {entry.id}."
        elif self.page == MenuPage.LOAD and self.saves is not None:
            candidate = self.saves.load(int(entry.id))
            self._on_load(candidate)
