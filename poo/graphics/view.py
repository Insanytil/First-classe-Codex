"""Présentation graphique à résolution logique fixe, redimensionnable."""
import math
from functools import lru_cache

import pygame as pg

from poo.graphics import art
from poo.graphics.animation import attack_pose, frame_at, action_frame_at, clamp, ease
from poo.game.prologue import PROLOGUE_PAGES, DUEL_DURATION
from poo.characters.jobs import JOBS, SKILLS, WEAPONS
from poo.graphics.character import BASE_STAT, HAIR_COLORS, POINT_BUDGET, STAT_LABELS
from poo.graphics.world import REGIONS, TILE, nearby

SIZE = (1280, 800)
INK = (16, 27, 34)
PANEL = (24, 39, 46)
LINE = (52, 69, 72)
PAPER = (235, 226, 202)
MUTED = (151, 169, 164)
GOLD = (216, 177, 105)
TEAL = (108, 190, 170)
MAP_RECT = pg.Rect(24, 112, 912, 576)


@lru_cache(maxsize=32)
def font(size=20, serif=False):
    return pg.font.SysFont('georgia,dejavuserif' if serif else 'segoeui,dejavusans', size)


def text(surface, value, position, size=20, color=PAPER, serif=False):
    image = font(size, serif).render(str(value), True, color)
    surface.blit(image, position)
    return image.get_rect(topleft=position)


def wrap(surface, value, rect, size=19, color=PAPER, spacing=7, max_lines=None):
    y = rect.y
    lines = []
    for paragraph in value.split('\n'):
        line = ''
        for word in paragraph.split():
            test = f'{line} {word}'.strip()
            if font(size).size(test)[0] > rect.width and line:
                lines.append(line)
                line = word
            else:
                line = test
        lines.append(line)
    for line in lines[:max_lines] if max_lines else lines:
        if y + font(size).get_height() > rect.bottom:
            break
        text(surface, line, (rect.x, y), size, color)
        y += font(size).get_height() + spacing
    return y


def panel(surface, rect, color=PANEL, border=LINE, radius=12):
    pg.draw.rect(surface, (9, 17, 23), pg.Rect(rect).move(0, 4), border_radius=radius)
    pg.draw.rect(surface, color, rect, border_radius=radius)
    pg.draw.rect(surface, border, rect, 1, border_radius=radius)


def bar(surface, rect, value, maximum, color):
    pg.draw.rect(surface, (11, 22, 28), rect, border_radius=4)
    ratio = max(0, min(1, value / maximum)) if maximum else 0
    if ratio:
        fill = pg.Rect(rect)
        fill.width = max(1, round(fill.width * ratio))
        pg.draw.rect(surface, color, fill, border_radius=4)


@lru_cache(maxsize=48)
def shadow_texture(width, height):
    image = pg.Surface((width, height), pg.SRCALPHA)
    for inset in range(6):
        dx, dy = inset * width * .035, inset * height * .045
        pg.draw.ellipse(image, (8, 16, 18, 9 + inset * 7),
                        (dx, dy, width - 2 * dx, height - 2 * dy))
    return image


def shadow(surface, x, y, width, height):
    surface.blit(shadow_texture(width, height), (round(x), round(y)))


