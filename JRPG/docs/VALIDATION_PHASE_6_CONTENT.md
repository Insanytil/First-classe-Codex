# Phase 6 en cours — catalogue du MVP

Le contenu est désormais compilé depuis `combat.json` et `adventure.json`.
Voir [ADR 0010](adr/0010-catalogue-mvp.md) et [guide d'extension](EXTENDING_CONTENT.md).

| Critère | Résultat |
| --- | --- |
| Héros / classes / actifs | 4 / 4 / 4 |
| Cartes reliées | 3 |
| Types d'ennemis ordinaires / boss | 5 / 1 |
| Compétences de héros | 12, trois par héros |
| Objets / équipements inclus | 15 / 10 |
| Consommables | 5 |
| Campagne principale | 3 chapitres |
| Quêtes secondaires | 3 |
| PNJ interactifs | 5 |

L'audit vérifie aussi que tous les types d'ennemis sont placés, tous les objets
peuvent être obtenus, toutes les compétences ont un utilisateur et chaque quête
peut être acceptée puis remise. Ces quantités ne suffisent pas à valider la durée.

## Vérifications locales

Windows, Python 3.15.2, pygame-ce 2.5.8 et outils déjà installés par l'utilisateur.
Aucune installation par l'agent.

- 299 tests réussis, couverture globale 91 %, branches incluses.
- Ruff lint et formatage OK ; mypy strict OK sur 90 fichiers source.
- Audit du catalogue au vert ; même audit ajouté à la configuration CI.
- Catalogue invalide refusé : types, doublons, champs inconnus, références,
  compétences ennemies et séquences annoncées incohérentes.
- Éther utilisable en combat et hors combat, borne de PM, unité consommée,
  message et rendu de PM vérifiés via le vrai contrôleur/menu de combat.
- Antidote réel sur une cible empoisonnée, conservation des autres effets,
  refus explicite hors combat sans perte d'objet.
- Trois quêtes secondaires terminées via les cartes, récompenses remises,
  sauvegarde/rechargement et refus d'une récompense répétée.
- Nouvelles créatures : empreintes, dimensions, ressources embarquées et poses
  de contact vérifiées par le vrai rendu.
- Scénario principal complet jusqu'à la Sentinelle toujours au vert.

Les images originales proviennent de l'outil imagegen intégré ; elles sont
conservées avec les prompts et atlas normalisés dans `art/creatures/`.
Les captures SDL ont été inspectées : [bestiaire](previews/bestiary.png),
[Tala](previews/tala.png), [consommables](previews/consumables.png).

## Recette manuelle

1. Commencer une nouvelle partie de contenu 3 avec `uv run --no-sync jrpg`.
2. Parler à Tala au sud-est du carrefour de Clairval et accepter sa mission.
3. Explorer la réserve au sud-ouest de la forêt, puis revenir chercher sa récompense.
4. Tester les trois compétences de chaque héros, notamment Givre sur les spectres
   et Feu sur les ronces. Observer les explications pendant la sélection.
5. Accepter « Apaiser les lisières » chez l'archiviste. Vaincre les corbeaux au
   sud-ouest de la forêt, le gardien au sud-est et les spectres à l'est des ruines.
6. Remettre cette mission et vérifier le journal des trois quêtes secondaires.
7. Acheter éther, grande potion, antidote, capuche et bouclier chez Oren. Tester
   les contextes d'usage et les restrictions d'équipement.
8. Sauvegarder puis reprendre ; vérifier stocks, objectifs et récompenses uniques.

Les contenus de sauvegarde 1 et 2 sont refusés sans migration, selon la demande
de l'utilisateur. Les fichiers existants ne sont pas supprimés automatiquement.
Aucun emplacement utilisateur n'a été écrit par l'agent. Les tests utilisent
`.test-tmp/`. Aucun build ni résultat de CI distante n'est présenté comme exécuté.

Restent dans la phase 6 : équilibrage global et partie chronométrée de 30–60 min,
écran titre/options, son, mesures de performance et distribution desktop.
