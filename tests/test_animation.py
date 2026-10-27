import unittest

from poo.characters import Hero
from poo.characters.boss import Gatekeeper
from poo.game.battle import Battle
from poo.game.encounters import flan, wolf
from poo.game.prologue import DUEL_DURATION, PROLOGUE_PAGES
from poo.graphics.animation import attack_pose, frame_at
from poo.graphics.character import CharacterDraft
from poo.graphics.state import Session


class AnimationTests(unittest.TestCase):
    def test_damage_is_applied_at_contact_once_and_recovery_still_plays(self):
        hero = Hero('Lucien', strength=20)
        enemy = wolf()
        battle = Battle(hero, [enemy])
        battle.choose('1')
        motion = battle.motion
        hp = enemy.hp
        battle.update(motion.contact_time - .001)
        self.assertEqual(enemy.hp, hp)
        battle.update(.002)
        self.assertLess(enemy.hp, hp)
        self.assertIs(battle.motion, motion)
        self.assertTrue(motion.impact_applied)
        self.assertFalse(battle.choose('1'))
        after = enemy.hp
        battle.update(.05)
        self.assertEqual(enemy.hp, after)

    def test_creatures_have_different_attack_timelines(self):
        self.assertEqual(Battle.enemy_motion(wolf()), 'claw')
        self.assertEqual(Battle.enemy_motion(flan()), 'jump')
        boss = Gatekeeper()
        self.assertEqual(Battle.enemy_motion(boss), 'charge')
        boss.charged = True
        self.assertEqual(Battle.enemy_motion(boss), 'heavy')

    def test_sword_and_claw_reach_the_opponent_and_return_home(self):
        for kind in ('slash', 'claw', 'heavy'):
            start, target = (100, 400), (600, 350)
            self.assertEqual((attack_pose(kind, 0, start, target).x,
                              attack_pose(kind, 0, start, target).y), start)
            contact = attack_pose(kind, .55, start, target)
            self.assertAlmostEqual(contact.x, target[0])
            self.assertAlmostEqual(contact.y, target[1])
            end = attack_pose(kind, 1, start, target)
            self.assertEqual((end.x, end.y), start)

    def test_slime_squashes_takes_off_and_lands_at_contact(self):
        start, target = (700, 400), (300, 450)
        preparing = attack_pose('jump', .09, start, target, .62)
        self.assertLess(preparing.scale_y, 1)
        self.assertGreater(preparing.scale_x, 1)
        airborne = attack_pose('jump', .4, start, target, .62)
        self.assertLess(airborne.y, airborne.ground_y - 100)
        contact = attack_pose('jump', .62, start, target, .62)
        self.assertAlmostEqual(contact.y, target[1])
        self.assertAlmostEqual(contact.x, target[0])
        landing = attack_pose('jump', .63, start, target, .62)
        self.assertLess(landing.scale_y, 1)
        end = attack_pose('jump', 1, start, target, .62)
        self.assertAlmostEqual(end.x, start[0])
        self.assertAlmostEqual(end.y, start[1])

    def test_animation_frames_do_not_loop_during_recovery(self):
        self.assertEqual(frame_at(0, 8), 0)
        self.assertEqual(frame_at(.55, 8), 4)
        self.assertEqual(frame_at(1, 8), 7)
        self.assertEqual(frame_at(2, 8), 7)

    def test_prologue_duel_cannot_be_skipped_before_the_counterattack(self):
        session = Session()
        draft = CharacterDraft(name='Lucien', points={'strength': 10, 'magic': 10, 'defense': 0, 'resistance': 0})
        session.start(draft)
        for _ in range(3):
            self.assertTrue(session.advance_prologue())
        self.assertEqual(PROLOGUE_PAGES[session.cinematic].scene, 'duel')
        self.assertFalse(session.advance_prologue())
        for _ in range(round(DUEL_DURATION / .025) + 1):
            session.update(.025)
        self.assertTrue(session.advance_prologue())
        while session.mode == 'prologue':
            self.assertTrue(session.advance_prologue())
        self.assertEqual(session.mode, 'world')
        self.assertEqual(session.hero.hp, session.hero.max_hp)
        self.assertEqual(session.hero.name, 'Lucien')

    def test_pause_freezes_prologue_choreography(self):
        session = Session()
        session.mode = 'prologue'
        session.cinematic = 3
        session.update(.025)
        before = session.cinematic_time
        session.pause()
        for _ in range(100):
            session.update(.025)
        self.assertEqual(session.cinematic_time, before)
