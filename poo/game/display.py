from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

from poo.characters import Hero, Monster

console = Console()

def banner() -> Panel:
    title = Text("FINAL CLASSE", style="bold dark_violet", justify="center")
    return Panel(title, subtitle="un mini-RPG pour apprendre la POO", border_style="italic dark_red")


def bar(current: int, maximum: int, width: int = 10) -> str:
    """Une jauge en couleur : verte, puis jaune sous la moitié, rouge sous le quart."""
    ratio = current / maximum
    filled = round(width * ratio)
    color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
    return f"[{color}]{'█' * filled}[/][dim]{'░' * (width - filled)}[/]"


def hero_sheet(char: Hero | Monster) -> str:
    """La fiche d'un héros : son nom, ses PV, ses PM et ses statistiques."""
    return (
        f"[bold]{char.name}[/]\n"
        f"  PV {char.hp:>4}/{char.max_hp:<4} {bar(char.hp, char.max_hp)}\n"
        f"  PM {char.mp:>4}/{char.max_mp:<4} {bar(char.mp, char.max_mp)}\n"
        f"  FOR {char.strength}  MAG {char.magic}  DÉF {char.defense}  RÉS {char.resistance}"
    )

def monster_line(monster: Monster| Hero) -> str:
    """ La fiche du monstre en question, son nom, pv"""
    return (
        f"[bold]{monster.name}[/]\n"
        f"  PV {monster.hp:>4}/{monster.max_hp:<4} {bar(monster.hp, monster.max_hp)}\n"
    )

def monster_panel(monster: Monster) -> Panel:
    """Crée un panneau pour un monstre."""
    return Panel(
        monster_line(monster),
        title=f"[bold red]{monster.name}[/]",
        border_style="red",
        expand=True,
    )

def display_all_monster(monsters: list[Monster]) -> None:
    panels = [monster_panel(monster) for monster in monsters]

    console.print(
        Panel(
            Columns(panels, equal=True, expand=True),
            title="[bold red]ENNEMIS[/]",
            border_style="bright_red",
        )
    )

def hero_panel(hero: Hero) -> Panel:
    """Crée un panneau centré pour le héros."""
    return Panel(
        Align.center(hero_sheet(hero)),
        title=f"[bold cyan]{hero.name}[/]",
        border_style="cyan",
        expand=False,
        width=60,
    )

def display_combat(hero: Hero, monsters: list[Monster]) -> None:
    """Affiche le héros centré au-dessus des monstres."""

    hero_display = Align.center(hero_panel(hero))

    monster_panels = [
        monster_panel(monster)
        for monster in monsters
    ]

    monsters_display = Align.center(
        Columns(
            monster_panels,
            equal=True,
            expand=False,
        )
    )

    console.print(
        Group(
            hero_display,
            monsters_display,
        )
    )