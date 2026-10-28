# ADR 0009 — Sentinelle, attaque annoncée et conclusion du voyage

## Périmètre

Après validation des cartes et animations, l'utilisateur autorise le boss et sa
quête finale. Il précise que les anciennes sauvegardes peuvent être abandonnées :
le contenu passe à la version 2, sans migration. Aucun fichier utilisateur n'est
supprimé automatiquement et aucune dépendance n'est installée.

## Règles de combat et stratégie séparées

La Sentinelle prépare son grand balayage, puis frappe tous les héros conscients
au tour suivant. `StatusKind.CHARGING` rend cette préparation observable. L'état
dure deux fins de tour de son porteur : il reste actif après la préparation,
puis expire après la frappe. Le moteur de durée existant suffit.

`Ability.required_status` est une précondition générale de compétence. Le moteur
refuse un balayage sans charge, même si une commande contourne l'IA. Il vérifie
également que l'état requis existe dans les définitions connues. Aucune règle du
moteur ne compare un identifiant particulier de boss ou de compétence.

`TelegraphedAI` reçoit un `TelegraphPattern` immuable : préparation, attaque et
état. Il sélectionne uniquement des commandes légales. La décision vient de l'état
du combattant ; aucun compteur de phase caché n'est conservé. Les autres ennemis
conservent `BasicAI` comme politique de repli. Une perte de charge impose une
nouvelle préparation avant le balayage. La fuite est désactivée par la configuration
de cette rencontre, avec la règle existante du moteur.

L'affichage lit le résultat de combat et montre la charge dans le bandeau, la
fiche ennemie et le journal. Le sprite tient son arme levée pendant la préparation.
Le balayage utilise l'animation historique de la sentinelle, calée sur le même
instant d'impact que les dégâts. La taille et la position du boss lui sont adaptées.

## Progression déclarative

La remise de « La mémoire de Sylve » ouvre « Le serment de la Sentinelle » chez
Éline. Deux courts dialogues expliquent la localisation, l'absence de fuite et
Défendre, pour rester lisibles dans la fenêtre de dialogue existante.

`EncounterGate` utilise les conditions narratives déjà typées. Le catalogue
JSON déclare que `ruins_sentinel` exige la quête finale active. Le service
d'exploration vérifie cette restriction avant de créer un combat ; un refus
n'altère ni ressources ni RNG. Les références et doublons sont vérifiés au
chargement. Le rendu ne décide pas de l'accès au boss.

La victoire verse une seule fois 200 XP par héros, 120 pièces, deux potions et
une plume. Elle marque la rencontre vaincue et complète la quête, sans conclure
immédiatement le voyage. Éline remet ensuite 120 XP, 80 pièces et le Sceau de
Sylve, puis pose `adventure_complete`. Ce drapeau exige désormais la quête finale
récompensée. Le sceau est un accessoire utilisable (+24 PV maximaux, +4 résistance).
Une hausse de PV maximaux ne soigne pas gratuitement le personnage.

Une défaite garde la quête active et la Sentinelle présente. Le retour au point
d'origine et la restauration du groupe utilisent le service existant. Une nouvelle
tentative reconstruit un boss à pleine vie, sans charge résiduelle.

## Vérifications et limites

Le scénario complet traverse les trois cartes, remet les quêtes, accepte le défi,
gagne le boss, conclut chez Éline, sauvegarde puis recharge. La remise répétée est
refusée sans changement. Une victoire peut aussi être sauvegardée avant remise.

Douze simulations déterministes avec un groupe de niveau 3, ses armes initiales,
Défendre, soins et compétences existantes gagnent sans KO. Un test compare les
dégâts du même balayage avec et sans garde ; les dégâts sont divisés par deux.
Les commandes sans charge, la fuite, l'accès prématuré, la défaite/reprise et
l'avertissement visuel sont couverts. Ces simulations valident ce contre-jeu ;
elles ne remplacent pas l'équilibrage global ni une partie de 30 à 60 minutes.

Les captures du boss se reproduisent avec `tools/preview_sentinel.py`. La phase 6
reste en cours : catalogue complet du MVP, sons, finition et distribution desktop.
