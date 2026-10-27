# Validation de phase 4 — exploration

La phase 3 a été validée par l'utilisateur, qui a autorisé cette phase.
Référence : phase 4 du cahier des charges ; [ADR 0005](adr/0005-exploration.md).

## Livrable

Lancement sur Clairval, déplacement continu sur trois cartes reliées :

```text
Village de Clairval ⇄ Forêt des murmures ⇄ Ruines de Sylve
```

Tuiles 32 px, collisions, pont, caméra, profondeur et surplombs, quatre PNJ,
trois coffres et deux rencontres. Groupe, PV/PM, XP, objets et monnaie sont
conservés après combat et changement de carte. Une rencontre vaincue disparaît ;
un coffre ouvert reste vide. La fuite ne relance pas automatiquement le combat.
Une défaite ramène le groupe rétabli au point initial.

Cette conservation dure pendant la session ; aucune sauvegarde disque n'est livrée.

## Vérifications locales

Windows, Python 3.15.2, outils installés préalablement par l'utilisateur.
Aucune installation de dépendance ou de Python par l'agent.

| Contrôle | Résultat |
| --- | --- |
| Ruff lint et formatage | OK |
| mypy strict | OK, 50 fichiers source |
| pytest complet | 172 tests réussis |
| Couverture globale, branches incluses | 93 % |
| Monde et collisions | 92 % |
| Orchestration d'exploration | 96 % |
| Chargeur de cartes | 91 % |
| Routeur exploration/combat | 100 % |
| Boucle SDL, cadrage et focus | 98 % |
| Frontières d'architecture | OK |
| Export et inspection visuelle des trois cartes via SDL dummy | OK |

Les tests parcourent effectivement les passages, PNJ et coffres avec un itinéraire
calculé pour le test, via les mêmes déplacements que le joueur. Ils vérifient les
sous-pas anti-traversée, la vitesse diagonale, le glissement, les limites, l'eau,
le pont et les troncs. Le contenu corrompu, une référence inconnue, une apparition
bloquée ou une destination absente sont rejetés.

Les scénarios de règlement testent victoire, fuite et défaite, conservation du
même groupe/sac/portefeuille, interdiction de se déplacer en combat, suppression
uniquement de la rencontre vaincue, reprise après défaite et refus d'un second
règlement. Un conflit de définition dans un coffre ne change ni le sac, ni l'or,
ni le marqueur d'ouverture.

Les tests SDL couvrent touches simultanées/relâchées, focus, dialogue modal, combat
joué jusqu'à victoire puis retour via Entrée, fuite puis retour via clic, absence
de déplacement fantôme et nouvelle interaction nécessaire pour retenter une fuite.
Le joueur et l'interface restent dans le champ sous différents ratios ; une
fenêtre extrêmement étroite ne produit pas de surface de fond non bornée.

Aperçus inspectés : [village](previews/village.png), [forêt](previews/forest.png),
[ruines](previews/ruins.png). Régénération :

```bash
uv run --no-sync python tools/preview_exploration.py
```

## Recette desktop attendue

```bash
uv run --no-sync jrpg
```

1. Se déplacer avec les flèches, ZQSD ou WASD ; relâcher les touches et tester Alt-Tab.
2. Parler à Éline au nord du départ avec E, puis fermer le texte avec E/Entrée.
3. Ouvrir le coffre à l'ouest du départ ; recommencer et vérifier l'absence de second versement.
4. Suivre le chemin à l'est jusqu'au passage, puis utiliser E pour entrer dans la forêt.
5. Affronter les loups sur le sentier ; après le résultat, revenir à la carte avec Entrée.
6. Vérifier que la rencontre disparaît après victoire et que PV/PM et gains sont conservés.
7. Traverser le pont ; aller à l'est vers les ruines et revenir par les passages.
8. Visiter les PNJ et ouvrir les coffres des trois zones ; revenir au premier coffre.
9. Redimensionner/maximiser la fenêtre ; vérifier le champ, les contrôles et les clics en combat.

Les visuels sont provisoires. SDL dummy ne prouve pas la fluidité ni la recette
sur le bureau réel. Aucun nouveau build, résultat CI distant ou validation
Linux/macOS n'est présumé ; le build et ses installations restent gérés par
l'utilisateur. Les cartes JSON doivent être incluses dans le prochain wheel.

Statut : phase 4 validée par l’utilisateur, qui a autorisé la phase 5.
Suite : [validation de phase 5](VALIDATION_PHASE_5.md).
