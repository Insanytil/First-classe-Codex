import unittest

from poo.graphics.character import BASE_STAT, HAIR_COLORS, POINT_BUDGET, STAT_KEYS, CharacterDraft
from poo.graphics.state import Session


class CharacterBuilderTests(unittest.TestCase):
    def draft(self):
        draft = CharacterDraft(name='Lucien', hair_color=HAIR_COLORS[3][1])
        for _ in range(POINT_BUDGET):
            draft.adjust('strength', 1)
        return draft

    def test_points_can_all_go_into_any_single_stat(self):
        for target in STAT_KEYS:
            draft = CharacterDraft(name='Lucien')
            for _ in range(POINT_BUDGET):
                self.assertTrue(draft.adjust(target, 1))
            hero = draft.build()
            for stat in STAT_KEYS:
                self.assertEqual(getattr(hero, stat), BASE_STAT + (POINT_BUDGET if stat == target else 0))
            self.assertEqual(draft.remaining, 0)

    def test_budget_cannot_be_exceeded_and_points_can_be_reassigned(self):
        draft = self.draft()
        self.assertFalse(draft.adjust('magic', 1))
        self.assertTrue(draft.adjust('strength', -1))
        self.assertEqual(draft.remaining, 1)
        self.assertTrue(draft.adjust('magic', 1))
        hero = draft.build()
        self.assertEqual((hero.strength, hero.magic), (29, 11))

    def test_cannot_go_below_base_or_adjust_an_unknown_stat(self):
        draft = CharacterDraft()
        self.assertFalse(draft.adjust('defense', -1))
        self.assertFalse(draft.adjust('unknown', 1))
        self.assertFalse(draft.adjust('strength', 20))
        self.assertFalse(draft.adjust('strength', True))
        self.assertEqual(draft.remaining, POINT_BUDGET)

    def test_unspent_points_and_invalid_names_block_creation(self):
        with self.assertRaises(ValueError):
            CharacterDraft(name='Lucien').build()
        draft = self.draft()
        for name in ('', 'Ab', 'Lucien12', 'L' * 19):
            draft.name = name
            with self.assertRaises(ValueError):
                draft.build()

    def test_mutated_or_malformed_draft_is_revalidated(self):
        for bad in (
            {'strength': 21, 'magic': 0, 'defense': 0, 'resistance': 0},
            {'strength': 21, 'magic': -1, 'defense': 0, 'resistance': 0},
            {'strength': 20},
            {'strength': 20.0, 'magic': 0, 'defense': 0, 'resistance': 0},
        ):
            draft = CharacterDraft(name='Lucien', points=bad)
            with self.assertRaises(ValueError):
                draft.build()
        for color in ((-1, 0, 0), (256, 0, 0), (1, 2), (True, 0, 0), [1, 2, 3]):
            draft = self.draft()
            draft.hair_color = color
            with self.assertRaises(ValueError):
                draft.build()

    def test_reset_preserves_identity_and_restores_full_budget(self):
        draft = self.draft()
        draft.reset_points()
        self.assertEqual(draft.remaining, POINT_BUDGET)
        self.assertEqual(draft.name, 'Lucien')
        self.assertEqual(draft.hair_color, HAIR_COLORS[3][1])
        self.assertTrue(all(draft.value(stat) == BASE_STAT for stat in STAT_KEYS))

    def test_custom_character_is_retained_across_maps_and_battles(self):
        draft = self.draft()
        session = Session()
        session.start(prologue=False, draft=draft)
        self.assertEqual(session.hero.name, 'Lucien')
        self.assertEqual((session.hero.strength, session.hero.magic), (30, 10))
        self.assertEqual(session.hair_color, HAIR_COLORS[3][1])
        session.travel('road')
        session.interact_object('wolf')
        session.choose_dialogue('road')
        self.assertIs(session.battle.hero, session.hero)
        self.assertEqual(session.hair_color, draft.hair_color)
        draft.reset_points()
        draft.hair_color = HAIR_COLORS[0][1]
        self.assertEqual(session.hero.strength, 30)
        self.assertEqual(session.hair_color, HAIR_COLORS[3][1])

    def test_invalid_creation_does_not_replace_the_current_session(self):
        session = Session()
        hero = session.hero
        with self.assertRaises(ValueError):
            session.start(draft=CharacterDraft())
        self.assertIs(session.hero, hero)
        self.assertEqual(session.mode, 'title')

    def test_palette_contains_eight_distinct_valid_colors(self):
        self.assertEqual(len(HAIR_COLORS), 8)
        self.assertEqual(len({color for _, color in HAIR_COLORS}), 8)
        for _, color in HAIR_COLORS:
            draft = self.draft()
            draft.hair_color = color
            draft.build()
