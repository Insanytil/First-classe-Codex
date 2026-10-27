# Phase 6 en cours — héros, monstres et monde vivant

La phase 5 est validée et la phase 6 autorisée par l'utilisateur. Celui-ci a
précisé préférer de véritables images de personnages et autorisé l'inspiration
des sprites, animations et prompts de `poo`, avec génération via imagegen.

## Livré dans ce lot

- Quatre personnages originaux peints : Ari, Lyra, Mira, Nox.
- Quatre sources imagegen conservées, quatre atlas normalisés transparents.
- Seize poses de marche et huit poses d'action par personnage.
- Affichage du chef de groupe en exploration, avec sa direction de marche.
- Affichage des quatre héros en combat, pose de contact synchronisée sur l'impact.
- Chargement paresseux, cache des images et tailles ; ressources indépendantes du cwd.
- Manifeste avec provenance, empreintes, rectangles source et ancrage aux pieds.
- Prompts complets dans `art/HERO_PROMPTS.md`, décision dans ADR 0007.

## Extension : monstres et cartes vivantes

Les sprites et attaques de loup et flan du prototype sont repris sans altérer les
fichiers sources. Les atlas de la sentinelle sont préparés pour le contenu futur.
Les PNJ, arbres, piliers, feu et décor de combat du prototype sont aussi embarqués.
Les captures `previews/poo-*.png` proviennent de l'exécution du rendu historique.

Trois nouvelles peintures imagegen couvrent Clairval, la forêt et les ruines,
avec guides JSON, prompts archivés et manifeste d'intégrité. Le recalage graphique
aligne la rivière, le pont et les passages sur la géométrie existante. Les arbres
et piliers sont triés en profondeur avec les personnages. Reflets, feuilles,
poses des PNJ, fumée, lucioles et braseros évoluent sans déplacement du joueur.
Voir [ADR 0008](adr/0008-monde-peint-vivant.md).

`tools/preview_living_world.py` capture les trois ambiances et les deux attaques.
Ouvrir `previews/animations.html` pour les consulter hors ligne, avec pause.

Les ressources sont dans `src/JRPG/infrastructure/content/art/`. Le script
`tools/prepare_hero_art.py` reproduit la sélection et le découpage sans réseau,
sans installer de bibliothèque, avec le Pygame déjà présent. Il isole chaque
silhouette pour exclure les fragments des poses voisines. La source imagegen
de Nox contient des poses supplémentaires ; huit poses d'action sont retenues.

## Vérifications

Windows, Python 3.15.2 et pygame-ce 2.5.8 existants. Aucune installation.

- 248 tests réussis, dont les contrôles des nouveaux assets et animations.
- Ruff lint et formatage ; mypy strict.
- Intégrité SHA-256 des sources et atlas, 24 cases non vides par héros.
- Véritable transparence alpha et marges empêchant les débordements de cases.
- Chargement à la demande, cache des tailles, correspondance pose/contact.
- Captures de la vraie boucle SDL dummy : combat et trois cartes.
- Captures animées des cartes et des attaques, exportées sans dépendance ajoutée.
- Empreintes des ressources reprises, dimensions d'atlas, poses et cache.
- Recalage sans trous, formats très larges/hauts, contact et trajectoires.
- Instantané complet de session identique avant/après rendu animé au repos.

La couverture de phase 5 n'est pas présentée comme une nouvelle mesure.
La fluidité et la qualité visuelle des mouvements nécessitent encore un essai
sur le bureau réel. Le build n'a pas été exécuté ; il doit embarquer `art/`.

Ce lot ne clôt pas la phase 6. Restent le contenu
final du MVP, le boss jouable, l'équilibrage, le son, les mesures de performance et la
distribution desktop. Aucun changement de format de sauvegarde dans ce lot.
