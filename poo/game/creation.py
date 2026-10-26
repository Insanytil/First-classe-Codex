from poo.characters import Hero


def ask_int(prompt, low, high) -> int:
    while True:
        try:
            num = int(input(prompt))
            if num < low or num > high:
                raise ValueError
            return num
        except ValueError:
            print("Please enter a number between {} and {}".format(low, high))

def ask_name() -> str:
    while True:
        name = input("What is your name? ")
        return name


def create_hero() -> Hero:
    stats = {"FOR": 10, "MAG": 10, "DEF": 10, "RES": 10}
    resting_value = 20
    hero_name = ask_name()
    print("Chaque statistique commence à 10. Répartissez 20 points.\n")

    for stat in ["FOR", "MAG", "DEF"]:
        if resting_value > 0:
            points_attribues = ask_int(f"{stat} (+0 à +{resting_value}) : ", 0, resting_value)
            stats[stat] += points_attribues
            resting_value -= points_attribues
        else:
            print(f"{stat} (+0) : Attribution automatique (0 point restant).")

    stats["RES"] += resting_value
    print(f"\nRES reçoit automatiquement les {resting_value} points restants.")

    print(f"Points finaux -> FOR: {stats['FOR']}, MAG: {stats['MAG']}, DEF: {stats['DEF']}, RES: {stats['RES']}\n")

    return Hero(
        name=hero_name,
        strength=stats["FOR"],
        magic=stats["MAG"],
        defense=stats["DEF"],
        resistance=stats["RES"],
        level=1
    )

