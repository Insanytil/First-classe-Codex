# ADR 0006 — Progression transactionnelle et sauvegardes versionnées

Statut : implémentée ; validation utilisateur de phase 5 attendue.
Référence : sections 2.8–2.12, 3, 5, 6 et phase 5 du cahier des charges.

## Contenu et règles

`adventure.json` décrit les quêtes, récompenses, équipements, boutiques, dialogues,
conditions et opérations. Le chargeur compile ces valeurs en définitions immuables.
Les opérations sont une enum fermée : accepter, recevoir une récompense, fixer
un drapeau, ouvrir une boutique, se reposer. Aucun code de dialogue n'est évalué.
Les références de quête, marchand, objet, nœud, PNJ et objectif de monde sont validées.
Les cycles de prérequis de quête sont refusés ; les retours entre nœuds de dialogue
sont permis puisqu'ils nécessitent un nouveau choix explicite.

`QuestBook` applique LOCKED → AVAILABLE → ACTIVE → COMPLETED → REWARDED. Les
objectifs observent les faits du monde : carte visitée, PNJ rencontré, coffre
ouvert, rencontre vaincue ou drapeau narratif. Les identifiants observés sont
dédupliqués ; rejouer un événement ne compte pas deux fois. Des faits antérieurs
à l'acceptation sont pris en compte, afin de ne pas rendre une quête impossible
si le joueur a déjà ouvert son coffre. Un prérequis n'est débloqué qu'après
attribution de la récompense précédente, pas simplement après son achèvement.

Le contenu livré comprend deux quêtes principales et une recherche secondaire.
La quête finale exige de lire l'inscription de l'archiviste et de vaincre les
gardiens. Sa remise à Éline fixe `adventure_complete` et donne accès à la conclusion.
Une règle déclarative exige que cette quête soit REWARDED pour accepter le drapeau
final, y compris lors d'un chargement. Le modèle reste ouvert à d'autres objectifs,
mais ne prétend pas déjà implémenter tous les types V2/V3, l'échec ou l'abandon.

## Transactions de récit, économie et équipement

`AdventureProgress` prépare les effets d'un choix sur une copie du journal, du sac
et des personnages. Les récompenses, états et drapeaux sont validés avant
publication sur les objets réels. Deux demandes de récompense dans le même choix
échouent sans verser la première à moitié. La disponibilité du choix est vérifiée
avant cette transaction, et le domaine vérifie encore le statut de quête.
Le rendu ne peut pas verser une récompense.

`Shop` possède ses stocks ; identité, nom et offres ont des vues en lecture seule.
Les prix appartiennent à des définitions immuables. Achat/vente valident quantité,
stock, fonds et définitions du sac sur une copie avant transfert. Les prix de vente
ne dépassent pas ceux d'achat. Le marchand ne négocie que ses références déclarées ;
un équipement porté n'est pas vendable directement depuis le sac.

Les menus utilisent les opérations existantes `equip`/`unequip` et une requête de
comparaison en lecture seule, qui applique les mêmes restrictions de classe/slot.
Les fiches exposent niveau, XP, dix caractéristiques et compétences. La première
place du groupe reste le leader ; le menu permet de modifier cet ordre.
Les potions et plumes réutilisent les effets de soins/résurrection hors combat,
avec validation du contexte et de la cible avant retrait d'une unité.

Les classes de démonstration gagnent désormais de modestes caractéristiques par
niveau, et des armes initiales sont attribuées au groupe dans l'assemblage du
voyage. Ces données sont provisoires, pas un équilibrage final de phase 6.
Le repos explicite chez Éline restaure le groupe gratuitement ; gagner de l'XP
ou équiper un bonus ne soigne toujours pas automatiquement.

## Frontières de persistance

`SaveRepository` et `SnapshotMapper` sont des ports applicatifs. Le premier stocke
un instantané typé ; le second capture ou reconstruit une session. `SaveService`
coordonne les deux, sans importer JSON, Pygame, pathlib ou une horloge.
`GameSnapshotMapper`, `SaveCodec` et `JsonSaveRepository` sont des adaptateurs
séparés. Le bootstrap les injecte à la scène ; aucun menu n'importe les fichiers.

`CharacterState` permet un état validé, une copie transactionnelle et une
restauration sans écrire les attributs privés depuis l'infrastructure. Les
identifiants de classe/objet/compétence sont résolus dans le catalogue actuel ;
les définitions ne sont pas copiées dans le fichier du joueur. L'XP détermine le
niveau et le contenu détermine les statistiques : ces valeurs dérivées ne sont
pas dupliquées dans le format.

