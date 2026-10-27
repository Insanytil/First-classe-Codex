# Validation de la phase 1 — fondations métier

Référence : phase 1 du cahier des charges. Les fondations de phase 0 ont été
validées par l'utilisateur avant le démarrage de cette phase.

## Périmètre réalisé

- Dix caractéristiques, modificateurs signés, bornage et valeurs immuables.
- Personnages avec identité stable et définitions de classes composées.
- Ressources PV/PM encapsulées et progression configurable, sans soin gratuit.
- Équipe ordonnée de quatre membres maximum, identité unique, leader et état KO.
- Définitions d'items, piles, six slots, restrictions et bonus d'équipement.
- Ajouts/retraits et échanges atomiques avec conservation des quantités.
- Jeux de données Python de test pour guerrier, mage, soigneur et voleur.
- Exemple exécutable sans Pygame : `examples/foundations.py`.

Les choix, seuils provisoires et limites sont explicités dans
[l'ADR 0002](adr/0002-fondations-metier.md).

## Vérifications exécutées

Sous Windows, Python 3.15.2, avec les outils déjà installés par l'utilisateur.
Aucune dépendance ou version de Python installée par l'agent.

| Contrôle | Résultat |
| --- | --- |
| Ruff lint | OK |
| Ruff formatage | OK |
| mypy strict, domaine/tests/exemple | OK, 18 fichiers source |
| pytest complet, y compris les tests de fenêtre et d'architecture | 59 tests réussis |
| Couverture globale, branches incluses | 95 % |
| Personnages et progression | 97 % |
| Inventaire et définitions d'items | 92 % |
| Caractéristiques | 96 % |
| Équipe | 100 % |
| Import récursif domaine/application avec Pygame bloqué | OK |
| Exécution console de `examples/foundations.py` | OK |

La démonstration produit :

```text
Ari : niveau 3, force 19
PV 100/120, PM 20/20
Équipe : 1, épées dans le sac : 0
Épée rendue au sac : 1
```

Les scénarios négatifs vérifient notamment : PM insuffisants, quantités invalides,
retraits impossibles, définitions contradictoires, équipement de mauvaise classe
ou de mauvais slot, absence d'objet, refus de déséquiper dans un sac contradictoire,
équipe pleine, identité dupliquée et déplacement hors limites. Ils comparent les
états avant/après échec. La progression et les bonus sont vérifiés sans interface.

## Limites et arrêt

Pas de combat, compétence, effet temporaire ou consommable utilisable, sauvegarde,
chargement JSON, équipement unique personnalisé ou interface métier. Ce sont des
extensions des phases dédiées, pas des fonctionnalités prétendument réalisées ici.
Le nouveau build n'a pas été lancé par l'agent : il peut préparer des dépendances
et l'utilisateur conserve la gestion exclusive des installations. Le build validé
en phase 0 n'est pas présenté comme un build de ces nouvelles sources.

Statut : phase 1 validée par l’utilisateur, qui a autorisé la phase 2.
Suite : [validation de phase 2](VALIDATION_PHASE_2.md).
