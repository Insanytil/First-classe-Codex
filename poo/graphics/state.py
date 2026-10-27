"""État du jeu graphique ; aucun appel à input() ni console."""
from dataclasses import dataclass

from poo.characters import Hero
from poo.characters.boss import Gatekeeper
from poo.game.encounters import flan, wolf
from poo.game.world import Chapter, buy_potion, camp_rest
from poo.graphics.character import CharacterDraft, DEFAULT_HAIR
from poo.graphics.world import REGIONS, TILE, move, nearby
from poo.game.battle import Battle
from poo.game.prologue import PROLOGUE_PAGES
from poo.characters.jobs import WEAPONS


@dataclass
class Dialogue:
    speaker: str
    text: str
    choices: tuple[tuple[str, str], ...] = (('Fermer', 'close'),)
    portrait: str | None = None


class Session:
    def __init__(self):
        self.hero = Hero('Voyageur', strength=20, magic=20, defense=10, resistance=10)
        self.hair_color = DEFAULT_HAIR
        self.chapter = Chapter()
        self.place = 'camp'
        self.x, self.y = REGIONS['camp'].spawn
        self.facing = 'down'
        self.walking = False
        self.time = 0.0
        self.mode = 'title'
        self.dialogue: Dialogue | None = None
        self.battle: Battle | None = None
        self.notice = 'Mira vous attend au camp. Approchez-vous et appuyez sur E.'
        self.destination = ''
        self.previous_mode = 'world'
        self.cinematic = 0
        self.cinematic_time = 0.0
        self.hits = []
        self.inventory_shop = False

    def open_inventory(self, shop=False):
        if self.mode != 'world' or (self.dialogue and not shop):
            return False
        self.dialogue = None
        self.inventory_shop = shop
        self.mode = 'inventory'
        return True

    def close_inventory(self):
        if self.mode == 'inventory':
            self.mode = 'world'
            self.inventory_shop = False

    def equip_weapon(self, weapon_id):
        if self.mode != 'inventory':
            return False
        result = self.hero.equip(weapon_id)
        self.notice = f'{self.hero.weapon.name} équipée.' if result else 'Cette arme ne peut pas être équipée.'
        return result

    def buy_weapon(self, weapon_id):
        if self.mode != 'inventory' or not self.inventory_shop:
            return False
        result = self.hero.buy_weapon(weapon_id)
        self.notice = f'{WEAPONS[weapon_id].name} rejoint votre inventaire.' if result else 'Achat impossible : classe, possession ou gils insuffisants.'
        return result

    def start(self, draft: CharacterDraft, prologue: bool = True):
        hero = draft.build()
        hair_color = draft.hair_color
        self.__init__()
        self.hero = hero
        self.hair_color = hair_color
        self.mode = 'prologue' if prologue else 'world'

    def advance_prologue(self) -> bool:
        if self.mode != 'prologue':
            return False
        page = PROLOGUE_PAGES[self.cinematic]
        if self.cinematic_time < page.minimum_duration:
            return False
        self.cinematic += 1
        self.cinematic_time = 0.0
        if self.cinematic >= len(PROLOGUE_PAGES):
            self.mode = 'world'
        return True

    def travel(self, destination: str):
        old = self.place
        self.place = destination
        region = REGIONS[destination]
        entry = next((exit for exit in region.exits if exit.destination == old), None)
        if entry:
            self.x, self.y = (entry.x + .5) * TILE, (entry.y + .5) * TILE
            if entry.direction == 'west':
                self.x += TILE
            elif entry.direction == 'east':
                self.x -= TILE
            elif entry.direction == 'north':
                self.y += TILE
            else:
                self.y -= TILE
        else:
            self.x, self.y = region.spawn
        self.notice = region.subtitle

    def update(self, dt: float, direction: tuple[float, float] = (0, 0)):
        dt = max(0, min(dt, .05))
        self.time += dt
        self.walking = False
        if self.mode == 'prologue':
            self.cinematic_time += dt
        self.hits = [hit for hit in self.hits if self.time - hit['time'] < 1]
        if self.mode == 'battle':
            before = [self.hero.hp, *(monster.hp for monster in self.battle.monsters)]
            self.battle.update(dt)
            after = [self.hero.hp, *(monster.hp for monster in self.battle.monsters)]
            for index, (old, new) in enumerate(zip(before, after)):
                if old != new:
                    self.hits.append({'target': index - 1, 'amount': old - new, 'time': self.time})
            return
        if self.mode != 'world' or self.dialogue:
            return
        dx, dy = direction
        length = (dx * dx + dy * dy) ** .5
        if length:
            dx, dy = dx / length, dy / length
            self.facing = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')
            old = self.x, self.y
            self.x, self.y = move(REGIONS[self.place], self.x, self.y, dx * 155 * dt, dy * 155 * dt)
            self.walking = old != (self.x, self.y)

    def interact(self):
        if self.mode != 'world' or self.dialogue:
            return
        region = REGIONS[self.place]
        # Les sorties utilisent E, pour éviter les changements de carte accidentels.
        exit = next((exit for exit in region.exits if abs((exit.x + .5) * TILE - self.x) < 85 and abs((exit.y + .5) * TILE - self.y) < 65), None)
        if exit:
            self.travel(exit.destination)
            return
        obj = nearby(region, self.x, self.y)
        if obj is None:
            self.notice = 'Approchez-vous d’un personnage, d’un feu ou d’un passage.'
            return
        self.interact_object(obj.kind)

    def interact_object(self, kind: str):
        if kind == 'fire':
            camp_rest(self.hero)
            self.notice = 'Le feu crépite. Tous vos PV et PM sont restaurés.'
            self.dialogue = Dialogue('Au coin du feu', self.notice)
        elif kind == 'mira':
            self.dialogue = Dialogue('Mira · Éclaireuse', 'La route des caravanes est attaquée. Libérez le passage, puis cherchez le sceau dans les ruines, au nord du pont. Revenez vous reposer entre les combats.' if not self.chapter.gate_unlocked else 'Le sceau est complet. À l’est, la Sentinelle charge son arme avant de frapper. Mettez-vous en garde quand elle brille !', portrait='mira')
        elif kind == 'merchant':
            self.dialogue = Dialogue('Oren · Marchand', f'Une potion pour la route ? 25 gils la fiole. Mes armes sont aussi à vendre. Vous avez {self.hero.gil} gils.', (('Potion · 25 gils', 'buy'), ('Voir les armes', 'armory'), ('Plus tard', 'close')), portrait='merchant')
        elif kind in ('wolf', 'traveler'):
            if 'road' in self.chapter.completed:
                self.dialogue = Dialogue('Le voyageur', 'Grâce à vous, les caravanes peuvent reprendre la route. Merci !', portrait='traveler')
            else:
                self.dialogue = Dialogue('Une caravane en danger', 'Un loup rôde autour du chariot. Le marchand est pris au piège.', (('Intervenir', 'road'), ('Revenir plus tard', 'close')), portrait='traveler')
        elif kind in ('altar', 'flan'):
            if 'ruins' in self.chapter.completed:
                self.dialogue = Dialogue('Le sanctuaire', 'Le bassin est vide. Le sceau repose désormais dans votre sac.')
            else:
                self.dialogue = Dialogue('Le sceau du levant', 'Deux formes se détachent du bassin. Pour récupérer le sceau, il faudra les affronter.', (('Prendre le sceau', 'ruins'), ('Reculer', 'close')))
        elif kind == 'boss':
            if self.chapter.gate_unlocked:
                self.dialogue = Dialogue('La Sentinelle', 'PORTEUR DU SCEAU. PROUVE TA FORCE. Son arme accumule de l’énergie avant chaque frappe lourde.', (('Affronter la Sentinelle', 'gate'), ('Se préparer', 'close')), portrait='boss')
            else:
                self.dialogue = Dialogue('Une porte scellée', 'Libérez la caravane et retrouvez le sceau des ruines pour ouvrir le passage.', portrait='boss')
        elif kind == 'sign':
            self.dialogue = Dialogue('La stèle du pont', 'NORD · Ruines du levant. EST · Porte de Dalmasca. OUEST · Camp des voyageurs.')

    def choose_dialogue(self, action: str):
        if not self.dialogue or action not in {key for _, key in self.dialogue.choices}:
            return
        self.dialogue = None
        if action == 'armory':
            self.open_inventory(shop=True)
        elif action == 'buy':
            self.notice = 'Une potion rejoint votre sac.' if buy_potion(self.hero) else 'Votre bourse est trop légère. Il vous faut 25 gils.'
            self.dialogue = Dialogue('Oren · Marchand', self.notice, portrait='merchant')
        elif action in ('road', 'ruins', 'gate'):
            self.destination = action
            monsters = {'road': lambda: [wolf()], 'ruins': lambda: [flan(), flan()], 'gate': lambda: [Gatekeeper()]}[action]()
            self.battle = Battle(self.hero, monsters)
            self.mode = 'battle'
        elif action == 'rescue':
            self.chapter.rescued = True
            self.hero.add_potion(2)
            self.notice = 'Le marchand vous remercie : +2 potions.'
        elif action == 'tracks':
            self.hero.gain_gil(40)
            self.notice = 'Vous trouvez 40 gils dans un ancien poste de garde.'

    def finish_battle(self):
        if not self.battle or self.battle.result is None:
            return
        if not self.battle.result:
            self.mode = 'dead'
            return
        self.chapter.completed.add(self.destination)
        self.hero.defending = False
        self.hero.shield = 0
        self.battle = None
        self.mode = 'world'
        if self.destination == 'road':
            self.dialogue = Dialogue('Le voyageur est sain et sauf', 'Le loup ne reviendra plus. Le chariot s’est renversé pendant l’attaque.', (('Aider le marchand · +2 potions', 'rescue'), ('Inspecter les traces · +40 gils', 'tracks')), portrait='traveler')
        elif self.destination == 'ruins':
            self.hero.add_potion(1)
            self.notice = 'Sceau du levant récupéré. Vous trouvez aussi une potion.'
            self.dialogue = Dialogue('Le sceau du levant', self.notice)
        else:
            self.mode = 'ending'

    def pause(self):
        if self.mode == 'pause':
            self.mode = self.previous_mode
        elif self.mode not in ('title', 'create', 'ending', 'dead'):
            self.previous_mode, self.mode = self.mode, 'pause'