class View:
    def __init__(self):
        self.surface = pg.Surface(SIZE)
        self.buttons = []
        self.mouse = (-1, -1)

    def button(self, label, rect, action, enabled=True, primary=False):
        rect = pg.Rect(rect)
        hover = rect.collidepoint(self.mouse) and enabled
        fill = (64, 83, 76) if hover else (48, 65, 62) if primary else (30, 46, 52)
        edge = GOLD if primary or hover else LINE
        pg.draw.rect(self.surface, fill if enabled else (24, 34, 39), rect, border_radius=7)
        pg.draw.rect(self.surface, edge if enabled else (43, 53, 57), rect, 1, border_radius=7)
        label_size = 18
        while label_size > 11 and font(label_size).size(label)[0] > rect.width - 16:
            label_size -= 1
        image = font(label_size).render(label, True, PAPER if enabled else (93, 111, 114))
        self.surface.blit(image, image.get_rect(center=rect.center))
        if enabled:
            self.buttons.append((rect, action))

    def click(self, position):
        return next((action for rect, action in reversed(self.buttons) if rect.collidepoint(position)), None)

    def background(self, place, opened=False):
        name = f'map_{place}'
        if place == 'gate' and opened:
            name += '_open'
        return art.backdrop(name, MAP_RECT.size)

    def prop_image(self, obj, session):
        if obj.kind in ('mira', 'merchant', 'traveler', 'wolf', 'flan', 'boss'):
            if (obj.kind == 'wolf' and 'road' in session.chapter.completed) or (obj.kind == 'flan' and 'ruins' in session.chapter.completed) or (obj.kind == 'boss' and 'gate' in session.chapter.completed):
                return None
            return art.actor(obj.kind, int(session.time * 3) % 2)
        # Ces éléments font partie des peintures, leurs collisions restent dans world.py.
        if obj.kind in ('house', 'tent', 'wagon', 'gate', 'tree', 'pillar', 'stone'):
            return None
        if obj.kind == 'altar' and 'ruins' in session.chapter.completed:
            return None
        return art.prop(obj.kind, int(session.time * 8) % 2 if obj.kind == 'fire' else 0, 'gate' in session.chapter.completed)

    def draw_world(self, session):
        surface = self.surface
        region = REGIONS[session.place]
        panel(surface, MAP_RECT.inflate(4, 4), border=(78, 93, 83), radius=4)
        surface.blit(self.background(session.place, 'gate' in session.chapter.completed), MAP_RECT)
        old_clip = surface.get_clip()
        surface.set_clip(MAP_RECT)
        # Reflets indépendants de la lecture clavier.
        if session.place == 'bridge':
            for i in range(18):
                x = 7 * TILE + (i * 47 + int(session.time * 8)) % (4 * TILE)
                y = (i * 73 + 12) % MAP_RECT.height
                if region.terrain[y // TILE][x // TILE] == 'w':
                    pg.draw.line(surface, (87, 146, 147), (MAP_RECT.x + x, MAP_RECT.y + y), (MAP_RECT.x + x + 12, MAP_RECT.y + y), 2)
        entities = []
        for obj in region.objects:
            image = self.prop_image(obj, session)
            if image is None:
                continue
            foot = (obj.y + obj.height) * TILE
            x = MAP_RECT.x + obj.x * TILE + obj.width * TILE / 2 - image.get_width() / 2
            y = MAP_RECT.y + foot - image.get_height()
            entities.append((foot, image, x, y, obj))
        frame = int(session.time * 9) % 4 if session.walking else 0
        image = art.player(session.hero.class_id, session.hero.weapon_id, frame, session.facing, session.hair_color)
        entities.append((session.y, image, MAP_RECT.x + session.x - image.get_width() / 2, MAP_RECT.y + session.y - image.get_height() + 6, None))
        for foot, image, x, y, obj in sorted(entities, key=lambda item: item[0]):
            shadow(surface, x + image.get_width() * .15, MAP_RECT.y + foot - 7, max(1, round(image.get_width() * .7)), 12)
            if obj and obj.kind == 'fire':
                glow = pg.Surface((128, 96), pg.SRCALPHA)
                intensity = 35 + int(math.sin(session.time * 7) * 8)
                pg.draw.ellipse(glow, (244, 164, 65, intensity), (0, 0, 128, 96))
                surface.blit(glow, (x + image.get_width() / 2 - 64, MAP_RECT.y + foot - 65))
            surface.blit(image, (round(x), round(y)))
            if obj and obj.label:
                done = (obj.kind in ('wolf', 'traveler') and 'road' in session.chapter.completed) or (obj.kind == 'altar' and 'ruins' in session.chapter.completed)
                if not done:
                    cx = round(x + image.get_width() / 2)
                    cy = round(y - 13 + math.sin(session.time * 2) * 3)
                    pg.draw.polygon(surface, GOLD, [(cx, cy - 5), (cx + 4, cy), (cx, cy + 5), (cx - 4, cy)])
        for exit in region.exits:
            x, y = MAP_RECT.x + (exit.x + .5) * TILE, MAP_RECT.y + (exit.y + .5) * TILE
            pg.draw.circle(surface, (224, 198, 133), (int(x), int(y)), 14, 1)
            label = {'east': '>', 'west': '<', 'north': '^', 'south': 'v'}[exit.direction]
            image = font(22).render(label, True, (244, 222, 172))
            surface.blit(image, image.get_rect(center=(x, y - 1)))
        surface.set_clip(old_clip)
        text(surface, 'DALMASCA  /  CHAPITRE I', (26, 20), 14, GOLD)
        text(surface, region.name, (24, 43), 34, PAPER, True)
        text(surface, region.subtitle, (26, 87), 15, MUTED)
        self.sidebar(session)
        self.hud(session)
        obj = nearby(region, session.x, session.y)
        label = obj.label if obj else ''
        exit = next((e for e in region.exits if abs((e.x + .5) * TILE - session.x) < 85 and abs((e.y + .5) * TILE - session.y) < 65), None)
        if exit:
            label = 'Voyager : ' + REGIONS[exit.destination].name
        if label and session.mode == 'world' and not session.dialogue:
            rect = pg.Rect(228, 638, 510, 34)
            pg.draw.rect(surface, (21, 36, 39), rect, border_radius=7)
            image = font(16).render('E   ' + label, True, PAPER)
            surface.blit(image, image.get_rect(center=rect.center))

    def sidebar(self, session):
        s = self.surface
        panel(s, (960, 112, 296, 253))
        text(s, 'LE JOURNAL', (982, 134), 14, GOLD)
        text(s, 'Une route vers demain', (982, 163), 21, PAPER, True)
        for i, (key, label, detail) in enumerate((('road', 'Libérer la caravane', 'Route des caravanes'), ('ruins', 'Retrouver le sceau', 'Au nord du vieux pont'), ('gate', 'Ouvrir la porte', 'La Sentinelle de l’Est'))):
            yy = 210 + i * 49
            done = key in session.chapter.completed
            pg.draw.circle(s, TEAL if done else LINE, (991, yy + 5), 6, 0 if done else 1)
            text(s, label, (1008, yy - 8), 17, TEAL if done else PAPER)
            text(s, detail, (1008, yy + 15), 13, MUTED)
        panel(s, (960, 381, 296, 154))
        text(s, 'CARNET DE VOYAGE', (982, 401), 13, GOLD)
        wrap(s, session.notice, pg.Rect(982, 432, 252, 87), 16, MUTED, spacing=5)
        panel(s, (960, 551, 296, 137))
        text(s, 'LES PLAINES', (982, 570), 13, GOLD)
        points = {'camp': (993, 631), 'road': (1058, 631), 'bridge': (1122, 631), 'ruins': (1122, 598), 'gate': (1211, 631)}
        for a, b in (('camp', 'road'), ('road', 'bridge'), ('bridge', 'gate'), ('bridge', 'ruins')):
            pg.draw.line(s, LINE, points[a], points[b], 2)
        for key, point in points.items():
            pg.draw.circle(s, GOLD if key == session.place else TEAL if key in session.chapter.completed else (82, 104, 101), point, 5)
        text(s, 'Camp', (980, 648), 11, MUTED)
        text(s, 'Pont', (1108, 648), 11, MUTED)
        text(s, 'Est', (1202, 648), 11, MUTED)

    def hud(self, session):
        s, hero = self.surface, session.hero
        panel(s, (24, 712, 1232, 64))
        s.blit(art.player(hero.class_id, hero.weapon_id, hair_color=session.hair_color, size=(52, 65)), (34, 708))
        text(s, hero.name, (100, 724), 19)
        text(s, f'{hero.job.name} · Niv. {hero.level}', (100, 749), 11, GOLD)
        text(s, 'PV', (269, 724), 13, MUTED)
        bar(s, pg.Rect(300, 726, 170, 8), hero.hp, hero.max_hp, (112, 174, 127))
        text(s, f'{hero.hp} / {hero.max_hp}', (300, 743), 12, MUTED)
        text(s, 'PM', (496, 724), 13, MUTED)
        bar(s, pg.Rect(531, 726, 120, 8), hero.mp, hero.max_mp, (91, 150, 181))
        text(s, f'{hero.mp} / {hero.max_mp}', (531, 743), 12, MUTED)
        text(s, f'{hero.potions} potions   ·   {hero.gil} gils', (690, 732), 16, GOLD)
        text(s, 'Flèches / ZQSD / WASD', (997, 725), 13, MUTED)
        text(s, 'E Interagir · I Inventaire · Échap Pause', (997, 747), 12, MUTED)

    def overlay(self, alpha=170):
        veil = pg.Surface(SIZE, pg.SRCALPHA)
        veil.fill((5, 13, 20, alpha))
        self.surface.blit(veil, (0, 0))

    def title(self, session):
        self.overlay(160)
        s = self.surface
        text(s, 'UNE AVENTURE À DALMASCA', (102, 175), 15, GOLD)
        text(s, 'FINAL', (94, 220), 76, PAPER, True)
        text(s, 'CLASSE', (94, 300), 76, PAPER, True)
        pg.draw.line(s, GOLD, (102, 406), (208, 406), 2)
        text(s, 'Les braises du matin', (102, 429), 27, GOLD, True)
        wrap(s, 'Un village en cendres. Une route oubliée.\nEt ce qui reste à sauver.', pg.Rect(104, 478, 500, 95), 20, MUTED)
        self.button('Commencer l’aventure   [Entrée]', (102, 583, 364, 52), 'new', primary=True)
        self.button('Quitter', (102, 649, 364, 44), 'quit')
        text(s, 'ILLUSTRATIONS ORIGINALES  ·  PYTHON + PYGAME-CE', (102, 737), 12, MUTED)
        panel(s, (831, 434, 344, 229), color=(23, 37, 42))
        hero = art.player(session.hero.class_id, session.hero.weapon_id, hair_color=session.hair_color, size=(128, 160))
        s.blit(hero, (929, 447))
        text(s, 'CHAPITRE I', (927, 617), 13, GOLD)

    def create(self, app):
        self.overlay(205)
        s, draft = self.surface, app.builder
        chosen = JOBS[draft.class_id]
        panel(s, (96, 42, 1088, 716), border=(96, 102, 78))
        text(s, 'CRÉATION DU PERSONNAGE', (126, 64), 14, GOLD)
        text(s, 'Choisissez votre voie.', (124, 91), 30, PAPER, True)
        panel(s, (126, 145, 292, 513), color=(18, 32, 39))
        text(s, chosen.name.upper(), (150, 167), 17, GOLD)
        facing = ('down', 'left', 'up', 'right')[app.preview_facing]
        sprite = art.player(draft.class_id, chosen.starter, int(app.session.time * 7) % 4,
                            facing, draft.hair_color, size=(168, 210))
        s.blit(sprite, (188, 216))
        display_name = draft.name.strip() or 'Votre héros'
        image = font(20, True).render(display_name, True, PAPER)
        s.blit(image, image.get_rect(center=(272, 205)))
        self.button('< Tourner', (149, 437, 116, 34), ('rotate', -1))
        self.button('Tourner >', (277, 437, 116, 34), ('rotate', 1))
        text(s, '600 PV  /  60 PM  ·  3 potions', (154, 489), 14, MUTED)
        text(s, 'COMPÉTENCES', (150, 525), 12, GOLD)
        for i, skill_id in enumerate(chosen.skills):
            skill = SKILLS[skill_id]
            text(s, f'{skill.name} · {skill.cost} PM', (150, 550 + i * 30), 15)
        for i, job in enumerate(JOBS.values()):
            self.button(job.name, (454 + i * 174, 148, 162, 42), ('class', job.id), primary=job.id == draft.class_id)
        text(s, chosen.description, (454, 203), 15, TEAL)
        text(s, 'Nom du personnage', (454, 236), 14, MUTED)
        name_rect = pg.Rect(454, 261, 684, 46)
        pg.draw.rect(s, (14, 27, 34), name_rect, border_radius=6)
        pg.draw.rect(s, GOLD if app.name_focus else LINE, name_rect, 1, border_radius=6)
        if app.name_selected:
            width = min(646, font(23).size(draft.name)[0] + 8)
            pg.draw.rect(s, (54, 87, 99), (468, 266, width, 36), border_radius=3)
        caret = '|' if app.name_focus and int(app.session.time * 2) % 2 else ''
        text(s, (draft.name or 'Votre nom…') + caret, (470, 270), 23, PAPER if draft.name else MUTED)
        self.buttons.append((name_rect, 'focus_name'))
        text(s, 'Couleur de cheveux', (454, 322), 14, MUTED)
        for i, (label, color) in enumerate(HAIR_COLORS):
            rect = pg.Rect(454 + i * 62, 350, 44, 32)
            selected = color == draft.hair_color
            pg.draw.rect(s, color, rect, border_radius=6)
            pg.draw.rect(s, PAPER if selected else LINE, rect.inflate(6, 6), 2 if selected else 1, border_radius=8)
            if rect.collidepoint(self.mouse):
                text(s, label, (982, 357), 15, PAPER)
            self.buttons.append((rect.inflate(8, 8), ('hair', i)))
        text(s, 'Caractéristiques', (454, 405), 21, PAPER, True)
        text(s, f'{draft.remaining} / {POINT_BUDGET} points restants', (934, 410), 14, TEAL if draft.remaining == 0 else GOLD)
        for i, (stat, label, description) in enumerate(STAT_LABELS):
            yy = 446 + i * 48
            if not app.name_focus and app.selected_stat == i:
                pg.draw.rect(s, (32, 50, 55), (447, yy - 3, 695, 45), border_radius=5)
            text(s, label, (462, yy), 18)
            text(s, description, (462, yy + 23), 11, MUTED)
            value = draft.value(stat)
            bar(s, pg.Rect(760, yy + 13, 136, 7), value, BASE_STAT + POINT_BUDGET, TEAL)
            self.button('−', (924, yy, 38, 35), ('stat', (stat, -1)), draft.points[stat] > 0)
            image = font(23).render(str(value), True, GOLD)
            s.blit(image, image.get_rect(center=(994, yy + 17)))
            self.button('+', (1031, yy, 38, 35), ('stat', (stat, 1)), draft.remaining > 0)
            text(s, f'+{draft.points[stat]}', (1090, yy + 9), 13, MUTED)
        if app.error:
            wrap(s, app.error, pg.Rect(454, 645, 684, 24), 14, (224, 138, 113), spacing=0, max_lines=1)
        else:
            text(s, 'TAB : nom / points · Flèches : ajuster · La classe conserve votre répartition.', (454, 645), 12, MUTED)
        self.button(('[x] ' if app.with_prologue else '[ ] ') + 'Jouer le prologue', (126, 690, 292, 43), 'toggle_prologue')
        self.button('Réinitialiser les points', (454, 690, 236, 43), 'reset_points')
        self.button('Prendre la route   [Entrée]', (710, 690, 428, 43), 'begin', enabled=draft.remaining == 0, primary=True)

    def inventory(self, session):
        self.overlay(215)
        s, hero = self.surface, session.hero
        panel(s, (80, 48, 1120, 704), border=GOLD)
        text(s, 'L’ARMURERIE D’OREN' if session.inventory_shop else 'INVENTAIRE & ÉQUIPEMENT', (112, 74), 16, GOLD)
        text(s, f'{hero.name} · {hero.job.name}', (110, 104), 30, PAPER, True)
        text(s, f'{hero.gil} gils · {hero.potions} potions', (880, 112), 18, GOLD)
        panel(s, (110, 160, 266, 490), color=(18, 32, 39))
        sprite = art.player(hero.class_id, hero.weapon_id, int(session.time * 6) % 4,
                            'right', session.hair_color, size=(208, 260))
        s.blit(sprite, (139, 180))
        wrap(s, hero.weapon.name, pg.Rect(132, 448, 224, 60), 20, GOLD, max_lines=2)
        text(s, f'FOR {hero.strength}   MAG {hero.magic}', (132, 520), 17)
        text(s, f'DÉF {hero.defense}   RÉS {hero.resistance}', (132, 551), 17)
        wrap(s, 'Les bonus sont appliqués dès que l’arme est équipée.', pg.Rect(132, 590, 220, 48), 13, MUTED, max_lines=2)
        # Chaque classe dispose de son arme initiale et d’une amélioration.
        for i, weapon in enumerate(WEAPONS.values()):
            col, row = i % 2, i // 2
            x, y = 400 + col * 382, 160 + row * 120
            compatible = weapon.job == hero.class_id
            owned = weapon.id in hero.weapons
            equipped = weapon.id == hero.weapon_id
            panel(s, (x, y, 364, 108), border=GOLD if equipped else LINE)
            icon = art.weapon_icon(weapon.id, (60, 86))
            s.blit(icon, (x + 5, y + 10))
            text(s, weapon.name, (x + 72, y + 12), 16, GOLD if equipped else PAPER)
            text(s, JOBS[weapon.job].name + ' · ' + weapon.bonuses, (x + 72, y + 39), 11, MUTED)
            if owned:
                self.button('Équipée' if equipped else 'Équiper', (x + 72, y + 65, 278, 30), ('equip', weapon.id), compatible and not equipped, primary=equipped)
            elif session.inventory_shop and compatible:
                self.button(f'Acheter · {weapon.price} gils', (x + 72, y + 65, 278, 30), ('buy_weapon', weapon.id), hero.gil >= weapon.price)
            else:
                text(s, 'Réservée à une autre classe' if not compatible else 'Disponible chez Oren', (x + 72, y + 73), 12, MUTED)
        wrap(s, session.notice, pg.Rect(112, 671, 760, 48), 15, MUTED, max_lines=2)
        self.button('Reprendre · I / Échap', (892, 685, 272, 42), 'close_inventory', primary=True)

    def dialogue(self, session):
        dialog = session.dialogue
        s = self.surface
        self.overlay(55)
        panel(s, (136, 469, 1008, 279), border=(110, 108, 80))
        if dialog.portrait:
            portrait_image = art.portrait(dialog.portrait)
            s.blit(portrait_image, (160, 501))
        else:
            image = art.prop('fire' if dialog.speaker == 'Au coin du feu' else 'altar' if 'sceau' in dialog.speaker.lower() or 'sanctuaire' in dialog.speaker.lower() else 'sign')
            image = pg.transform.smoothscale(image, (96, 112))
            s.blit(image, (170, 512))
        text(s, dialog.speaker.upper(), (300, 496), 16, GOLD)
        wrap(s, dialog.text, pg.Rect(300, 532, 800, 110), 21, PAPER)
        count = len(dialog.choices)
        width = (800 - (count - 1) * 12) // count
        for i, (label, action) in enumerate(dialog.choices):
            self.button(label, (300 + i * (width + 12), 674, width, 47), ('dialogue', action), primary=i == 0)

    def pause(self, session):
        self.overlay(190)
        panel(self.surface, (420, 235, 440, 345), border=(106, 105, 80))
        text(self.surface, 'Une halte', (464, 276), 37, PAPER, True)
        text(self.surface, 'La partie est en pause.', (465, 331), 19, MUTED)
        self.button('Reprendre   [Échap]', (464, 388, 352, 49), 'resume', primary=True)
        self.button('Retour au titre', (464, 452, 352, 49), 'title')
        text(self.surface, 'La progression n’est pas sauvegardée.', (465, 531), 14, MUTED)

    def prologue(self, session):
        s = self.surface
        page = PROLOGUE_PAGES[min(session.cinematic, len(PROLOGUE_PAGES) - 1)]
        t = session.cinematic_time
        if page.scene == 'morning':
            self.draw_world(session)
            self.overlay(100)
        else:
            s.blit(art.backdrop('nibelheim', SIZE), (0, 0))
            # Les braises suivent leur propre temps, sans retarder les entrées.
            for i in range(58):
                x = int((i * 117 + session.time * (8 + i % 9)) % 1280)
                y = int(610 - (i * 43 + session.time * 32) % 570)
                radius = 1 if i % 3 else 2
                pg.draw.circle(s, (223, 150 + i % 4 * 12, 87), (x, y), radius)
            cloud_x, cloud_y = 350.0, 535.0
            demon_x, demon_y = 934.0, 526.0
            cloud_frame, demon_frame = 0, 0
            if page.scene == 'duel':
                if t < 1.65:
                    progress = clamp(t / 1.65)
                    pose = attack_pose('slash', progress, (350, 535), (720, 535), .55)
                    cloud_x, cloud_y = pose.x, pose.y
                    cloud_frame = 0 if progress < .16 else 1 if progress < .48 else 2
                    demon_frame = 1
                else:
                    progress = clamp((t - 1.65) / (DUEL_DURATION - 1.65))
                    pose = attack_pose('heavy', progress, (934, 526), (520, 535), .55)
                    demon_x, demon_y = pose.x, pose.y
                    demon_frame = frame_at(progress, 4)
                    cloud_frame = 3 if progress >= .55 else 0
                    if progress >= .55:
                        cloud_x -= ease((progress - .55) / .45) * 55
                    if abs(progress - .55) < .075:
                        flash = pg.Surface(SIZE, pg.SRCALPHA)
                        flash.fill((235, 218, 205, 90))
                        s.blit(flash, (0, 0))
                        pg.draw.line(s, (235, 220, 255), (285, 295), (575, 480), 7)
            elif page.scene == 'defeat':
                cloud_frame, demon_frame = 3, 3
                cloud_x = 295
            cloud, pivot = art.animation('cloud', cloud_frame)
            s.blit(cloud, (round(cloud_x - pivot[0]), round(cloud_y - pivot[1])))
            if page.scene in ('reveal', 'duel', 'defeat'):
                if page.scene == 'reveal':
                    demon_frame = 1 if t > 1 else 0
                demon, pivot = art.animation('sephiroth', demon_frame)
                if page.scene == 'reveal':
                    demon = demon.copy()
                    demon.set_alpha(round(255 * ease(t / 1.25)))
                s.blit(demon, (round(demon_x - pivot[0]), round(demon_y - pivot[1])))
        pg.draw.rect(s, (12, 20, 29), (0, 0, 1280, 100))
        text(s, 'PROLOGUE  /  CINQ ANS PLUS TÔT' if page.scene != 'morning' else 'CHAPITRE I  /  AUJOURD’HUI', (68, 24), 14, GOLD)
        text(s, 'Nibelheim, la nuit des cendres' if page.scene != 'morning' else 'Dalmasca, les braises du matin', (68, 54), 28, PAPER, True)
        panel(s, (68, 558, 1144, 191), border=(104, 99, 77))
        text(s, page.speaker.upper(), (100, 579), 15, GOLD)
        wrap(s, page.text, pg.Rect(100, 614, 1067, 70), 22)
        ready = t >= page.minimum_duration
        self.button('Continuer   [Entrée]' if ready else 'Le choc des lames…', (932, 699, 245, 35), 'next', enabled=ready, primary=True)
        text(s, f'{session.cinematic + 1} / {len(PROLOGUE_PAGES)}', (100, 705), 14, MUTED)

    def ending(self, session):
        self.overlay(175)
        s = self.surface
        panel(s, (262, 170, 756, 462), border=GOLD)
        victory = session.mode == 'ending'
        text(s, 'CHAPITRE I TERMINÉ' if victory else 'FIN DU VOYAGE', (316, 216), 15, GOLD)
        text(s, 'La route est libre.' if victory else 'Les sables se referment.', (312, 259), 36, PAPER, True)
        line = ('Le marchand que vous avez sauvé mène la première caravane. ' if session.chapter.rescued else 'Les caravanes reprennent leur chemin. ') + 'Mira découvre un signe sur la Sentinelle : celui du réacteur de Nibelheim. Le passé n’a pas fini de vous chercher.' if victory else 'Votre voyage s’arrête ici. Revenez au camp entre les combats et protégez-vous lorsque la Sentinelle prépare sa frappe.'
        wrap(s, line, pg.Rect(316, 330, 647, 133), 22, MUTED)
        text(s, f'{session.hero.name} · Niveau {session.hero.level} · {session.hero.gil} gils', (316, 487), 19, GOLD)
        self.button('Revenir au titre', (316, 545, 648, 50), 'title', primary=True)

    def battle(self, session):
        s, battle, hero = self.surface, session.battle, session.hero
        text(s, 'RENCONTRE  /  DALMASCA', (26, 20), 14, GOLD)
        text(s, 'La Sentinelle de l’Est' if session.destination == 'gate' else 'Sous un ciel de poussière', (24, 43), 34, PAPER, True)
        text(s, f'Tour {battle.turn}   ·   Choisissez votre action, puis laissez le tour se dérouler.', (26, 87), 15, MUTED)
        stage = pg.Rect(24, 112, 912, 442)
        pg.draw.rect(s, (65, 93, 87), stage, border_radius=7)
        old_clip = s.get_clip()
        s.set_clip(stage)
        s.blit(art.backdrop('battle_dalmasca', stage.size), stage)
        positions = [(706, 385)] if len(battle.monsters) == 1 else [(677, 353 + i * 128) for i in range(len(battle.monsters))]
        hx, hy = 223, 449
        motion = battle.motion
        progress = motion.progress if motion else 0
        hero_pose = attack_pose(motion.kind, progress, (hx, hy),
                                (positions[motion.target][0] - 105, positions[motion.target][1]),
                                motion.impact_ratio) if motion and motion.actor == -1 else attack_pose('idle', 0, (hx, hy), (hx, hy))
        hx, hy = hero_pose.x, hero_pose.y
        if hero.shield:
            pg.draw.ellipse(s, GOLD, (hx - 72, hy - 178, 144, 190), 3)
            text(s, f'Égide · {hero.shield}', (hx - 52, hy - 197), 13, GOLD)
        if hero.defending:
            pg.draw.ellipse(s, (85, 142, 163), (hx - 75, hy - 173, 152, 189), 3)
        shadow(s, hx - 62, hero_pose.ground_y - 6, 124, 22)
        if motion and motion.actor == -1 and motion.kind not in ('heal', 'guard', 'ward'):
            hero_image, pivot = art.player_action(hero, action_frame_at(motion.kind, progress, motion.impact_ratio), session.hair_color)
            s.blit(hero_image, (round(hx - pivot[0]), round(hy - pivot[1])))
        else:
            hero_image = art.player(hero.class_id, hero.weapon_id, 0, 'right', session.hair_color, size=(128, 160))
            s.blit(hero_image, (round(hx - 64), round(hy - 156)))
        for index, monster in enumerate(battle.monsters):
            x, y = positions[index]
            acting = motion and motion.actor == index
            pose = attack_pose(motion.kind, progress, (x, y), (223 + 105, 449), motion.impact_ratio) if acting else attack_pose('idle', 0, (x, y), (x, y))
            x, y = pose.x, pose.y
            if not monster.is_alive:
                text(s, 'VAINCU', (x - 30, y - 20), 14, MUTED)
                continue
            kind = 'boss' if monster.name == 'Sentinelle' else 'flan' if monster.name == 'Flandwich' else 'wolf'
            scale_factor = 3 if kind == 'boss' else 2
            shadow(s, x - 56, pose.ground_y - 2, 112, 20)
            if acting and motion.kind in ('claw', 'jump', 'heavy'):
                name = {'claw': 'wolf_claw', 'jump': 'slime_jump', 'heavy': 'sentinel_strike'}[motion.kind]
                sprite, pivot = art.animation(name, action_frame_at(motion.kind, progress, motion.impact_ratio))
                scaled = (max(1, round(sprite.get_width() * pose.scale_x)), max(1, round(sprite.get_height() * pose.scale_y)))
                sprite = pg.transform.smoothscale(sprite, scaled)
                pivot = (pivot[0] * pose.scale_x, pivot[1] * pose.scale_y)
                s.blit(sprite, (round(x - pivot[0]), round(y - pivot[1])))
            else:
                animation_frame = min(3, int(progress * 4)) if acting else int(session.time * 2) % 2
                if acting and motion.kind == 'charge':
                    animation_frame = 2 + min(1, int(progress * 2))
                sprite = art.actor(kind, animation_frame, size=(336, 224) if kind == 'boss' else (56 * scale_factor, 64 * scale_factor))
                s.blit(sprite, (round(x - sprite.get_width() / 2), round(y - sprite.get_height() + 6)))
            # Les étiquettes restent à leur place pendant l'approche et le bond.
            label_x, label_y = positions[index]
            target_rect = pg.Rect(label_x - 74, label_y + 25, 148, 32)
            pg.draw.rect(s, (29, 48, 45), target_rect, border_radius=5)
            label = font(14).render(f'{index + 1}  {monster.name}', True, GOLD if index == battle.target else PAPER)
            s.blit(label, label.get_rect(center=target_rect.center))
            self.buttons.append((pg.Rect(label_x - 90, label_y - 170, 180, 225), ('target', index)))
            if index == battle.target:
                pg.draw.polygon(s, GOLD, [(label_x, label_y - 174), (label_x - 7, label_y - 185), (label_x + 7, label_y - 185)])
            if getattr(monster, 'charged', False) or (acting and motion.kind == 'charge'):
                radius = 56 + int(math.sin(session.time * 5) * 6)
                pg.draw.circle(s, (215, 146, 74), (round(x), round(y - 55)), radius, 3)
        if motion:
            if motion.kind in ('fire', 'arcane', 'frost', 'storm', 'shoot') and motion.actor == -1:
                tx, ty = positions[motion.target]
                launch = motion.impact_ratio * .8 if motion.kind == 'shoot' else .18
                flight = ease((progress - launch) / (motion.impact_ratio - launch))
                px = hx + (tx - hx) * flight
                py = hy - 70 + ((ty - 50) - (hy - 70)) * flight
                targets = positions if motion.skill_id and SKILLS[motion.skill_id].effect.endswith('_all') else (positions[motion.target],)
                color = (165, 218, 244) if motion.kind == 'frost' else (177, 139, 234) if motion.kind in ('arcane', 'storm') else (219, 192, 126)
                for tx, ty in targets:
                    px = hx + (tx - hx) * flight
                    py = hy - 100 + ((ty - 70) - (hy - 100)) * flight
                    if motion.kind == 'shoot':
                        if launch <= progress <= motion.impact_ratio:
                            pg.draw.line(s, color, (px - 38, py), (px, py), 3)
                            pg.draw.polygon(s, PAPER, ((px + 8, py), (px - 3, py - 4), (px - 3, py + 4)))
                        if abs(progress - motion.impact_ratio) < .1:
                            pg.draw.circle(s, TEAL if motion.skill_id == 'venom' else GOLD, (round(tx), round(ty - 70)), 22, 2)
                    elif motion.kind == 'fire':
                        flame = art.effect('fire_projectile', int(session.time * 16) % 8)
                        s.blit(flame, flame.get_rect(center=(round(px), round(py))))
                    else:
                        for trail in range(5, 0, -1):
                            pg.draw.circle(s, color, (round(px - trail * 9), round(py)), max(2, 13 - trail * 2), 1)
                        pg.draw.circle(s, color, (round(px), round(py)), 13)
                        if abs(progress - motion.impact_ratio) < .12:
                            for ray in range(8):
                                angle = ray * math.pi / 4 + progress * 3
                                pg.draw.line(s, color, (tx, ty - 70), (tx + math.cos(angle) * 43, ty - 70 + math.sin(angle) * 43), 3)
            elif motion.kind in ('heal', 'ward'):
                for i in range(8):
                    xx, yy = hx + math.sin(i * 3) * 55, hy - (progress * 150 + i * 19) % 155
                    pg.draw.line(s, TEAL, (xx - 4, yy), (xx + 4, yy), 2)
                    pg.draw.line(s, TEAL, (xx, yy - 4), (xx, yy + 4), 2)
            elif motion.kind in ('slash', 'smash', 'claw', 'heavy', 'enemy') and abs(progress - motion.impact_ratio) < .10:
                tx, ty = positions[motion.target] if motion.actor == -1 else (223, 449)
                if motion.kind == 'claw':
                    for claw in range(3):
                        pg.draw.line(s, (245, 190, 134), (tx - 32 + claw * 13, ty - 115), (tx + 12 + claw * 13, ty - 47), 3)
                else:
                    targets = positions if motion.actor == -1 and motion.skill_id and SKILLS[motion.skill_id].effect.endswith('_all') else ((tx, ty),)
                    for hit_x, hit_y in targets:
                        swing = pg.Rect(hit_x - 64, hit_y - 154, 128, 132)
                        pg.draw.arc(s, (255, 232, 178), swing, -.6, 1.8, 5)
            elif motion.kind == 'jump' and progress > motion.impact_ratio and progress < motion.impact_ratio + .14:
                radius = 16 + int((progress - motion.impact_ratio) * 260)
                pg.draw.ellipse(s, (187, 168, 113), (223 - radius, 449 - radius / 3, radius * 2, radius * .65), 3)
        for hit in session.hits:
            x, y = (hx, hy) if hit['target'] == -1 else positions[hit['target']]
            age = session.time - hit['time']
            number = str(hit['amount']) if hit['amount'] > 0 else '+' + str(-hit['amount'])
            image = font(32).render(number, True, (255, 215, 150) if hit['amount'] > 0 else TEAL)
            s.blit(image, image.get_rect(center=(x, y - 140 - age * 45)))
        s.set_clip(old_clip)
        panel(s, (960, 112, 296, 300))
        text(s, 'ADVERSAIRES', (981, 134), 14, GOLD)
        for i, monster in enumerate(battle.monsters):
            yy = 180 + i * 75
            text(s, f'{i + 1}. {monster.name}', (982, yy), 19, GOLD if i == battle.target else PAPER)
            bar(s, pg.Rect(982, yy + 32, 249, 8), monster.hp, monster.max_hp, (180, 111, 89))
            text(s, f'{monster.hp} / {monster.max_hp} PV' + (' · Poison' if i in battle.poison else '') + (' · Givre' if i in battle.chilled else ''), (982, yy + 46), 13, MUTED)
        panel(s, (960, 430, 296, 258))
        text(s, 'DERNIERS ÉVÉNEMENTS', (982, 451), 13, GOLD)
        wrap(s, '\n'.join(battle.log[-3:]), pg.Rect(982, 487, 250, 178), 16, MUTED, spacing=6)
        charged = any(getattr(m, 'charged', False) and m.is_alive for m in battle.monsters)
        text(s, 'FRAPPE LOURDE IMMINENTE · Défendez-vous !' if charged else 'TAB / Flèches : cible   ·   Vous pouvez aussi cliquer sur un adversaire.', (28, 574), 17, GOLD if charged else MUTED)
        if battle.result is not None:
            self.button('Victoire ! Continuer   [Entrée]' if battle.result else 'Défaite · Continuer   [Entrée]', (24, 615, 912, 58), 'finish_battle', primary=True)
        else:
            ready = battle.motion is None
            for i, (key, label, skill_id) in enumerate(battle.actions):
                column, row = i % 3, i // 3
                x, y = 24 + column * 308, 602 + row * 47
                cost = f' · {SKILLS[skill_id].cost} PM' if skill_id else ''
                cooldown = battle.cooldowns.get(skill_id, 0)
                if cooldown:
                    cost = f' · {cooldown} tour(s)'
                self.button(f'{key}  {label}{cost}', (x, y, 298, 41), ('battle', key), ready and not battle.unavailable(key), primary=i == 0)
                if skill_id and pg.Rect(x, y, 298, 41).collidepoint(self.mouse):
                    pg.draw.rect(s, PANEL, (26, 559, 905, 32), border_radius=5)
                    text(s, SKILLS[skill_id].description, (34, 566), 15, PAPER)
        self.hud(session)

    def draw(self, app, mouse):
        self.mouse = mouse
        self.buttons = []
        s, session = self.surface, app.session
        s.fill(INK)
        battle_visible = session.mode == 'battle' or (session.mode == 'pause' and session.previous_mode == 'battle')
        if battle_visible and session.battle:
            self.battle(session)
        elif session.mode == 'prologue' or (session.mode == 'pause' and session.previous_mode == 'prologue'):
            self.prologue(session)
        else:
            self.draw_world(session)
        if session.mode == 'title':
            self.title(session)
        elif session.mode == 'create':
            self.create(app)
        elif session.mode == 'inventory':
            self.buttons = []
            self.inventory(session)
        elif session.mode == 'pause':
            self.buttons = []
            self.pause(session)
        elif session.mode in ('ending', 'dead'):
            self.buttons = []
            self.ending(session)
        if session.dialogue and session.mode == 'world':
            self.buttons = []
            self.dialogue(session)
        return s
