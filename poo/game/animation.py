
import time

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()


def animate_frames(
    title: str,
    frames: list[str],
    color: str = "bright_yellow",
    delay: float = 0.12,
    subtitle: str = "",
) -> None:
    """Joue une animation dans un panneau Rich actualisé en direct."""

    if not frames:
        return

    def render_frame(frame: str) -> Panel:
        content = Text(frame, style=color, justify="center")

        elements = [Align.center(content)]

        if subtitle:
            elements.append(
                Align.center(Text(subtitle, style="dim italic"))
            )

        return Panel(
            Group(*elements),
            title=f"[bold {color}]{title}[/]",
            border_style=color,
            padding=(1, 3),
            expand=False,
        )

    with Live(
        render_frame(frames[0]),
        console=console,
        refresh_per_second=20,
        transient=True,
    ) as live:
        for frame in frames:
            live.update(render_frame(frame))
            time.sleep(delay)

    console.print()


def attack_animation(attacker_name: str, target_name: str) -> None:
    """Animation d'une attaque physique."""

    animate_frames(
        f"⚔ {attacker_name} attaque !",
        [
            "          ⚔",
            "         ⚔ ⚔",
            "       💨 ⚔",
            "     💨💨 ⚔",
            "   💨💨💨 ⚔",
            "       ✴ 💥 ✴",
        ],
        color="bright_white",
        delay=0.12,
        subtitle=f"Cible : {target_name}",
    )

    console.print(
        f"[bold bright_red]⚔ {attacker_name} frappe "
        f"{target_name} ![/]\n"
    )


def fireball_animation(attacker_name: str, target_name: str) -> None:
    """Animation d'une boule de feu."""

    animate_frames(
        f"🔥 {attacker_name} incante un sort !",
        [
            "             ✨",
            "            🔥",
            "           🔥🔥",
            "          🔥🔥🔥",
            "        🔥🔥🔥🔥",
            "      🔥🔥🔥🔥🔥",
            "    🔥🔥🔥🔥🔥🔥",
            "          💥",
            "       💥🔥💥",
            "      ✴💥🔥💥✴",
        ],
        color="bright_red",
        delay=0.12,
        subtitle=f"Cible : {target_name}",
    )

    console.print(
        f"[bold bright_red]🔥 {target_name} est englouti "
        f"par les flammes ![/]\n"
    )


def potion_animation(consumer_name: str) -> None:
    """Animation de consommation d'une potion."""

    animate_frames(
        f"🧪 {consumer_name} utilise une potion",
        [
            "          🧪",
            "          🧪 ✨",
            "          🍷",
            "         🍷 ✨",
            "        🍷 ✨ ✨",
            "          💚",
            "        ✨💚✨",
            "      ✨💚💚💚✨",
            "    ✨💚💚💚💚💚✨",
        ],
        color="bright_green",
        delay=0.16,
        subtitle="Une énergie nouvelle envahit le héros...",
    )

    console.print(
        f"[bold bright_green]💚 {consumer_name} récupère "
        "des forces ![/]\n"
    )


def monster_attack_animation(
    monster_name: str,
    target_name: str,
) -> None:
    """Animation d'attaque d'un monstre."""

    animate_frames(
        f"👹 {monster_name} passe à l'attaque !",
        [
            "             👹",
            "           👹 💢",
            "         👹 💢 💢",
            "       👹 💨 💢",
            "          💨 💨",
            "        💥 👤 💥",
            "       ✴ 💥 👤 💥 ✴",
        ],
        color="bright_red",
        delay=0.13,
        subtitle=f"Cible : {target_name}",
    )

    console.print(
        f"[bold red]👹 {monster_name} attaque "
        f"{target_name} ![/]\n"
    )


def monster_death_animation(monster_name: str) -> None:
    """Animation de défaite d'un monstre."""

    animate_frames(
        f"💀 {monster_name} est vaincu !",
        [
            "           👹",
            "           👹 💢",
            "           👹 💫",
            "           🥴",
            "           💫",
            "           💀",
            "          💀 💨",
            "            .",
            "             ",
        ],
        color="bright_red",
        delay=0.2,
        subtitle="Le monstre ne peut plus combattre.",
    )

    console.print(
        f"[bold yellow]💀 {monster_name} s'écroule "
        "et ne bouge plus...[/]\n"
    )


def hero_death_animation(hero_name: str) -> None:
    """Animation de défaite du héros."""

    animate_frames(
        f"☠ {hero_name} est à bout de forces...",
        [
            "           🦸",
            "           🦸 💥",
            "           🦸 💫",
            "           🧎",
            "           🧎 💫",
            "           💤",
            "            .",
        ],
        color="bright_red",
        delay=0.25,
        subtitle="Le combat touche à sa fin...",
    )

    console.print(
        f"[bold bright_red]☠ {hero_name} est tombé "
        "au combat...[/]\n"
    )


def dalmasca_arrival_animation(hero_name: str) -> None:
    """Accueil du héros dans les plaines de Dalmasca."""

    animate_frames(
        "🌾 LES PLAINES DE DALMASCA",
        [
            "                 ☀",
            "           ☀           ☁",
            "       🌾       🌾       🌾",
            "    🌾     🌿       🌿     🌾",
            "  🌾    🌿       🚶       🌿    🌾",
            " 🌾   🌿       🚶          🌿   🌾",
            "🌾🌿🌾🌿🌾🌿🌾🌿🌾🌿🌾🌿🌾",
            "       🏜️ DALMASCA 🏜️",
        ],
        color="bright_yellow",
        delay=0.35,
        subtitle="Un vent chaud souffle sur les plaines...",
    )

    console.print(
        Panel(
            f"[bold bright_green]Bienvenue, {hero_name} ![/]\n\n"
            "[italic]Les plaines de Dalmasca s'étendent devant toi. "
            "Ton aventure commence ici.[/]",
            title="[bold yellow]Nouvelle zone[/]",
            border_style="bright_green",
            padding=(1, 3),
        )
    )


def dalmasca_success_animation(hero_name: str) -> None:
    """Célèbre la traversée réussie des plaines."""

    animate_frames(
        "🏆 TRAVERSÉE DE DALMASCA",
        [
            "🚶",
            "    🚶       🌾",
            "        🚶       🌿",
            "             🚶",
            "                 🚶       🏜️",
            "                     🏰",
            "                  ✨ 🏰 ✨",
            "              🌟 VICTOIRE 🌟",
            "          ✨🌟✨🌟✨🌟✨",
        ],
        color="bright_cyan",
        delay=0.3,
        subtitle=f"{hero_name} approche de sa destination.",
    )

    console.print(
        Panel(
            f"[bold bright_green]✓ {hero_name} a traversé "
            "les plaines de Dalmasca ![/]\n\n"
            "[bold yellow]🏆 Zone terminée[/]\n"
            "[italic]Une nouvelle étape de l'aventure "
            "est accomplie.[/]",
            title="[bold bright_cyan]Victoire[/]",
            border_style="bright_green",
            padding=(1, 3),
        )
    )