L'instantané v1 contient : version du format et du contenu, position et reprise,
ordre du groupe, identité/classe/XP/PV/PM/compétences/équipements, sac, or,
coffres et rencontres terminés, cartes visitées, PNJ rencontrés, drapeaux, statuts
de quête, stocks des marchands, temps de jeu et état du générateur aléatoire.
Le journal de livraison d'événements et l'état graphique des menus ne sont pas
sauvegardés ; les faits durables reconstituent la progression sans rejouer les
versements. Les effets temporaires restent limités au combat, conformément aux
ADR précédentes. La sauvegarde n'est permise qu'en exploration, hors combat actif.

L'adaptateur RNG expose un checkpoint de son générateur local, sérialisé en
entiers et valeurs numériques JSON, jamais via pickle. Le chargement vérifie
sa compatibilité avec le générateur natif avant utilisation. Cela prolonge la
reproductibilité du loot après une sauvegarde/reprise.

## Écriture et chargement

Trois emplacements indépendants, `slot-1.json` à `slot-3.json` :

- Windows : `%LOCALAPPDATA%/technobel-jrpg/saves`, repli sous le profil utilisateur.
- Linux/macOS : `$XDG_DATA_HOME/technobel-jrpg/saves`, repli `~/.local/share/...`.

Le répertoire n'est créé qu'à l'enregistrement. Les tests injectent un dossier
temporaire du projet ; les aperçus ne créent aucune sauvegarde utilisateur.
Le fichier est d'abord entièrement sérialisé et validé, écrit dans un temporaire
du même dossier, puis flush/fsync et `os.replace`. L'ancien emplacement n'est
pas tronqué pendant la préparation. Les garanties restent celles du système de
fichiers et d'un processus synchrone ; il n'est pas promis de transaction entre
plusieurs processus ou de survie à toute panne matérielle.

Le codec refuse types, champs inconnus/manquants, valeurs non finies et formats
non supportés. Le mapper construit ensuite un nouveau graphe complet et vérifie
références, corps sur la carte, classes, slots, ressources, XP, stocks et cohérence
des quêtes/drapeaux. L'interface ne remplace la session qu'après ce succès.
Une erreur conserve la partie en cours et affiche son motif.

La protection contre les doubles gains traverse désormais les chargements : les
rencontres/coffres sont mémorisés, les quêtes REWARDED restent telles, et le monde,
le sac et les ressources sont restaurés ensemble. Charger un ancien emplacement
remonte toute la session à cet instant ; aucun portefeuille global n'est partagé
avec la session remplacée.

## Versions et migrations

Le premier format livré est `version: 1`, associé à `content_version: 1`. Il n'existe
pas de sauvegarde de phase 4 à migrer : elle n'écrivait pas de fichier. Les versions
futures ou de contenu incompatible sont refusées explicitement, sans modification
du fichier source. On n'invente pas une migration « legacy » non documentée.

Lors d'une évolution incompatible, ajouter une transformation pure version n →
n+1 avant la validation du schéma courant, puis valider le résultat complet.
Chaque transformation devra avoir des fixtures anciennes, tests de conservation
(coffres, récompenses, stocks, équipements et ressources) et tests d'échec.
Les identifiants de contenu restent stables ; un renommage exigera une table de
correspondance explicite et un incrément de version de contenu. Aucun chargement
approximatif ou remplacement automatique d'objet manquant n'est autorisé.

## Présentation et validation

`GameMenu` et `MenuRenderer` séparent navigation et dessin ; ils utilisent les
services et objets métier existants. Tab ouvre/ferme, I/C/J donnent accès direct
au sac/fiches/quêtes, F5/F9 ouvrent les trois emplacements. Le joueur choisit son
emplacement puis valide. Les dialogues ont un choix au clavier/souris ; Backspace
permet de repartir. Les menus bloquent les déplacements et les entrées du combat
restent séparées. Le temps de jeu compte les menus mais pas la pause de focus.

Tests : aventure complète avec reprise intermédiaire et conclusion, récompenses
uniques après rechargement, trois fichiers indépendants, RNG identique, ventes et
équipements atomiques, corruption des références et scalaires, refus de version
future, et simulation d'échec du remplacement avec ancien fichier inchangé.
Les visuels restent temporaires. Son, contenu final, équilibrage et build desktop
restent en phase 6 ; aucune dépendance n'est installée par l'agent.
