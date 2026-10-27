import unittest

from poo.characters import Hero


class CharacterTests(unittest.TestCase):
    def test_add_potions(self):
        hero = Hero('Lucien')
        hero.add_potion(2)
        self.assertEqual(hero.potions, 5)
