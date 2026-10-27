# Validation de la phase 0

Suite du projet : [validation de phase 1](VALIDATION_PHASE_1.md).

## Résultats locaux — 27 octobre 2026

Environnement installé par l'utilisateur : Windows, Python 3.15.2, environnement
`JRPG/.venv`. Exécution depuis WSL via `.venv/Scripts/python.exe` ; aucun paquet
ni interpréteur n'a été installé pendant cette validation.

| Contrôle | Résultat |
| --- | --- |
| `python -m ruff check .` | OK |
| `python -m ruff format --check .` | OK |
| `python -m mypy` | OK, 11 fichiers source vérifiés |
| `python -m pytest --cov=JRPG --cov-report=term-missing` | 17 tests réussis |
| Couverture globale, branches incluses | 87 % |
| Couverture de `presentation/pygame_app.py` | 96 % |
| Tests des frontières et import avec Pygame bloqué | OK |
| Rendu d'une frame SDL dummy, sortie croix/Échap | OK |
| Nettoyage SDL après erreur d'initialisation ou de rendu | OK |

Le formatage du test d'architecture et l'annotation de sa liste d'erreurs ont
été corrigés. Les contrôles ci-dessus ont été relancés après ces corrections.
La couverture globale inclut le lanceur `__main__.py`, non exercé par ces tests ;
elle ne mesure aucune règle métier, puisqu'aucune n'est encore implémentée.

Le verrou `uv.lock` créé par l'utilisateur est présent. La CI utilise désormais
`uv sync --locked`. Aucun résultat d'exécution distante n'est disponible.

## Build et recette desktop — confirmés par l'utilisateur

L'utilisateur confirme la réussite de `uv build` sous Windows / Python 3.15.2 :

- `dist/technobel_jrpg-0.1.0.tar.gz` créé avec succès.
- `dist/technobel_jrpg-0.1.0-py3-none-any.whl` construit depuis la distribution source.

Deux lancements par `uv run --no-sync python -m JRPG` ont permis de vérifier
la fermeture par Échap et par la croix de la fenêtre. Le journal fourni indique
pygame-ce 2.5.8, SDL 2.32.10 et Python 3.15.2. Ces résultats de build et de recette
sont rapportés par l'utilisateur, et non exécutés par l'agent.

## Statut

**Phase 0 validée par l'utilisateur.** Les contrôles automatisés passent et le
build ainsi que les deux modes de fermeture sont confirmés sous Windows.
La CI distante, Linux et macOS n'ont pas été validés par ces résultats.
La phase 1 n'est pas commencée ; son lancement fera l'objet d'une instruction
séparée, conformément au périmètre initial limité à la phase 0.

## Complément — fenêtre adaptée à l'écran

Après la validation initiale, la fenêtre a été rendue redimensionnable et son
format initial adapté à 90 % du bureau. Le cadrage conserve le ratio logique,
avec marges centrées, échelle entière ou réduction pour les petites fenêtres.

Contrôles relancés sous Windows / Python 3.15.2 : Ruff lint et formatage OK,
mypy strict OK, 25 tests réussis, couverture globale 91 % et présentation 98 %.
Les tests incluent plusieurs tailles de bureau, les fenêtres larges et verticales,
la réduction sous 640 × 360 et le rendu après changement de taille de la surface.
Aucune dépendance installée. La recette visuelle de ce nouveau comportement reste
à faire ; le build confirmé plus haut correspond à la version initiale.

## Correction — agrandissement du rendu

Le retour utilisateur relève que l'échelle entière laisse des marges excessives.
Le rendu utilise désormais le plus grand facteur proportionnel possible, même
fractionnaire. Une fenêtre 1536 × 864 affiche ainsi une image 1536 × 864 ; une
fenêtre 1000 × 800 affiche une image 1000 × 562 centrée, sans déformation.
Ce comportement remplace la préférence précédente pour l'échelle entière.

Vérification sous Windows / Python 3.15.2 : 26 tests réussis, Ruff lint/formatage
et mypy strict OK. Couverture globale 91 %. Aucun paquet installé. La recette
visuelle du rendu corrigé reste à confirmer par l'utilisateur.

## Correction — suppression des bandes noires

À la demande de l’utilisateur, le cadrage couvre désormais toute la fenêtre,
sans étirement : le facteur d’échelle couvre les deux dimensions, puis les
débordements sont recadrés au centre. Cette décision remplace le cadrage avec
marges précédent. Le calcul arrondit les dimensions vers le haut pour éviter
une bande résiduelle d’un pixel.

Contrôles Windows / Python 3.15.2 : 30 tests réussis, Ruff lint/formatage et mypy
strict OK. Les tests vérifient également la couverture des quatre bords sur des
fenêtres larges, verticales et de dimensions impaires. Aucune dépendance installée.
La recette visuelle du cadrage corrigé reste à confirmer.
