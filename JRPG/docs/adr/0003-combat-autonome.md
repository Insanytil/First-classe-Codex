# ADR 0003 — Combat transactionnel à instantanés et règlement explicite

Statut : acceptée par l’utilisateur avant la phase 3.
Référence : sections 2.5, 2.6, 3.4, 3.5, 6 et phase 2 du cahier des charges.

## Frontières et responsabilités

`Battle` possède le déroulement d'un affrontement et des `Combatant` immuables.
Un héros est converti depuis `Character` ; les ennemis sont créés par
`EnemyDefinition.spawn(instance_id)`. La définition d'un ennemi ne contient pas
ses PV courants ni son identité d'instance. Aucune sous-classe de personnage par
espèce n'est nécessaire.

Le combat ne modifie pas les personnages ou le sac de la session d'exploration.
`BattleSession`, dans l'application, réconcilie ces ressources et attribue les
récompenses après la fin. Elle refuse les instantanés incohérents à la création
et les changements externes du groupe, du sac ou du portefeuille pendant le
combat. Les définitions, commandes, résultats, événements et effets intégrés
sont des valeurs immuables ; les vues exposées sont des tuples.

Le port `RandomSource` appartient au domaine qui le consomme. `SeededRandom`
est un adaptateur d'infrastructure avec son propre générateur : pas de hasard
global et pas d'import `random` dans les règles. Le port réel `ActionPolicy`
permet d'injecter une IA ; `BasicAI` choisit une attaque/compétence légale et
passe si un état empêche d'agir. Elle est volontairement sans tactique élaborée.
La démonstration constitue un point de composition console distinct du bootstrap
graphique, sans ajouter de menu ou de scène prématurément.

## États, validation et publication

1. `start()` : INITIALIZING → TURN_READY.
2. `prepare_turn()` : sélectionne le prochain acteur et passe à AWAITING_ACTION.
3. `execute(command, random)` valide acteur, identifiant de tour, état, ressources,
   compétence apprise, objet disponible, restrictions et ensemble des cibles.
4. La résolution utilise des instantanés locaux et un sac temporaire. Les étapes
   RESOLVING → TURN_END → TURN_READY/FINISHED sont retournées dans le résultat.
   La publication ne survient qu'après résolution complète, avec les événements.

Les phases transitoires sont synchrones et observables dans le résultat, sans
callback réentrant exposant un état partiel. Une commande refusée ne consomme
aucun tirage ; une panne du RNG ou d'un effet pendant la résolution ne publie
aucun dégât, coût, objet consommé ou journal partiel. Le RNG peut toutefois avoir
avancé avant une panne : son état n'est pas transactionnel et on ne promet pas de
rejouer la même séquence après une exception technique.

Le jeton de tour croît à chaque `prepare_turn()` ; il empêche de réutiliser une
ancienne commande, même lorsque le même personnage rejoue plus tard.
Les acteurs KO sont exclus de l'ordre. Chaque round trie par vitesse effective
décroissante, puis par identifiant pour les égalités. Un changement de vitesse
s'applique au prochain calcul de round. Un acteur ressuscité qui n'était pas
planifié rejoint le round suivant. La garde expire au début du prochain tour
propre du défenseur, ou lors du KO.

## Règles provisoires explicites

Ces formules rendent le moteur vérifiable, sans prétendre à un équilibrage final.

| Règle | Choix initial |
| --- | --- |
| Toucher | tirage 1–100 <= max(0, précision − esquive) |
| Dégâts physiques bruts | max(1, 2 × force + puissance − défense) |
| Dégâts magiques bruts | max(1, 2 × magie + puissance − résistance) |
| Critique | second tirage 1–100 <= critique, dégâts ×2 |
| Élément | multiplicateur entier en pourcentage : 0 immunité, 50 résistance, 150 vulnérabilité |
| Défendre | division entière par 2 ; minimum 1 sauf immunité |
| Dégâts affichés | bornés aux PV réellement perdus |
| Fuite | 50 % par défaut, paramétrable ou interdite, réservée aux alliés |
| Double KO en fin d'action | défaite prioritaire |
| XP de victoire | valeur de la table pour chaque membre actif, y compris KO |

