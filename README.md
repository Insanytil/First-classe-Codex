# Final Classe — Les braises du matin

> Nouvelle version : [JRPG](JRPG/README.md) — projet piloté par le [cahier des charges](CAHIER_DES_CHARGES_RPG_PYGAME_CODEX.md).
> La suite de ce README décrit le prototype historique `poo/`, conservé séparément.

Un premier chapitre de RPG en Python avec une interface graphique Pygame-ce : environnements peints en perspective, sprites illustrés, dialogues, quêtes et combats animés.

## Lancer le jeu

```bash
uv sync
uv run python -m poo
```

Le jeu se lance dans une fenêtre Pygame. Tout se passe dans la fenêtre : écran titre, nom du héros, prologue, exploration, dialogues et combats. Aucune question n'est posée dans le terminal.

Le projet déclare Python 3.15 ou supérieur et dépend de `pygame-ce`. L'installation du paquet `pygame-ce` fournit l'import `pygame`.

Pour commencer directement au camp, sans le prologue :

```bash
uv run python -m poo --quick
```

La fenêtre s'adapte à la taille du bureau au lancement. Elle peut être redimensionnée ; le jeu conserve son rapport d'aspect et ses coordonnées logiques de 1280 × 800. F11 bascule le plein écran.

## Créateur de personnage

Avant le prologue, créez votre héros dans la fenêtre :

- **Classe** : Guerrier, Mage, Rôdeur ou Paladin, avec tenue, arme initiale et trois compétences propres. Changer de classe conserve les points déjà attribués.
- **Nom** : 3 à 18 lettres. Cliquez dans le champ pour le modifier ; Ctrl+A sélectionne le nom entier.
- **Cheveux** : huit couleurs (blond, châtain, brun, roux, argent, noir, bleu, violet), avec un aperçu animé que vous pouvez tourner.
- **Caractéristiques** : Force, Magie, Défense et Résistance commencent à 10. Répartissez **20 points** comme vous le souhaitez, y compris tous dans la même statistique.
- **Boutons +/−** : ajoutez ou retirez les points attribués. Le budget ne peut pas être dépassé et aucune statistique ne peut descendre sous 10.
- **Réinitialiser les points** : recommencez la répartition sans effacer le nom ni la couleur.

Le bouton de départ s'active lorsque les 20 points sont répartis ; un nom invalide empêche aussi le lancement et affiche une erreur. TAB bascule entre le nom et les caractéristiques ; dans les caractéristiques, Haut/Bas sélectionne la ligne et Gauche/Droite ajuste sa valeur. La couleur choisie suit le héros sur les cartes, dans le HUD et pendant les combats. Cloud, dans le prologue, conserve son apparence propre.

## Commandes

| Commande | Action |
| --- | --- |
| Flèches, ZQSD ou WASD | Déplacement continu |
| E, Entrée ou Espace | Interagir avec un personnage, un objet ou un passage proche |
| Souris | Boutons, choix de dialogue et sélection des adversaires |
| 1 à 6, ou pavé numérique | Attaque, compétence principale, potion, garde et deux autres compétences |
| I | Ouvrir / fermer l’inventaire en exploration |
| TAB ou flèches | Changer de cible pendant un combat |
| Entrée | Continuer un dialogue, une cinématique ou le résultat du combat |
| Échap | Fermer un dialogue ou ouvrir/reprendre la pause |
| F11 | Plein écran / fenêtre |

Les touches de combat acceptent aussi les symboles `&`, `é`, `"`, `'`, `(`, `-` des six premières touches d'un clavier AZERTY. Les dialogues à plusieurs choix se sélectionnent à la souris ou avec 1/2/3 ; Entrée valide le premier choix.

Les déplacements utilisent les événements d'appui et de relâchement des touches. La vitesse dépend du temps écoulé, les diagonales sont normalisées, et les collisions sont calculées sur les pieds du personnage avec des sous-pas. La perte de focus efface les touches maintenues et met le jeu en pause.

## Prologue et direction visuelle

Le prologue utilise des dessins dédiés de Cloud, Sephiroth et du village de Nibelheim en flammes. Cloud porte sa grande épée et Sephiroth apparaît sous la forme d'un démon ailé majestueux. La confrontation se déroule en six tableaux, avec une attaque de Cloud et une contre-attaque de Sephiroth pendant une séquence de 3,8 secondes. Les commandes restent actives ; la pause suspend aussi la chorégraphie. Le personnage créé par le joueur garde ses propres statistiques et son apparence.

La même finition illustrée est appliquée au campement, à la route, au pont, aux ruines, à la porte et au fond des combats. Les personnages restent des couches séparées et les collisions sont indépendantes des peintures. La porte possède un visuel fermé et un visuel ouvert après la victoire.

