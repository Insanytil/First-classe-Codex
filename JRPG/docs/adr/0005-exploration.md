# ADR 0005 — Monde en mémoire, contenu JSON et raccord au combat

Statut : acceptée par l’utilisateur avant la phase 5.
Référence : sections 2.7, 3, 5 et phase 4 du cahier des charges.

## Domaine et contenu

`MapDefinition`, `MapObject`, `Decoration` et `MapPosition` sont immuables.
Une carte contient sol, grille de collision indépendante, interactions et
surplombs. `World` protège position, déplacements et passages ; `WorldState`
conserve les identifiants des coffres ouverts et rencontres résolues ainsi que
les visites et événements du voyage. Une vue immutable est exposée pour chaque
collection. Il n'y a aucun import SDL, fichier, JSON ou horloge dans ces règles.

Trois cartes déclaratives sont embarquées dans
`src/JRPG/infrastructure/content/maps/` : village, forêt et ruines. Ce placement
permet un chargement installable via `importlib.resources`, sans dépendre du
répertoire courant ni d'un chemin vers le prototype. Le contenu reste séparé
physiquement et conceptuellement des instances et de leur état. Hatch embarque
les ressources du paquet ; le nouveau build reste à valider par l'utilisateur.

`JsonMapLoader` accepte uniquement les valeurs connues : version 1, grilles
rectangulaires, tuiles et types d'interaction énumérés, entiers, booléens, références
d'objets et d'ennemis déclarées. La construction du monde vérifie les identifiants
globaux, les destinations et les points d'apparition réellement praticables.
Les erreurs sont contextualisées ; aucun code du JSON n'est exécuté.
Le catalogue complet d'objets/compétences reste pour les phases de contenu.

## Déplacement et collisions

- Tuiles de 32 pixels, conformément au cahier des charges.
- Point de position au niveau des pieds ; boîte de collision carrée de rayon 7 px.
- Vitesse initiale 96 px/s, vecteur de direction normalisé (pas d'avantage diagonal).
- Déplacement par sous-pas de 8 px au maximum, avec résolution X puis Y pour
  permettre le glissement le long des obstacles sans traverser les murs.
- Terrain bloqué, eau, limites et objets solides utilisent les mêmes vérifications.
  Le pont est une tuile distincte et praticable. La décoration ne calcule pas la
  collision : les troncs et bâtiments sont explicitement déclarés dans la grille.
- Interaction manuelle à 48 px maximum, plus proche cible puis id pour les égalités.
  E/Entrée ne lance qu'une interaction. Une sortie ne se déclenche pas par simple
  présence sur sa destination, ce qui évite les allers-retours automatiques.

Le pathfinding n'est pas implémenté. Les tests emploient un BFS externe pour
prouver qu'un utilisateur peut atteindre les objets et les trois cartes.

## Application et transactions

`ExplorationSession` orchestre groupe, sac, monnaie, monde et fabrique de combat.
La fabrique est un port applicatif injecté ; son adaptateur réutilise les
compétences et définitions de démonstration existantes. Les héros, leurs PV/PM,
l'XP, le sac et la monnaie sont les mêmes objets avant et après le combat.
Les définitions d'ennemis créent de nouveaux combattants, jamais de nouveaux héros.

Un coffre prépare ses ajouts sur une copie du sac, puis verse objets et monnaie
avant de marquer son identifiant. Les données ont déjà été validées : les erreurs
métier attendues surviennent avant publication. Un coffre déjà marqué renvoie un
message sans versement ni second événement. La garantie est synchrone/en mémoire,
sans prétendre couvrir une panne matérielle pendant la transaction.

Une rencontre active bloque les autres cas d'utilisation d'exploration. Le combat
existait déjà ; seul son raccord est ajouté. Après lecture de son résultat,
Entrée revient à la carte et `BattleSession.settle` renvoie son résultat mémorisé.
La victoire marque la rencontre, la retire du rendu et de la collision. La fuite
conserve le point de retour et la rencontre, qui exige une nouvelle interaction.
Les récompenses ne sont pas versées par le routeur graphique ou les événements.

Faute de règle de reprise spécifiée, la défaite ramène le groupe au point initial
(Clairval par défaut) et restaure tous ses PV/PM. Elle ne donne aucune récompense
et ne vide ni sac ni portefeuille. Coffres et rencontres déjà résolus restent
résolus. C'est un checkpoint provisoire explicite, pas une sauvegarde ni une
nouvelle fonctionnalité de commerce/repos.

## Présentation et caméra

`AdventureScene` route vers l'exploration ou le combat. `ExplorationController`
porte dialogue court, notification et état de marche ; `ExplorationRenderer`
dessine sol, décors arrière, entités triées par profondeur puis surplombs.
`UiPainter` mutualise panneaux, palette et polices entre les deux rendus par
composition : l'exploration ne dépend plus du renderer de combat pour ses textes.

La caméra reste une valeur pure, suit le joueur et se borne à la carte. Si le
champ est plus grand que la carte, elle la centre et le rendu remplit les zones
extérieures avec du décor. Le champ de fond suit désormais le ratio réel de la
fenêtre au lieu de recadrer une vue de carte 16:9 : le personnage demeure visible
près des limites, même en portrait. L'interface reste transparente, cadrée en
640 × 360 et entièrement visible. Les surfaces de fond sont plafonnées à 2048 px
par côté pour éviter des allocations démesurées lors d'un redimensionnement très
étroit ; les tailles extrêmes ne sont pas présentées comme confortables à jouer.

Les touches physiques détenues sont suivies séparément : relâcher D ne supprime
pas une flèche Droite encore enfoncée. Elles sont effacées à l'interaction, au
changement de mode et à la perte de focus. La boucle transmet la perte de focus
avant de suspendre la scène. Cela évite un déplacement fantôme après Alt-Tab.
Les dialogues suspendent le déplacement et se ferment par une nouvelle validation.

Le combat intégré propose Continuer, pas Rejouer : recréer un combat isolé aurait
réinitialisé le groupe ou dupliqué la progression du voyage. La bataille autonome
reste disponible pour les tests et son outil d'aperçu.

## Persistance et limites

Le terme persistant désigne ici la conservation entre cartes et combats d'une
même session. `WorldState` peut être réutilisé lors de la reconstruction d'un
monde, sans rouvrir ses coffres. Aucun fichier d'état, format de sauvegarde,
migration ou registre inter-redémarrages n'est livré avant la phase 5.

Les dialogues sont courts et statiques, sans choix, préconditions ou quêtes.
Aucun inventaire graphique, boutique, quête ou contenu final n'est ajouté.
Les visuels sont procéduraux et temporaires. Les tests d'accès, de physique,
de transactions et de raccord doivent passer avant d'élargir le voyage.
