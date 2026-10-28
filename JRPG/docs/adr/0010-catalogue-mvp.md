# ADR 0010 — Catalogue jouable du MVP

## Décision

Les définitions de combat quittent les constructions en dur du module de
démonstration. `infrastructure/content/combat.json` décrit les héros/classes,
leurs compétences, les états, les ennemis, consommables, profils de rencontre
et récompenses. `combat_content.py` compile ces données en objets métier typés.
`CatalogEncounterFactory` compose les combats à partir du catalogue ; le scénario
autonome `create_training_encounter()` reste disponible pour les exemples/tests.

Ce découpage permet d'ajouter une compétence ou un ennemi utilisant les composants
existants par les données. Aucun nom de nouveau monstre ne crée une branche dans
le moteur de combat. La présentation associe séparément un identifiant d'ennemi
à ses images. Les champs inconnus, types invalides, identifiants dupliqués et
références absentes sont refusés. Une séquence annoncée est aussi vérifiée : état
appliqué au lanceur pour au moins deux fins de tour, attaque exigeant cet état,
et ennemi connaissant les deux compétences.

## Composition des compétences et objets

Les quatre héros disposent de trois compétences chacun dès le départ. Leurs
douze compétences sont comptées séparément des compétences ennemies et du boss.
Les nouvelles actions réutilisent dégâts élémentaires, ciblage collectif et
modificateurs temporaires : Fauchage, Rempart, Givre entravant, Entaille vive et
Voile de fumée. Purification utilise le nouveau composant `CureStatuses`.

`RestoreMana` et `CureStatuses` sont des effets immuables et réutilisables.
Ils n'accèdent ni à l'inventaire ni aux fichiers ni à Pygame. Ils ne consomment
pas de hasard. Les PM restaurés sont bornés au maximum, un KO n'est pas ressuscité,
et un soin d'altération conserve les états hors de sa liste. L'éther utilise les
mêmes effets en combat et en exploration. L'antidote reste réservé au combat,
puisque les altérations ne persistent pas hors combat ; le menu indique ce refus
avant utilisation. Les transferts d'objets restent atomiques dans les services
existants. L'événement de restauration de PM a un libellé et un effet visuel propres.

Les quinze objets du catalogue comprennent dix équipements et cinq consommables.
Cette convention suit le modèle `ItemDefinition`, dont l'équipement est une
catégorie. Les deux nouvelles pièces occupent les emplacements existants : tête
pour la capuche, main secondaire pour le bouclier réservé au guerrier.

## Profils et bestiaire

Les profils décrivent XP/or par ennemi, butin par rencontre, autorisation de fuite,
classification de boss et éventuelle politique d'annonce. Le profil régulier
utilise `BasicAI`, la Sentinelle utilise `TelegraphedAI`. Les ennemis d'une même
rencontre doivent partager un profil ; mélanger des profils incompatibles est
refusé explicitement. Un boss accompagné d'ennemis avec règles distinctes reste
hors du périmètre de ce lot.

Spectre, gardien des ronces et corbeau complètent le loup et le flan. Le spectre
utilise la magie et craint la glace ; le gardien résiste physiquement mais craint
le feu ; le corbeau agit vite et peut infliger le silence. Leurs images sont des
créations imagegen originales, avec sources, prompts et empreintes conservés.
Les atlas normalisés contiennent quatre poses d'attente et huit d'attaque.
Le décalage de début d'action appartient à `AtlasSpec`, pas à une branche du rendu.

## Quêtes et disponibilité réelle

`QuestKind` distingue principale et secondaire dans les données et le journal.
La campagne principale conserve ses trois chapitres. Les trois quêtes secondaires
sont le coffre de la rive, les remèdes de Tala et les lisières de l'archiviste.
Elles utilisent les objectifs existants, avec faits dédupliqués ; les menaces déjà
vaincues comptent aussi si la mission est acceptée plus tard. La réserve de Tala
est une quête d'exploration du coffre, pas une livraison consommant des objets.

Tala est le cinquième PNJ interactif ; elle réutilise un modèle graphique humain
historique. Chaque nouveau type d'ennemi est placé dans une rencontre, chaque objet
a une source d'obtention, et chaque quête a des choix d'acceptation et de remise.
`tools/audit_content.py` vérifie ces propriétés et les minimums du cahier des charges.
L'audit est ajouté à la CI ; l'exécution distante n'est pas présumée.

## Persistance et limites

Le contenu passe à la version 3. Conformément à la demande de l'utilisateur,
aucune migration n'est ajoutée pour les contenus 1 et 2 ; leur chargement demande
une nouvelle partie. Les fichiers anciens ne sont pas supprimés automatiquement.

Les quantités MVP et les scénarios automatiques sont vérifiés. Ils ne démontrent
pas une durée réelle de 30 à 60 minutes. Équilibrage global, titre/options, son,
mesures de FPS et distribution desktop restent dans la suite de la phase 6.