Aperçus des ressources : [prologue](assets/previews/prologue.png), [poses d'attaque](assets/previews/attack-poses.png), [environnements](assets/previews/environments.png).

## Le premier chapitre

```text
                                     Ruines
                                       |
Campement --- Caravanes --- Vieux pont --- Porte de l'Est
```

- **Campement** : Mira donne les objectifs. Le feu restaure gratuitement PV et PM ; le marchand vend des potions à 25 gils.
- **Route des caravanes** : approchez le loup ou le voyageur pour lancer le combat. Aidez ensuite le marchand (+2 potions) ou inspectez les traces (+40 gils).
- **Vieux pont** : traversez la rivière, lisez la stèle et empruntez le passage au nord pour atteindre les ruines.
- **Ruines** : approchez le sceau. Deux flans protègent le sanctuaire ; la victoire donne le sceau et une potion.
- **Porte de l'Est** : après les deux objectifs, affrontez la Sentinelle. Elle charge son arme un tour avant sa frappe lourde : utilisez Défendre.
- **Épilogue** après la victoire ; écran de défaite si le héros tombe.

Pour changer de carte, approchez-vous d'une flèche au bord du décor puis appuyez sur E. Les changements de carte conservent l'inventaire et la progression. Les ennemis des zones libérées disparaissent, et leurs récompenses ne peuvent pas être récupérées plusieurs fois.

Revenez au camp entre les combats pour restaurer vos PV et PM. Le héros graphique commence au niveau 1 avec 600 PV, 60 PM et trois potions. Son nom, sa couleur de cheveux et ses caractéristiques sont définis dans le créateur de personnage.

## Combats et rendu

Les combats réutilisent les classes `Hero`, `Monster`, `Gatekeeper` et une simulation de combat indépendante du rendu. Les commandes sont disponibles quand le héros peut agir. Le coup d’épée, le coup de patte du loup et le bond du slime possèdent chacun huit poses dédiées. Le slime se comprime, saute selon une trajectoire en cloche puis s’écrase à l’atterrissage. Les dégâts sont appliqués une seule fois au contact ; le recul et le retour en position terminent ensuite le geste. Feu, soins, garde et nombres de dégâts sont aussi animés. Les ennemis encore vivants ripostent l'un après l'autre. Le boss annonce sa frappe lourde.

Les cinq régions de Dalmasca et le décor des combats utilisent des peintures détaillées dans `assets/maps/`. Les personnages et leurs poses sont chargés depuis des planches PNG haute résolution. Le style est illustré, avec des contours doux et un redimensionnement lissé. Les fichiers du corps et des cheveux sont séparés pour conserver la personnalisation. Les images sont chargées et découpées une fois, puis mises en cache. Aucun téléchargement supplémentaire n’est nécessaire pour jouer.

Les planches originales générées, les prompts et un aperçu des ressources sont documentés dans [assets/README.md](assets/README.md). Les menus et dialogues sont graphiques, avec un journal de quête et un HUD. La boucle vise 60 FPS. Cette première version n'a pas encore de musique ni de sauvegarde.

## Classes et équipement

| Classe | Arme | Compétences |
| --- | --- | --- |
| Guerrier | Épée | Frappe puissante, Tourbillon (zone), Second souffle (soin) |
| Mage | Bâton | Feu, Givre (riposte réduite), Tempête (zone) |
| Rôdeur | Arc | Tir précis (perce-armure), Flèche venimeuse, Salve (zone) |
| Paladin | Marteau | Châtiment, Lumière curative, Égide (bouclier) |

Les compétences coûtent des PM et certaines ont un délai de récupération en tours. Survolez les boutons pour lire leur effet. L’attaque de base restaure 4 PM ; les compétences se résolvent au contact de leur animation. Poison dure trois fins de tour, Givre réduit la prochaine riposte de 35 %, Égide absorbe des dégâts sans se cumuler. Les altérations et le bouclier sont propres au combat.

Appuyez sur **I** dans le monde pour voir les huit armes, leurs bonus, celles que vous possédez et celle équipée. Chaque classe commence avec une arme ; Oren vend une amélioration à 90 gils via **Voir les armes**. L’achat ajoute l’arme au sac ; cliquez ensuite sur **Équiper**. Les armes d’autres classes restent visibles mais ne sont pas équipables. Les bonus changent les statistiques utilisées en combat, sans modifier les points investis. L’inventaire est fermé pendant les combats et les dialogues.

Chaque classe possède seize poses de marche et huit poses d’action, un calque de cheveux recolorable et une arme PNG indépendante. Les repères de main et de poignée permettent de suivre le geste avec les différentes armes d’une même famille. Les tirs, traits magiques et frappes utilisent des animations distinctes. Voir les [prompts des classes](assets/CLASSES_PROMPTS.md) et l’[aperçu](assets/previews/classes.png).

## Organisation

- `poo/characters` : personnages et règles métier.
- `poo/game` : simulation des combats, ennemis du chapitre, progression, commerce et repos.
- `poo/graphics/character.py` : brouillon du personnage, palette et validation du budget.
- `poo/graphics/state.py` : état graphique, interactions et progression, sans dépendance à Pygame.
- `poo/graphics/world.py` : cartes, passages et collisions, sans dépendance à Pygame.
- `assets/` : cartes peintes, planches d’animation, manifeste, sources et aperçus.
- `poo/game/prologue.py` : tableaux et durée de la confrontation.
- `poo/graphics/animation.py` : trajectoires, anticipation et récupération des attaques.
- `poo/graphics/resources.py` : chemins et description des planches, sans dépendance à Pygame.
- `poo/graphics/art.py` : chargement, découpage, coloration et cache des images.
- `poo/graphics/view.py` : décors, interface, dialogues et effets visuels.
- `poo/graphics/app.py` : événements clavier/souris, boucle, fenêtre et redimensionnement.

## Vérifier

```bash
uv run python -m unittest discover -s tests -v
```

Les tests vérifient notamment le contact des attaques, les trajectoires, le timing du prologue, les fichiers PNG et leurs dimensions, le manifeste, la création de personnage, le chapitre complet, les combats, les récompenses, le repos, les achats, l'accessibilité des objectifs et des passages, les collisions, la normalisation des diagonales et l'arrêt du déplacement sans direction maintenue. Ils n'ouvrent pas de fenêtre.

Le rendu Pygame reste à valider sur la machine de jeu ; la syntaxe et les tests de logique peuvent être vérifiés indépendamment de son installation graphique.
