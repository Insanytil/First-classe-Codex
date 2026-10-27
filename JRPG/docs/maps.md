# Cartes déclaratives

Sources : `src/JRPG/infrastructure/content/maps/*.json`, embarquées dans le paquet.
Le chargeur utilise `importlib.resources`, pas le répertoire de lancement.

Chaque document de version 1 contient `id`, `name`, `ground`, `collision`,
`objects` et `decorations`. Les lignes de grille doivent être rectangulaires ;
la grille de collision a exactement la même taille que le sol.

| Code de sol | Tuile |
| --- | --- |
| `.` | Herbe |
| `:` | Chemin |
| `~` | Eau |
| `#` | Mur |
| `_` | Dallage |
| `=` | Pont |

La collision est indépendante : `1` bloque, `0` autorise. Un arbre n'invente pas
sa collision à partir de son dessin : son tronc est déclaré dans cette grille.
Les coordonnées JSON `x`/`y` sont des colonnes/lignes de tuiles. Le domaine
convertit les positions d'apparition et les destinations au centre des cellules.

Les interactions déclarent un `id` global stable, `name`, `kind`, `x`, `y` et
éventuellement `solid` (vrai par défaut) :

- `npc` : `message` non vide.
- `chest` : `items` avec `id`/`quantity` et `gold` positif ou nul.
- `encounter` : liste non vide `enemies`, références au catalogue d'ennemis.
- `portal` : `solid: false` et `destination` avec `map`, `x`, `y`.

Les références d'items proviennent du catalogue injecté ; les identifiants ne
sont pas des chemins d'images ou de modules. Une destination doit accepter tout
le corps de collision du joueur. Les doublons globaux sont refusés car les
marqueurs de coffres et de rencontres utilisent ces identifiants.

Les décorations `tree`, `roof`, `pillar` déclarent leur cellule et `foreground`
(vrai par défaut). Les décors arrière précèdent les entités ; les surplombs sont
dessinés après. Ces choix n'introduisent pas de règle de collision graphique.

Après modification, exécuter les tests de contenu et de parcours :

```bash
uv run --no-sync pytest tests/integration/test_world_content.py tests/unit/test_world.py
```

Ce format concerne les définitions de carte. L'état du joueur et les sauvegardes
ne sont pas écrits dans ces fichiers.
