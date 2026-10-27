"""Lancement du jeu Pygame."""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Final Classe · Les braises du matin")
    parser.add_argument("--quick", action="store_true", help="Passer le prologue")
    args = parser.parse_args()
    try:
        from poo.graphics.app import run

        run(quick=args.quick)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
    except KeyboardInterrupt:
        print("\nPartie interrompue. À bientôt !")


if __name__ == "__main__":
    main()
