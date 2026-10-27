# Validation de phase 3 — combat jouable Pygame

La phase 2 a été validée par l'utilisateur, qui a autorisé cette phase.
Référence : phase 3 du cahier des charges ; décisions dans
[l'ADR 0004](adr/0004-scene-combat.md).

## Livrable

`uv run --no-sync jrpg` ouvre directement une bataille de démonstration avec
quatre héros et trois ennemis. Navigation au clavier et à la souris, compétences,
objets, choix des cibles, PV/PM, états, acteurs KO, garde, journal défilant,
animations d'impact et écran de victoire/défaite/fuite sont disponibles.
Le bouton Rejouer ou R après la fin crée une nouvelle partie de démonstration.

Décor et silhouettes sont des placeholders procéduraux. Le décor couvre toute
la fenêtre, tandis que l'interface reste visible et cliquable après redimensionnement.
La perte de focus suspend le combat. Aucun comportement d'exploration n'est ajouté.

## Contrôles exécutés

Windows / Python 3.15.2, dépendances préalablement installées par l'utilisateur.
Aucun téléchargement ou installation par l'agent.

| Contrôle | Résultat |
| --- | --- |
| Ruff lint et formatage | OK |
| mypy strict | OK, 38 fichiers source |
| pytest complet | 125 tests réussis |
| Couverture globale, branches incluses | 95 % |
| Contrôleur de combat | 93 % |
| Rendu Pygame | 94 % |
| Adaptateur d'événements | 93 % |
| Boucle, fenêtre et cadrage | 99 % |
| Moteur de combat | 97 % |
| Frontières et combat sans Pygame | OK |
| Export et inspection visuelle d'une frame SDL dummy | OK |

Scénarios : menus et annulation, ciblage multiple, choix de cible à la souris,
soins/objets, affichage des motifs PM insuffisants/objet épuisé/absence de KO,
blocage de la double validation pendant l'animation, publication des instantanés
à l'impact, tours IA automatiques, combat joueur complet jusqu'à victoire et
règlement unique. Un test vérifie que le dessin répété n'exécute aucune commande
et ne change pas les ressources ou le journal métier.

Tests SDL : clavier, pavé numérique, AZERTY, clic réel sur les zones d'interface,
journal défilant, redémarrage après victoire, focus et fermeture. La transformation
de souris est vérifiée pour 16:9, 16:10, écran large et fenêtre verticale.
Les coins du décor restent colorés ; les marges de l'interface sont transparentes.

Aperçu : [battle.png](previews/battle.png). Pour le régénérer sans fenêtre :

```bash
uv run --no-sync python tools/preview_battle.py
```

L'outil capture une frame de la vraie boucle en remplaçant uniquement le pilote
SDL et les événements de fermeture. Il ne fabrique pas un mockup indépendant.

## Recette desktop à confirmer

Depuis `JRPG/` :

```bash
uv run --no-sync jrpg
```

1. Attaquer avec Nox : sélectionner Attaquer puis une cible, valider.
2. Avec Lyra, essayer Feu puis le ciblage collectif ; vérifier les PM.
3. Avec Mira, utiliser un soin ; vérifier le motif de résurrection si aucun allié KO.
4. Utiliser une potion et vérifier sa quantité au prochain tour.
5. Vérifier que marteler Entrée pendant une animation ne joue pas plusieurs actions.
6. Redimensionner/maximiser, puis cliquer des commandes et des cibles.
7. Quitter le focus pendant un tour ennemi, revenir et vérifier la reprise.
8. Terminer le combat, examiner les récompenses et rejouer avec R.
9. Tester la fermeture par Échap et par la croix.

Les tests dummy et l'aperçu ne prouvent pas la fluidité sur le bureau réel ou le
comportement de tous les gestionnaires de fenêtres. Aucun nouveau build ni
résultat CI distant n'est présumé. Pas de recette Linux/macOS pour ces sources.

Statut : phase 3 validée par l’utilisateur, qui a autorisé la phase 4.
Suite : [validation de phase 4](VALIDATION_PHASE_4.md).
