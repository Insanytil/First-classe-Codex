import unittest

from poo.characters import Hero, Monster
from poo.characters.boss import Gatekeeper
from poo.game.battle import Battle


def settle(battle):
    for _ in range(100):
        battle.update(.1)
        if battle.motion is None:
            return
    raise AssertionError('Le combat reste bloqué')


class BattleTests(unittest.TestCase):
    def test_damage_occurs_after_animation_and_action_cannot_be_spammed(self):
        hero = Hero('Lucien', strength=100)
        monster = Monster('Flan', hp=20, xp=100, gil=10)
        battle = Battle(hero, [monster])
        self.assertTrue(battle.choose('1'))
        self.assertFalse(battle.choose('1'))
        battle.update(.1)
        self.assertEqual(monster.hp, 20)
        settle(battle)
        self.assertTrue(battle.result)
        self.assertEqual((hero.gil, hero.level), (10, 2))
        for _ in range(20):
            battle.update(1)
        self.assertEqual(hero.gil, 10)

    def test_defense_lasts_until_enemy_animations_finish(self):
        hero = Hero('Lucien', defense=10)
        boss = Gatekeeper()
        boss.charged = True
        battle = Battle(hero, [boss])
        battle.choose('4')
        self.assertTrue(hero.defending)
        settle(battle)
        self.assertEqual(hero.hp, 600 - (24 * 18 - 50) // 2)
        self.assertFalse(hero.defending)
        self.assertEqual(battle.turn, 2)

    def test_unavailable_action_does_not_consume_turn(self):
        hero = Hero('Lucien', potions=0)
        hero.mp = 0
        battle = Battle(hero, [Monster('Flan')])
        self.assertFalse(battle.choose('2'))
        self.assertFalse(battle.choose('3'))
        self.assertIsNone(battle.motion)
        self.assertEqual(battle.turn, 1)

    def test_boss_telegraphs_and_defense_reduces_damage(self):
        boss = Gatekeeper()
        hero = Hero('Lucien', defense=10)
        self.assertEqual(boss.attack(hero), 0)
        self.assertTrue(boss.charged)
        hero.defending = True
        self.assertEqual(boss.attack(hero), (24 * 18 - 50) // 2)
        self.assertFalse(boss.charged)