Les caractéristiques de base et les modificateurs permanents sont conservés
séparément dans l'instantané de combat. Les bonus/malus d'équipement et les
modificateurs temporaires sont additionnés avant le bornage final : un malus
ramené à zéro avant un buff ne doit pas produire une statistique surestimée.

Les compétences déclarent coût, ciblage (ennemi/allié/soi, vivant/KO, individuel/
tous) et séquence d'effets. Les effets `Damage`, `Heal`, `Revive`, `ApplyStatus`
implémentent un protocole commun ; aucune branche sur le nom d'une compétence.
Les effets sont évalués dans l'ordre déclaré et lisent l'état courant du lanceur.
Un soin ordinaire ne ressuscite pas ; un effet offensif ou d'état ignore une
cible devenue KO lors d'un effet précédent. Une résurrection efface les états et
la garde. Le tag de magie de la compétence détermine son blocage par le silence ;
un effet élémentaire peut aussi appartenir à une technique non magique.

Les objets de combat référencent une définition de consommable et une compétence
sans coût de PM. Ils suivent le même ciblage et les mêmes effets ; la quantité
n'est retirée qu'après validation, dans la copie de résolution. Les ennemis n'ont
pas accès au sac des joueurs. Une compétence doit être apprise explicitement ;
les paliers d'apprentissage automatiques attendront les définitions de contenu.

## États temporaires

Poison et brûlure infligent leur puissance fixe à la fin de chaque tour de leur
porteur. Sommeil et paralysie imposent de passer ; silence bloque la magie.
Les modificateurs signés composent buffs et debuffs. Ces règles sont temporelles,
sans horloge réelle, et ne prétendent pas reproduire un jeu de référence précis.

La durée diminue en fin de tour du porteur, y compris au tour d'application si
l'effet se cible lui-même. Un même identifiant rafraîchit sa durée complète sans
multiplier sa puissance ; des identifiants différents coexistent. Les définitions
contradictoires pour un même identifiant sont rejetées avant le démarrage.
Les états expirent avec un événement, sont effacés au KO et ne persistent pas
après le combat dans cette phase. La persistance des états sera à décider avec
les sauvegardes. Les dégâts subis ne réveillent pas le sommeil automatiquement.

## Événements et récompenses

`BattleActionResult` contient commande, transitions, instantanés, événements et
issue. Le journal est append-only et typé par `EventKind`. Il inclut dégâts,
soins, coûts, états, KO, ennemi vaincu, victoire/défaite/fuite. Un ennemi passant
à zéro génère un événement de défaite unique pour cette transition. Une animation
future consommera ces faits ; elle ne calculera jamais les dégâts.

`RewardTable` combine XP, monnaie, drops garantis et tirages pondérés avec remise.
Les poids sont strictement positifs ; une entrée sans objet représente l'absence
de drop. Le nombre de tirages est explicite. Les cinq raretés sont des données
sur les objets ; elles ne déterminent pas implicitement les probabilités.

`BattleSession.settle()` prévalide le remplacement du sac et les récompenses avant
publication des ressources, XP et monnaie. Une nouvelle invocation de la même
session retourne le résultat mémorisé. Le combat porte également un marqueur de
règlement : une autre session ne peut pas redistribuer ses récompenses.
Aucun abonné aux événements ne verse lui-même les récompenses.

Cette garantie concerne les objets en mémoire et l'exécution synchrone. Un état
persisté/versionné avec registre d'identifiants soldés sera nécessaire en phase 5
pour étendre l'idempotence aux redémarrages. Aucun mécanisme de sauvegarde n'est
prétendument livré ici. Un combat perdu ou fui réconcilie ressources et objets
consommés, sans récompense. Les gains de niveau ne soignent toujours pas.

## Validation et limites

Tests : scénarios complets à graine fixe, mêmes validations pour l'IA, commandes
rejetées sans mutation, effets multiples avec panne après le premier effet,
KO/résurrection, durée/empilement, ciblage multiple, immunités, fuite, loot et
règlement idempotent. Un combat complet et son règlement sont aussi exécutés dans
un sous-processus qui interdit tout import Pygame.

Aucune scène de combat, animation, exploration, quête, boutique ou sauvegarde.
Le journal est local et synchrone ; un dispatcher de quêtes attend un besoin réel.
Le nouveau build reste une opération de l'utilisateur, qui gère les installations.
