# Validation de phase 5 — boucle de progression et persistance

La phase 4 a été validée par l'utilisateur, qui a autorisé cette phase.
Référence : phase 5 du cahier des charges ; [ADR 0006](adr/0006-progression-sauvegardes.md).

## Livrable

Mini-aventure sur les trois cartes existantes avec deux quêtes principales,
une quête secondaire, dialogues à choix et conditions, récompenses uniques,
épilogue, boutique d'achat/vente, sac utilisable, équipements comparés, fiches,
ordre du groupe et trois emplacements de sauvegarde JSON versionnée.

Le contenu de récit/commerce/équipement est dans `adventure.json`, distinct des
cartes et du fichier d'état. Aucune quête, scène ou donnée graphique n'importe
l'adaptateur de sauvegarde ; les services sont injectés au bootstrap.

## Vérifications locales

Windows / Python 3.15.2, dépendances déjà installées par l'utilisateur.
Aucune installation de dépendance ou d'interpréteur par l'agent.

| Contrôle | Résultat |
| --- | --- |
| Ruff lint et formatage | OK |
| mypy strict | OK, 71 fichiers source |
| pytest complet | 223 tests réussis |
| Couverture globale, branches incluses | 92 % |
| Quêtes et progression | 91 % |
| Commerce | 96 % |
| Capture/restauration de session | 94 % |
| Codec JSON | 92 % |
| Dépôt de sauvegarde | 94 % |
| Service de sauvegarde | 100 % |
| Menus de groupe | 92 % |
| Frontières et moteur sans Pygame | OK |
| Captures SDL et inspection visuelle des menus/dialogues | OK |

Les fichiers de test sont créés dans `.test-tmp/` avec `--basetemp=.test-tmp`.
Les aperçus consultent seulement un dépôt fictif d'emplacements vides. Aucun
emplacement de sauvegarde utilisateur n'a été écrit par l'agent.

Le scénario de bout en bout accepte la mission d'Éline, ouvre les coffres,
achève et remet la quête du voyageur, gagne le combat de forêt, sauvegarde dans
l'emplacement 2 puis recharge. Il remet la première quête, accepte la seconde,
achète/équipe une arme, lit l'inscription et vainc les gardiens. Il conclut chez
Éline, sauvegarde dans l'emplacement 3 et recharge : les quêtes récompensées,
les stocks, les coffres et rencontres restent cohérents, sans second versement.

Les round-trips vérifient tous les champs, ordre/leader, ressources, équipement,
XP, temps et état aléatoire. Les tests négatifs couvrent JSON mal formé, versions
inconnues, champs manquants, booléens à la place d'entiers, quantité nulle,
personnage/classe/compétence/objet/stock inconnu, équipement mal placé,
marqueurs invalides, position bloquée, RNG invalide et fin narrative prématurée.
La partie courante demeure inchangée. Une panne simulée d'`os.replace` laisse
le fichier précédent intact et nettoie son temporaire.

Les transactions testent également fonds/stock insuffisants, mauvaise quantité,
vente impossible, définitions contradictoires, comparaison d'équipement sans
mutation, changement de classe interdit, soins/résurrection hors combat et double
récompense dans un même choix de dialogue.

Aperçus : [dialogue](previews/dialogue.png), [équipement](previews/equipment.png),
[personnages](previews/characters.png), [boutique](previews/shop.png),
[sauvegardes](previews/save_slots.png). Régénération :

```bash
uv run --no-sync python tools/preview_progression.py
```

## Recette desktop attendue

```bash
uv run --no-sync jrpg
```

1. Parler à Éline, choisir la mission de route et consulter J.
2. Tester Tab, I, C, l'ordre du groupe et Retour arrière.
3. Ouvrir les coffres, parler au voyageur, accepter/remettre sa recherche.
4. Vaincre les loups puis revenir chez Éline pour remettre la mission.
5. Acheter chez Oren, comparer et équiper une arme ; tester une vente et un refus sans fonds.
6. Accepter la mission de Sylve, lire l'inscription chez l'archiviste et vaincre les gardiens.
7. Revenir chez Éline pour conclure ; vérifier le drapeau de voyage accompli.
8. Sauvegarder avec F5, sélectionner un emplacement, quitter puis relancer.
9. Charger avec F9 et vérifier position, quêtes, ressources, stocks et absence de doublons.

SDL dummy ne prouve pas la fluidité sur le bureau réel. Le format de sauvegarde
est sa première version livrée : les formats futurs sont refusés, la politique
de migration est documentée sans inventer de version historique. Pas de sauvegarde
en combat ; les états temporaires gardent leur durée de vie limitée au combat.

Le nouveau build et les validations Linux/macOS restent à réaliser par l'utilisateur.
Le build peut préparer ses dépendances ; il n'a pas été lancé par l'agent.
Les cartes et `adventure.json` doivent être présents dans le prochain wheel.

Statut : phase 5 validée par l'utilisateur (« je valide »), puis phase 6 autorisée
(« go »). Les résultats ci-dessus décrivent la livraison de phase 5.
