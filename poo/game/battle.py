from poo.characters import Hero, Monster
from poo.game.creation import ask_int
from poo.game.display import console, hero_sheet, monster_line, display_combat
from poo.game.animation import (
    attack_animation,
    fireball_animation,
    potion_animation,
    monster_attack_animation,
    hero_death_animation,
    monster_death_animation,
)
def show_all_monster_name(monsters) -> str:
    monster_dict = {}
    return_str = ""
    for monster in monsters:
        if monster.name in monster_dict:
            monster_dict[monster.name] += 1
        else:
            monster_dict[monster.name] = 1

    for monster_name, number in monster_dict.items():
        return_str += f"{monster_name} x{number} "
    return return_str


def at_least_one_monster_alive(monsters : list[Monster]) -> bool:
    return any(monster.is_alive for monster in monsters)

def fights(hero : Hero, monsters: list[Monster]) -> bool:
    print(f"Un combat se lance contre : {show_all_monster_name(monsters)}")
    turn = 1
    total_dmg_inflicted = 0
    total_dmg_taken = 0
    total_heal = 0

    while hero.is_alive and at_least_one_monster_alive(monsters):
        print(f"------- Tour {turn} ---------")
        display_combat(hero, monsters)
        return True
    return False


def reward(hero: Hero, monster: Monster) -> None:
    print(f"Butin: +{monster.xp} points d'expérience, + {monster.gil} gils")
    if hero.gain_xp(monster.xp) > 0:
        print(f"{hero.name} passe au niveau {hero.level}")
def fight(hero : Hero, monster: Monster) -> bool:
    print(f"Un combat se lance contre : {monster.name}")
    turn = 1
    total_dmg_inflicted = 0
    total_dmg_taken = 0
    total_heal = 0
    while hero.is_alive and monster.is_alive:
        print(f"------- Tour {turn} ---------")
        console.print(hero_sheet(hero))
        console.print(monster_line(monster))
        hero_action = ask_int(f"1. Attaquer  2. Feu (8 PM)  3. Boire une Potion ({hero.potions})", 1, 3)
        match hero_action:
            case 1:
                    attack_animation(hero.name, monster.name)
                    dmg_dealt = hero.attack(target=monster)
                    total_dmg_inflicted += dmg_dealt
                    print(f"{hero.name} attaque {monster.name} : {dmg_dealt} dégats.")
                    console.print(monster_line(monster))
                    if monster.is_alive:
                        monster_attack_animation(monster.name, hero.name)
                        dmg_taken = monster.attack(target=hero)
                        total_dmg_taken += dmg_taken
                        print(f"{monster.name} attaque {hero.name} : {dmg_taken} dégats.")
                        turn += 1

            case 2:
                    if hero.can_cast_fire:
                        fireball_animation(hero.name, monster.name)
                        dmg_dealt = hero.cast_fire(target=monster)
                        total_dmg_inflicted += dmg_dealt
                        print(f"{hero.name} lance une boule de feu sur {monster.name} : {dmg_dealt} dégats magique.")
                        if monster.is_alive:
                            monster_attack_animation(monster.name, hero.name)
                            dmg_taken = monster.attack(target=hero)
                            total_dmg_taken += dmg_taken
                            print(f"{monster.name} attaque {hero.name} : {dmg_taken} dégats.")
                            turn += 1
                    else:
                        print("Vous n'avez pas assez de MP pour lancer ce sort...")
            case 3:
                    if hero.can_drink_potion:
                        potion_animation(hero.name)
                        heal = hero.drink_potion()
                        total_heal += heal
                        print(f"{hero.name} bois une potion et récupère {heal} point(s) de vie")
                        if monster.is_alive:
                            monster_attack_animation(monster.name, hero.name)
                            dmg_taken = monster.attack(target=hero)
                            total_dmg_taken += dmg_taken
                            print(f"{monster.name} en profite pour se déplacer dans un angle mort et attaque {hero.name} : {dmg_taken} dégats.")
                            turn += 1
                    else:
                        print("Vous n'avez plus de potions en inventaire...")



    if monster.is_alive:
        hero_death_animation(hero.name)
        return False
    else:
        monster_death_animation(monster.name)
        print(f"{hero.name} remporte le combat en {turn} tours.\n"
              f"Dégats infligés : {total_dmg_inflicted}\n"
              f"PV soignées : {total_heal}\n"
              f"Dégats reçus : {total_dmg_taken}\n"

        )
        reward(hero, monster)
        return True