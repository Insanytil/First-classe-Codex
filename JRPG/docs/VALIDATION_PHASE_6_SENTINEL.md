# Phase 6 en cours — Sentinelle et quête finale

L'utilisateur a autorisé la Sentinelle jouable et sa quête, et précisé que les
anciennes sauvegardes n'ont pas à être préservées. Voir [ADR 0009](adr/0009-sentinelle-et-conclusion.md).

## Livré

- Sentinelle au nord de Sylve, accessible après acceptation du défi final.
- Alternance préparation / grand balayage collectif, sans fuite.
- Précondition de charge contrôlée par le moteur, politique d'IA injectable.
- Avertissement persistant, état CHARGE, journal lisible, arme levée et animation d'attaque.
- Quête « Le serment de la Sentinelle », après remise de « La mémoire de Sylve ».
- Récompense de victoire, Sceau de Sylve à équiper, conclusion chez Éline.
- Défaite suivie d'un retour au point d'origine, groupe rétabli, boss retentable.
- Contenu des sauvegardes version 2 ; aucune migration ni suppression automatique des fichiers anciens.

## Vérifications locales

Windows, Python 3.15.2 et dépendances existantes. Aucune installation par l'agent.

| Contrôle | Résultat |
| --- | --- |
| Suite complète | 269 tests réussis |
| Couverture globale, branches incluses | 92 % |
| Ruff lint et formatage | OK |
| mypy strict | OK, 84 fichiers source |
| Simulations de contre-jeu, graines 0 à 11 | 12 victoires, aucun héros KO |
| Frontières d'architecture et moteur sans Pygame | OK |
| Captures SDL du boss et inspection | OK |

Les simulations utilisent un groupe de niveau 3 avec les armes initiales,
Défendre pendant la charge, et les compétences/soins existants. Elles vérifient
la viabilité de cette stratégie, pas l'équilibrage de toutes les stratégies.

Tests supplémentaires : balayage refusé sans préparation, réduction de moitié
par la garde, accès prématuré sans effet sur le RNG, fuite interdite, expiration
de charge lors d'un tour perdu, nouvelle préparation après interruption,
défaite et nouvelle tentative, victoire sauvegardée avant remise, récompense
finale unique, rejet explicite de l'ancien contenu.

Le scénario complet existant traverse désormais aussi le boss et sa conclusion,
puis recharge la sauvegarde finale et refuse une seconde remise de récompense.
Les fichiers de test sont limités à `.test-tmp/` ; aucun emplacement utilisateur
n'a été écrit. Le build et les FPS du bureau n'ont pas été mesurés dans ce lot.

## Recette manuelle

1. Lancer `uv run --no-sync jrpg` depuis `JRPG/` pour une nouvelle partie.
2. Accepter/remettre la quête de route, puis « La mémoire de Sylve » chez Éline.
3. Accepter le dernier défi ; lire les deux explications, se reposer et préparer le groupe.
4. Retourner aux ruines et franchir le passage central du mur nord.
5. Interagir avec la Sentinelle. Vérifier que Fuir est indisponible.
6. Attaquer ou soigner pendant les tours de préparation ; au bandeau de charge,
   utiliser Défendre avant le prochain tour du boss.
7. Après la victoire, revenir chez Éline, conclure et équiper le Sceau de Sylve.
8. Sauvegarder, relancer, recharger et vérifier la disparition du boss et l'unicité de la récompense.

Captures reproductibles :

```bash
uv run --no-sync python tools/preview_sentinel.py
```

[Boss prêt](previews/sentinel-ready.png), [préparation](previews/sentinel-charge.png),
[impact](previews/sentinel-impact.png).

La phase 6 globale reste en cours : catalogue complet du MVP, équilibrage global,
son, écran titre/options, mesures de performance et distribution desktop.
