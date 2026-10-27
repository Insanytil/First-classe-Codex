# ADR 0004 — Contrôleur testable, rendu de faits et cadrage de l'interface

Statut : acceptée par l’utilisateur avant la phase 4.
Référence : phase 3 et sections 2.12, 3.1, 3.4 du cahier des charges.

## Composition et responsabilités

- `BattleEncounter`, DTO applicatif, regroupe le combat, son règlement, les
  définitions consultables, le port aléatoire et la politique d'IA.
- `create_training_encounter` assemble les données de démonstration à la
  périphérie : quatre classes/héros, trois ennemis, compétences et consommables.
  Ces valeurs Python de démonstration ne remplacent pas le futur catalogue JSON.
- `bootstrap` injecte une fabrique de contrôleurs dans `BattleScene`. Rejouer
  crée une nouvelle démonstration complète, sans réutiliser de ressources ou de
  récompenses du combat précédent. Aucun adaptateur de présentation n'importe
  l'infrastructure ; la fabrique arrive du point de composition.
- `BattleController` gère menus, sélection, lecture des résultats et attente de
  l'IA. Il n'importe pas Pygame et est testable par appels explicites à `update`.
  Il reste dans la présentation : ce sont des responsabilités d'interaction et
  de temps visuel, pas des cas d'utilisation ou règles du domaine.
- `BattleRenderer` dessine les instantanés en lecture seule. `BattleScene` traduit
  les événements Pygame en intentions de navigation. `PygameApplication` possède
  SDL, la fenêtre et l'horloge, via un petit protocole `Scene`. Ce contrat est une
  frontière d'injection, pas une hiérarchie de scènes abstraites sans besoins.

## Commandes et feedback

Le domaine fournit désormais `candidate_commands()` et `command_error()` : la
présentation ne réimplémente ni le ciblage ni les règles de coût/restriction.
`legal_commands()` filtre ces mêmes candidats pour l'IA. `execute()` revalide
avant mutation, même si l'interface vient de consulter la disponibilité.
Les requêtes n'effectuent aucun tirage ni mutation. Les commandes impossibles
restent inspectables, avec un motif (PM, quantité, état, absence de cible KO…).

Les six groupes sont attaquer, compétences, défendre, objets, fuir et passer.
Les compétences/objets ont un sous-menu puis un choix de cible si nécessaire.
Clavier et souris empruntent les mêmes méthodes du contrôleur. Les clics sur
une cible invalide ne produisent aucune commande. Une action indisponible affiche
son motif ; changer de sélection efface le message devenu obsolète.
Les touches numériques, le pavé numérique et les symboles AZERTY sont acceptés.

## Lecture animée

La commande est exécutée exactement une fois. Le résultat immuable est conservé
dans `Playback` pour 0,72 seconde : mouvement d'attaque, trait d'effet et
nombres issus des événements. À 0,24 seconde, l'affichage bascule sur les
instantanés finaux du résultat. Les PV/PM sont lus depuis ces instantanés ;
la présentation ne soustrait pas les dégâts, ne dépense pas les ressources et
ne lance aucun jet pour les besoins d'une animation.

Pour cette première version, les impacts d'une action composée sont présentés
ensemble. La chronologie effet par effet pourra évoluer sans changer les règles.
Les commandes de combat sont bloquées pendant la lecture et les tours ennemis ;
la fermeture de fenêtre reste active. L'IA attend 0,35 seconde visuelle, puis
soumet une commande au même moteur. Le prochain acteur n'est préparé qu'après
la lecture, pour éviter de proposer des commandes sur un tour déjà terminé.

Le règlement applicatif est appelé après la dernière lecture de combat, et
l'écran de résultat présente son résultat mémorisé. Le rendu et les abonnements
visuels ne distribuent jamais de récompense. Le journal traduit les événements
en français, conserve les 80 dernières lignes et affiche quatre lignes à la fois,
avec navigation Page haut/bas.

## Fenêtre, image et souris

Le choix utilisateur de remplir l'écran sans bandes noires est conservé pour
le décor. Il utilise un cadrage couvrant toute la fenêtre, au besoin recadré.
L'interface est une seconde surface transparente en 640 × 360, entièrement
inscrite dans la fenêtre avec proportions conservées. Ses marges montrent le
décor, sans fond noir : les commandes et les fiches ne sont jamais rognées.

La transformation inverse de ce cadrage convertit la souris en coordonnées
logiques. Les clics hors de la surface d'interface sont ignorés. Cette séparation
évite de recadrer les boutons sur les écrans 16:10, larges ou verticaux. Les très
petites fenêtres peuvent rendre les textes trop petits ; il n'est pas prétendu
que cette interface desktop devient une interface mobile adaptative.

L'horloge et les événements restent périphériques. Le delta visuel est plafonné
à 0,1 seconde dans la boucle. La perte de focus suspend l'avancement et ignore
les commandes jusqu'au retour du focus. Échap et la croix ferment toujours SDL
via `finally`, y compris en cas d'erreur de rendu.

## Direction visuelle et périmètre

Décor procédural de ruines/forêt, silhouettes temporaires, palette sauge, pierre,
or et turquoise. Aucune dépendance à un fichier d'asset ou à une génération
externe ne bloque le jeu. Les polices intégrées à Pygame sont mises en cache.
Les PNG et prompts historiques restent des références possibles pour la finition.
La présentation actuelle est dimensionnée pour la bataille de démonstration
quatre héros contre trois ennemis ; ce n'est pas une interface générale pour un
nombre arbitraire de combattants.

Pas de menu principal, exploration, carte, quête, commerce ou sauvegarde.
La phase 4 attend validation. Le build reste géré par l'utilisateur, comme les
installations. Les contrôles locaux utilisent uniquement les outils existants.
