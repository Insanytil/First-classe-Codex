"""Règles du mode graphique : tests exécutables sans installer Pygame."""
import unittest
from collections import deque

from poo.graphics.character import CharacterDraft
from poo.graphics.state import Session
from poo.graphics.world import COLS, ROWS, REGIONS, TILE, move, passable


class GraphicsStateTests(unittest.TestCase):
    def draft(self, name='Lucien'):
        return CharacterDraft(name=name, points={
            'strength': 10, 'magic': 10, 'defense': 0, 'resistance': 0,
        })

    def session(self):
        session = Session()
        session.start(self.draft(), prologue=False)
        return session

    def test_start_is_fully_graphical_and_validates_name(self):
        session = Session()
        self.assertEqual(session.mode, 'title')
        with self.assertRaises(ValueError):
            session.start(self.draft('12'))
        self.assertEqual(session.mode, 'title')
        session.start(self.draft())
        self.assertEqual(session.mode, 'prologue')
        self.assertEqual(session.hero.name, 'Lucien')

    def test_continuous_movement_stops_without_held_direction(self):
        session = self.session()
        initial = session.x
        session.update(.02, (1, 0))
        session.update(.02, (1, 0))
        self.assertAlmostEqual(session.x - initial, 6.2)
        position = (session.x, session.y)
        session.update(.02)
        self.assertEqual((session.x, session.y), position)
        self.assertFalse(session.walking)

    def test_diagonal_speed_is_normalized(self):
        session = self.session()
        x, y = session.x, session.y
        session.update(.02, (1, 1))
        distance = ((session.x - x) ** 2 + (session.y - y) ** 2) ** .5
        self.assertAlmostEqual(distance, 3.1)

    def test_river_collision_and_bridge(self):
        region = REGIONS['bridge']
        x, _ = move(region, 5.5 * TILE, 4.5 * TILE, 300, 0)
        self.assertLess(x, 6 * TILE)
        x, _ = move(region, 6.5 * TILE, 5.5 * TILE, 300, 0)
        self.assertGreater(x, 11 * TILE)

    def test_every_exit_has_a_reachable_spawn_and_return(self):
        for name, region in REGIONS.items():
            self.assertTrue(passable(region, *region.spawn), name)
            for exit in region.exits:
                self.assertIn(exit.destination, REGIONS)
                self.assertTrue(any(other.destination == name for other in REGIONS[exit.destination].exits))
                session = self.session()
                session.place = name
                session.travel(exit.destination)
                self.assertTrue(passable(REGIONS[exit.destination], session.x, session.y), (name, exit.destination))

    def test_objectives_and_exits_are_reachable_from_spawn(self):
        for name, region in REGIONS.items():
            start = int(region.spawn[0] // TILE), int(region.spawn[1] // TILE)
            visited, queue = {start}, deque([start])
            while queue:
                x, y = queue.popleft()
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    point = x + dx, y + dy
                    if point in visited or not (0 <= point[0] < COLS and 0 <= point[1] < ROWS):
                        continue
                    if passable(region, (point[0] + .5) * TILE, (point[1] + .5) * TILE):
                        queue.append(point)
                        visited.add(point)
            for exit in region.exits:
                self.assertIn((exit.x, exit.y), visited, (name, exit.destination))
            for obj in region.objects:
                if obj.label:
                    self.assertTrue(any(abs(x - obj.x) <= 1 and abs(y - obj.y) <= 1 for x, y in visited), (name, obj.kind))

    def test_dialogue_freezes_movement_and_pause_freezes_battle(self):
        session = self.session()
        session.interact_object('mira')
        old = session.x, session.y
        session.update(.05, (1, 1))
        self.assertEqual(old, (session.x, session.y))
        session.choose_dialogue('close')
        session.interact_object('wolf')
        session.choose_dialogue('road')
        session.battle.choose('1')
        session.pause()
        session.update(.05)
        self.assertEqual(session.battle.motion.elapsed, 0)
        session.pause()
        session.update(.05)
        self.assertGreater(session.battle.motion.elapsed, 0)

    def test_gate_is_locked_and_rewards_cannot_be_farmed(self):
        session = self.session()
        session.interact_object('boss')
        self.assertEqual(session.dialogue.choices, (('Fermer', 'close'),))
        session.choose_dialogue('gate')
        self.assertIsNone(session.battle)
        session.dialogue = None
        session.chapter.completed.add('road')
        session.interact_object('wolf')
        self.assertEqual(session.dialogue.choices, (('Fermer', 'close'),))

    def test_fire_and_shop_use_existing_rules(self):
        session = self.session()
        session.hero.take_damage(100)
        session.hero.mp = 0
        session.interact_object('fire')
        self.assertEqual((session.hero.hp, session.hero.mp), (600, 60))
        session.choose_dialogue('close')
        session.interact_object('merchant')
        session.choose_dialogue('buy')
        self.assertEqual(session.hero.potions, 3)
        session.hero.gain_gil(25)
        session.choose_dialogue('close')
        session.interact_object('merchant')
        session.choose_dialogue('buy')
        self.assertEqual((session.hero.potions, session.hero.gil), (4, 0))

    def test_complete_graphical_chapter(self):
        session = self.session()
        for kind, objective in (('wolf', 'road'), ('altar', 'ruins'), ('boss', 'gate')):
            session.interact_object(kind)
            session.choose_dialogue(objective)
            self.assertEqual(session.mode, 'battle')
            for _ in range(3000):
                battle = session.battle
                if battle.result is not None:
                    break
                if not battle.motion:
                    if any(getattr(m, 'charged', False) for m in battle.monsters):
                        action = '4'
                    elif session.hero.hp < 300 and session.hero.can_drink_potion:
                        action = '3'
                    else:
                        action = '2' if session.hero.can_cast_fire else '1'
                    battle.choose(action)
                session.update(.05)
            self.assertTrue(session.battle.result)
            session.finish_battle()
            if objective == 'road':
                session.choose_dialogue('rescue')
                self.assertTrue(session.chapter.rescued)
            if objective != 'gate':
                if session.dialogue:
                    session.choose_dialogue('close')
                session.interact_object('fire')
                session.choose_dialogue('close')
        self.assertEqual(session.mode, 'ending')
        self.assertEqual(session.chapter.completed, {'road', 'ruins', 'gate'})
        self.assertTrue(session.hero.is_alive)

    def test_defeat_cannot_mark_an_objective_complete(self):
        session = self.session()
        session.interact_object('wolf')
        session.choose_dialogue('road')
        session.hero.take_damage(9999)
        session.battle.result = False
        session.finish_battle()
        self.assertEqual(session.mode, 'dead')
        self.assertEqual(session.chapter.completed, set())

    def test_painted_bridge_rail_cannot_be_walked_through(self):
        region = REGIONS['bridge']
        self.assertTrue(passable(region, 400, 264))
        self.assertFalse(passable(region, 400, 318))
        self.assertFalse(passable(region, 400, 215))
        x, y = move(region, 400, 264, 0, 200)
        self.assertLess(y, 304)
