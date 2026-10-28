# Sauvegarder et reprendre une partie

Depuis `JRPG/`, lancer `uv run --no-sync jrpg`.

- **F5** ouvre Sauvegarder. Choisir un des trois emplacements puis Entrée.
- **F9** ouvre Charger. Choisir un emplacement occupé puis Entrée.
- **Tab** permet aussi d'accéder aux deux menus.

Ces commandes sont disponibles en exploration. Une sauvegarde conserve la
position, le groupe, ses ressources et équipements, les quêtes, le monde, les
stocks, la monnaie, le temps et la suite aléatoire. Le chargement remplace la
partie seulement après validation complète ; une erreur laisse le jeu courant.

Sous Windows, fichiers `slot-1.json`, `slot-2.json`, `slot-3.json` dans :

```text
%LOCALAPPDATA%\technobel-jrpg\saves
```

Sous Linux/macOS : `$XDG_DATA_HOME/technobel-jrpg/saves`, ou
`~/.local/share/technobel-jrpg/saves` si la variable n'est pas définie.
L'emplacement ne dépend pas du dossier depuis lequel le jeu est lancé.

Le format est JSON UTF-8, `version: 1`, `content_version: 3`.
Le contenu 2 ajoutait la Sentinelle ; le contenu 3 complète le catalogue du MVP.
À la demande de l'utilisateur, les anciennes sauvegardes de contenus 1 et 2 ne
sont pas migrées : leur chargement
affiche une erreur invitant à commencer une nouvelle partie. Aucun fichier ancien
n'est supprimé automatiquement ; F5 permet d'enregistrer la nouvelle partie.
Les définitions de contenu restent dans le paquet ; les sauvegardes référencent
leurs identifiants. L'écriture utilise un temporaire dans le même dossier puis
un remplacement atomique. Un fichier corrompu ou une version inconnue provoque
une erreur explicite, sans chargement partiel ni écrasement automatique.

La stratégie d'évolution et les garanties précises sont dans
[l'ADR 0006](adr/0006-progression-sauvegardes.md).
