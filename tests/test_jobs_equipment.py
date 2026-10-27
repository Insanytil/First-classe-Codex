import unittest

from poo.characters import Hero, Monster
from poo.characters.jobs import JOBS, SKILLS, WEAPONS
from poo.game.battle import Battle
from poo.graphics.character import CharacterDraft
from poo.graphics.state import Session


def settle(battle):
    for _ in range(200):
        battle.update(.1)
        if battle.motion is None:
            return
    raise AssertionError('Tour bloqué')


def hero(class_id):
    return Hero('Lucien', strength=15, magic=15, defense=15, resistance=15, class_id=class_id)


class JobsEquipmentTests(unittest.TestCase):
    def test_each_job_builds_with_its_starter_and_three_unique_skills(self):
        for identifier, job in JOBS.items():
            draft = CharacterDraft(name='Lucien', class_id=identifier, points={'strength': 5, 'magic': 5, 'defense': 5, 'resistance': 5})
            player = draft.build()
            self.assertEqual(player.weapon_id, job.starter)
            self.assertEqual(player.weapons, {job.starter})
            self.assertEqual(player.strength, 15)
            self.assertEqual(len(set(job.skills)), 3)
            self.assertTrue(all(skill in SKILLS for skill in job.skills))
        with self.assertRaises(ValueError):
            hero('unknown')

    def test_purchase_equip_and_bonuses_do_not_accumulate(self):
        for identifier in JOBS:
            player = hero(identifier)
            upgrade = next(w for w in WEAPONS.values() if w.job == identifier and w.price)
            self.assertFalse(player.buy_weapon(upgrade.id))
            player.gil = 100
            self.assertTrue(player.buy_weapon(upgrade.id))
            self.assertEqual(player.gil, 10)
            self.assertFalse(player.buy_weapon(upgrade.id))
            self.assertTrue(player.equip(upgrade.id))
            self.assertTrue(player.equip(upgrade.id))
            self.assertEqual(player.strength, 15 + upgrade.strength)
            self.assertEqual(player.magic, 15 + upgrade.magic)
            self.assertTrue(player.equip(player.job.starter))
            self.assertEqual((player.strength, player.magic), (15, 15))
            self.assertFalse(player.equip('missing'))
            foreign = next(w for w in WEAPONS.values() if w.job != identifier)
            player.weapons.add(foreign.id)
            self.assertFalse(player.equip(foreign.id))

    def test_skill_costs_and_contact_are_applied_once(self):
        for identifier in JOBS:
            for key in ('2', '5', '6'):
                player = hero(identifier)
                player.take_damage(300)
                enemies = [Monster('Flan', hp=5000), Monster('Loup', hp=5000)]
                battle = Battle(player, enemies)
                skill_id = next(s for k, _, s in battle.actions if k == key)
                self.assertTrue(battle.choose(key))
                self.assertFalse(battle.choose(key))
                battle.update(.01)
                self.assertEqual(player.mp, 60)
                settle(battle)
                self.assertEqual(player.mp, 60 - SKILLS[skill_id].cost)
                if SKILLS[skill_id].effect == 'heal':
                    self.assertGreater(player.hp, 300)
                elif SKILLS[skill_id].effect != 'shield':
                    self.assertLess(enemies[0].hp, 5000)
                if SKILLS[skill_id].effect.endswith('_all'):
                    self.assertLess(enemies[1].hp, 5000)

    def test_poison_ticks_for_three_turns_then_expires(self):
        player = hero('ranger')
        enemy = Monster('Flan', hp=5000)
        battle = Battle(player, [enemy])
        battle.choose('5')
        settle(battle)
        self.assertEqual(battle.poison[0], 2)
        for _ in range(2):
            battle.choose('4')
            settle(battle)
        self.assertFalse(battle.poison)
        self.assertEqual(sum('Poison ·' in line for line in battle.log), 3)

    def test_givre_reduces_the_next_enemy_hit(self):
        player = hero('mage')
        enemy = Monster('Flan', hp=5000, strength=20)
        battle = Battle(player, [enemy])
        battle.choose('5')
        settle(battle)
        self.assertEqual(player.hp, 600 - round((200 - 75) * .65))
        self.assertFalse(battle.chilled)

    def test_shield_absorbs_damage_and_does_not_stack(self):
        player = hero('paladin')
        enemy = Monster('Flan', hp=5000, strength=10)
        battle = Battle(player, [enemy])
        battle.choose('6')
        settle(battle)
        self.assertEqual(player.hp, 600)
        self.assertEqual(player.shield, 190 - 25)
        player.take_damage(200)
        self.assertEqual(player.shield, 0)
        self.assertEqual(player.hp, 565)

    def test_cooldown_blocks_without_consuming_turn_and_basic_attack_restores_mp(self):
        player = hero('mage')
        battle = Battle(player, [Monster('Flan', hp=5000)])
        battle.choose('6')
        settle(battle)
        turn = battle.turn
        self.assertFalse(battle.choose('6'))
        self.assertEqual(battle.turn, turn)
        self.assertIsNone(battle.motion)
        self.assertTrue(battle.choose('1'))
        settle(battle)
        self.assertEqual(player.mp, 50)
        self.assertFalse(battle.choose('6'))
        battle.choose('4')
        settle(battle)
        self.assertTrue(battle.choose('6'))

    def test_out_of_mana_and_unknown_actions_are_rejected(self):
        player = hero('paladin')
        player.mp = 0
        battle = Battle(player, [Monster('Flan')])
        for key in ('2', '5', '6', 'unknown'):
            self.assertFalse(battle.choose(key))
        self.assertEqual(battle.turn, 1)
        self.assertIsNone(battle.motion)

    def test_inventory_is_world_only_and_shopping_requires_merchant(self):
        session = Session()
        session.mode = 'world'
        session.hero.gil = 100
        self.assertTrue(session.open_inventory())
        self.assertFalse(session.buy_weapon('dawn_sword'))
        session.close_inventory()
        session.interact_object('merchant')
        session.choose_dialogue('armory')
        self.assertTrue(session.inventory_shop)
        self.assertTrue(session.buy_weapon('dawn_sword'))
        self.assertTrue(session.equip_weapon('dawn_sword'))
        session.close_inventory()
        session.travel('road')
        self.assertEqual(session.hero.weapon_id, 'dawn_sword')
        session.interact_object('wolf')
        session.choose_dialogue('road')
        self.assertFalse(session.open_inventory())
        self.assertFalse(session.equip_weapon('iron_sword'))
        self.assertIs(session.battle.hero, session.hero)

    def test_poison_victory_rewards_once_and_clears_defense(self):
        player = hero('ranger')
        enemy = Monster('Flan', hp=500, xp=40, gil=30)
        battle = Battle(player, [enemy])
        battle.poison[0] = 1
        enemy.take_damage(490)
        battle.choose('4')
        settle(battle)
        self.assertTrue(battle.result)
        self.assertEqual(player.gil, 30)
        self.assertFalse(player.defending)
        battle.update(10)
        self.assertEqual(player.gil, 30)
