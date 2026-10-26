from poo.game.display import console, banner, hero_sheet
from poo.characters import Hero, Monster
from poo.game.creation import create_hero
from poo.game.battle import fight, fights
from poo.game.animation import (
    dalmasca_arrival_animation,
    dalmasca_success_animation
)
def prologue() -> None:
    """Nibelheim, il y a cinq ans : un duel perdu d'avance."""
    console.print("[italic]Nibelheim, il y a cinq ans…[/]\n")
    cloud = Hero("Cloud", strength=20, magic=12, defense=15, resistance=13)
    sephiroth = Monster("Sephiroth", strength=50, magic=60, defense=99, resistance=99)
    while cloud.is_alive and sephiroth.is_alive:
        console.print(hero_sheet(cloud))
        console.print(hero_sheet(sephiroth))
        damage = cloud.attack(sephiroth)
        console.print(f"Cloud frappe Sephiroth : [bold]{damage}[/] dégât(s).")
        damage = sephiroth.attack(cloud)
        console.print(f"Sephiroth frappe Cloud : [bold red]{damage}[/] dégâts.\n")
    console.print(hero_sheet(cloud))
    console.print("\nSephiroth : « Tu n'es qu'une marionnette. »")
    console.print("[italic]Un jour, tu reviendras. Et cette fois, tu seras prêt.[/]")

def flan() -> Monster:
    return Monster(
        name="Flandwich",strength=14, magic=1, defense=18, resistance=4, level=1, xp=300, gil=50, mp=0, hp=450)

def wolf() -> Monster:
    return Monster(name="WolferInn",hp=380, mp=0, strength=16, magic=1, defense=6,resistance=8, level=2, xp=400, gil=50)
def run():
    console.print(banner())
    prologue()

    hero = create_hero()
    console.print(hero_sheet(hero))
    input("Appuyez sur Entrée pour continuer...")
    dalmasca_arrival_animation(hero.name)
    input("Appuyez sur Entrée pour continuer...")
    console.clear()
    fights(hero, [flan(), wolf(), flan()])
    fights(hero, [flan()])
    #fight(hero, flan())
    print(f"{hero.name} se repose après ce combat acharné et récupère {hero.rest()} points de vie ")
    input("Appuyez sur Entrée pour continuer...")
    console.clear()
    #fight(hero, wolf())
    print(f"{hero.name} se repose après ce combat acharné et récupère {hero.rest()} points de vie ")
    input("Appuyez sur Entrée pour continuer...")
    console.clear()
    #fight(hero, flan())
    print(f"{hero.name} se repose après ce combat acharné et récupère {hero.rest()} points de vie ")
    input("Appuyez sur Entrée pour continuer...")
    dalmasca_success_animation(hero.name)