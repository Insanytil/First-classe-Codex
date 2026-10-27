"""Point d'entrée Pygame : aucune saisie ou animation ne bloque la boucle."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame as pg

from poo.graphics.character import CharacterDraft, HAIR_COLORS, NAME_LIMIT, STAT_KEYS
from poo.graphics.state import Session
from poo.graphics.view import SIZE, View
from poo.characters.jobs import JOBS


class Application:
    def __init__(self, quick=False):
        pg.display.init()
        pg.font.init()
        desktops = pg.display.get_desktop_sizes()
        desktop = desktops[0] if desktops else SIZE
        fit = max(.25, min(1, (desktop[0] - 64) / SIZE[0], (desktop[1] - 96) / SIZE[1]))
        initial_size = (round(SIZE[0] * fit), round(SIZE[1] * fit))
        self.window = pg.display.set_mode(initial_size, pg.RESIZABLE)
        pg.display.set_caption('Final Classe — Les braises du matin')
        self.clock = pg.time.Clock()
        self.view = View()
        self.session = Session()
        self.running = True
        self.held = set()
        self.builder = CharacterDraft()
        self.name_focus = True
        self.name_selected = False
        self.preview_facing = 0
        self.selected_stat = 0
        self.error = ''
        self.with_prologue = not quick
        self.viewport = pg.Rect((0, 0), self.window.get_size())
        self.focused = True
        self.view.draw(self, (-1, -1))

    def logical_position(self, position):
        if not self.viewport.collidepoint(position):
            return (-1, -1)
        return ((position[0] - self.viewport.x) * SIZE[0] / self.viewport.width,
                (position[1] - self.viewport.y) * SIZE[1] / self.viewport.height)

    def perform(self, action):
        if action is None:
            return
        session = self.session
        if isinstance(action, tuple):
            kind, value = action
            if session.mode == 'create' and kind in ('stat', 'hair', 'rotate', 'class'):
                self.name_focus = False
                self.name_selected = False
                pg.key.stop_text_input()
                if kind == 'stat':
                    stat, delta = value
                    self.selected_stat = STAT_KEYS.index(stat)
                    self.builder.adjust(stat, delta)
                elif kind == 'hair':
                    self.builder.hair_color = HAIR_COLORS[value][1]
                elif kind == 'class' and value in JOBS:
                    self.builder.class_id = value
                else:
                    self.preview_facing = (self.preview_facing + value) % 4
                self.error = ''
            elif kind == 'dialogue' and session.mode == 'world':
                session.choose_dialogue(value)
            elif kind == 'battle' and session.mode == 'battle':
                session.battle.choose(value)
            elif kind == 'equip':
                session.equip_weapon(value)
            elif kind == 'buy_weapon':
                session.buy_weapon(value)
            elif kind == 'target' and session.mode == 'battle' and session.battle.result is None and session.battle.monsters[value].is_alive:
                session.battle.target = value
            return
        if action == 'quit':
            self.running = False
        elif action == 'new':
            session.mode = 'create'
            self.builder = CharacterDraft()
            self.name_focus = True
            self.name_selected = False
            self.preview_facing = 0
            self.selected_stat = 0
            self.error = ''
            pg.key.start_text_input()
        elif action == 'begin':
            try:
                session.start(prologue=self.with_prologue, draft=self.builder)
            except ValueError as error:
                self.error = str(error)
                return
            self.held.clear()
            pg.key.stop_text_input()
        elif action == 'focus_name':
            self.name_focus = True
            pg.key.start_text_input()
        elif action == 'reset_points':
            self.builder.reset_points()
            self.error = ''
        elif action == 'toggle_prologue':
            self.with_prologue = not self.with_prologue
        elif action == 'next':
            session.advance_prologue()
            self.held.clear()
        elif action == 'resume':
            session.pause()
            self.held.clear()
        elif action == 'title':
            self.session = Session()
            self.held.clear()
            pg.key.stop_text_input()
        elif action == 'finish_battle':
            session.finish_battle()
        elif action == 'inventory':
            session.open_inventory()
            self.held.clear()
        elif action == 'close_inventory':
            session.close_inventory()
            self.held.clear()

    def keydown(self, event):
        key, session = event.key, self.session
        fresh = key not in self.held
        self.held.add(key)
        if not fresh:
            return
        if key == pg.K_F11:
            if self.window.get_flags() & pg.FULLSCREEN:
                self.window = pg.display.set_mode(SIZE, pg.RESIZABLE)
            else:
                self.window = pg.display.set_mode((0, 0), pg.FULLSCREEN)
            return
        if key == pg.K_ESCAPE:
            self.held.clear()
            if session.mode == 'create':
                session.mode = 'title'
                pg.key.stop_text_input()
            elif session.mode == 'inventory':
                session.close_inventory()
            elif session.mode == 'title':
                self.running = False
            elif session.mode == 'pause':
                session.pause()
            elif session.dialogue:
                if any(action in ('rescue', 'tracks') for _, action in session.dialogue.choices):
                    session.pause()
                else:
                    session.dialogue = None
            else:
                session.pause()
            return
        if session.mode == 'create':
            if key == pg.K_TAB:
                self.name_focus = not self.name_focus
                self.name_selected = False
                if self.name_focus:
                    pg.key.start_text_input()
                else:
                    pg.key.stop_text_input()
            elif self.name_focus and key == pg.K_a and getattr(event, 'mod', 0) & pg.KMOD_CTRL:
                self.name_selected = True
            elif self.name_focus and key == pg.K_BACKSPACE:
                self.builder.name = '' if self.name_selected else self.builder.name[:-1]
                self.name_selected = False
                self.error = ''
            elif key == pg.K_RETURN:
                self.perform('begin')
            elif not self.name_focus:
                if key in (pg.K_UP, pg.K_DOWN):
                    self.selected_stat = (self.selected_stat + (1 if key == pg.K_DOWN else -1)) % 4
                elif key in (pg.K_LEFT, pg.K_RIGHT):
                    self.perform(('stat', (STAT_KEYS[self.selected_stat], 1 if key == pg.K_RIGHT else -1)))
            return

        if session.mode == 'title':
            if key == pg.K_RETURN:
                self.perform('new')
            return
        if session.mode == 'prologue':
            if key in (pg.K_RETURN, pg.K_SPACE):
                self.perform('next')
            return
        if session.mode == 'pause':
            if key == pg.K_RETURN:
                self.perform('resume')
            return
        if session.mode == 'inventory':
            if key in (pg.K_i, pg.K_RETURN):
                self.perform('close_inventory')
            return
        if session.mode in ('ending', 'dead'):
            if key == pg.K_RETURN:
                self.perform('title')
            return
        if session.dialogue:
            if key in (pg.K_RETURN, pg.K_SPACE, pg.K_e):
                self.perform(('dialogue', session.dialogue.choices[0][1]))
            elif key in (pg.K_1, pg.K_2, pg.K_3):
                index = (pg.K_1, pg.K_2, pg.K_3).index(key)
                if index < len(session.dialogue.choices):
                    self.perform(('dialogue', session.dialogue.choices[index][1]))
            return
        if session.mode == 'battle':
            if session.battle.result is not None:
                if key in (pg.K_RETURN, pg.K_SPACE):
                    self.perform('finish_battle')
            elif key in (pg.K_TAB, pg.K_RIGHT, pg.K_DOWN):
                session.battle.cycle()
            elif key in (pg.K_LEFT, pg.K_UP):
                session.battle.cycle(-1)
            else:
                numbers = {pg.K_1: '1', pg.K_2: '2', pg.K_3: '3', pg.K_4: '4',
                           pg.K_5: '5', pg.K_6: '6', pg.K_KP5: '5', pg.K_KP6: '6',
                           pg.K_KP1: '1', pg.K_KP2: '2', pg.K_KP3: '3', pg.K_KP4: '4'}
                character = getattr(event, 'unicode', '')
                action = numbers.get(key, {'&': '1', 'é': '2', '"': '3', "'": '4', '(': '5', '-': '6'}.get(character, character))
                if action in ('1', '2', '3', '4', '5', '6'):
                    session.battle.choose(action)
            return
        if key == pg.K_i:
            self.perform('inventory')
        elif key in (pg.K_e, pg.K_RETURN, pg.K_SPACE):
            session.interact()

    def event(self, event):
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.WINDOWFOCUSLOST:
            self.focused = False
            self.held.clear()
            if self.session.mode in ('world', 'battle', 'prologue'):
                self.session.pause()
        elif event.type == pg.WINDOWFOCUSGAINED:
            self.focused = True
        elif event.type == pg.KEYDOWN:
            self.keydown(event)
        elif event.type == pg.KEYUP:
            self.held.discard(event.key)
        elif event.type == pg.TEXTINPUT and self.session.mode == 'create' and self.name_focus:
            base = '' if self.name_selected else self.builder.name
            self.builder.name = (base + event.text)[:NAME_LIMIT]
            self.name_selected = False
            self.error = ''
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            # Rafraîchir les zones cliquables si une transition a eu lieu.
            position = self.logical_position(event.pos)
            self.view.draw(self, position)
            self.perform(self.view.click(position))

    def direction(self):
        if not self.focused:
            return (0, 0)
        held = self.held
        right = bool(held & {pg.K_RIGHT, pg.K_d})
        left = bool(held & {pg.K_LEFT, pg.K_a, pg.K_q})
        down = bool(held & {pg.K_DOWN, pg.K_s})
        up = bool(held & {pg.K_UP, pg.K_w, pg.K_z})
        return (int(right) - int(left), int(down) - int(up))

    def frame(self, dt):
        self.session.update(dt, self.direction())
        mouse = self.logical_position(pg.mouse.get_pos())
        image = self.view.draw(self, mouse)
        window_width, window_height = self.window.get_size()
        ratio = min(window_width / SIZE[0], window_height / SIZE[1])
        size = (max(1, round(SIZE[0] * ratio)), max(1, round(SIZE[1] * ratio)))
        self.viewport = pg.Rect((0, 0), size)
        self.viewport.center = (window_width // 2, window_height // 2)
        self.window.fill((8, 14, 20))
        # Rééchantillonnage doux pour les sprites illustrés et l'interface.
        self.window.blit(pg.transform.smoothscale(image, size), self.viewport)
        pg.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000
            for event in pg.event.get():
                self.event(event)
            self.frame(dt)


def run(quick=False):
    try:
        Application(quick=quick).run()
    finally:
        pg.quit()
