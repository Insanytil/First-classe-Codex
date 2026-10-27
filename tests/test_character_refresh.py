import unittest

from poo.graphics.animation import action_frame_at
from poo.graphics.character import CharacterDraft
from poo.graphics.state import Session
from poo.graphics.resources import sheet


class CharacterRefreshTests(unittest.TestCase):
    def session(self):
        session = Session()
        session.start(CharacterDraft(name='Lucien', points={
            'strength': 10, 'magic': 10, 'defense': 0, 'resistance': 0,
        }), prologue=False)
        return session

    def test_dialogue_portraits_match_the_people_present(self):
        for obj, portrait in (('mira', 'mira'), ('merchant', 'merchant'),
                              ('traveler', 'traveler'), ('wolf', 'traveler'), ('boss', 'boss')):
            session = self.session()
            session.interact_object(obj)
            self.assertEqual(session.dialogue.portrait, portrait)
        session = self.session()
        session.chapter.completed.update(('road', 'ruins'))
        session.interact_object('boss')
        self.assertEqual(session.dialogue.portrait, 'boss')

    def test_environment_dialogues_do_not_show_a_random_merchant(self):
        for obj in ('fire', 'sign', 'altar'):
            session = self.session()
            session.interact_object(obj)
            self.assertIsNone(session.dialogue.portrait)

    def test_purchases_keep_the_merchant_portrait(self):
        session = self.session()
        session.interact_object('merchant')
        session.choose_dialogue('buy')
        self.assertEqual(session.dialogue.portrait, 'merchant')

    def test_reward_dialogue_keeps_the_traveler_portrait(self):
        session = self.session()
        session.interact_object('traveler')
        session.choose_dialogue('road')
        session.battle.result = True
        session.finish_battle()
        self.assertEqual(session.dialogue.portrait, 'traveler')

    def test_key_pose_is_synchronized_with_damage_for_each_creature(self):
        for kind, ratio, contact in (('slash', .55, 4), ('claw', .55, 4),
                                     ('jump', .62, 5), ('heavy', .66, 4)):
            self.assertLess(action_frame_at(kind, ratio - .001, ratio), contact)
            self.assertEqual(action_frame_at(kind, ratio, ratio), contact)
            self.assertEqual(action_frame_at(kind, 1, ratio), 7)

    def test_refreshed_characters_have_detailed_source_images(self):
        for name in ('hero_body', 'hero_hair', 'mira', 'merchant', 'traveler', 'boss'):
            self.assertGreaterEqual(sheet(name).cell[1], 320, name)
        for name in ('portrait_merchant', 'portrait_traveler', 'portrait_boss', 'portrait_mira'):
            self.assertEqual((sheet(name).columns, sheet(name).rows), (1, 1))
        strike = sheet('sentinel_strike')
        self.assertEqual(strike.columns * strike.rows, 8)
        self.assertEqual(len(strike.anchors), 8)
