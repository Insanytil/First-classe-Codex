# ADR 0007 — Atlas peints originaux et animation en présentation

## Décision

À la demande de l’utilisateur, les nouveaux héros adoptent le rendu peint adulte
des sprites et prompts historiques de `poo`, plutôt qu’une obligation de pixel art.
Les quatre identités sont distinctes : Ari, Lyra, Mira et Nox. Les personnages sont
dessinés avec leurs cheveux et leur arme : la personnalisation visuelle par calques
n’est pas un besoin de ce MVP et ajouterait des contraintes d’alignement inutiles.

Les images sont produites avec l’outil imagegen intégré, avec les planches de
`assets/previews/` comme références artistiques. Les prompts complets, originaux,
rectangles de découpage et empreintes SHA-256 sont conservés. Aucune licence
tierce n’est inventée pour ces créations générées.

## Séparation des responsabilités

`HeroArt` appartient à la présentation. Il charge les ressources embarquées via
`importlib.resources`, sans dépendre du répertoire de lancement. Il ne charge rien
avant le premier dessin et conserve les images découpées/redimensionnées en cache.
Le domaine et l’application restent indépendants des images et de Pygame.

Les identifiants de personnage associent une image à une entité, sans utiliser
l’ordre du groupe : réordonner l’équipe ne change pas l’identité visuelle. Les
personnages extérieurs au catalogue conservent le dessin générique existant.

L’animation lit le résultat déjà résolu par le contrôleur. La pose de contact
coïncide avec `Playback.IMPACT` ; elle ne calcule ni ne déclenche les dégâts.
L’exploration choisit la direction et la pose à partir de l’état visuel existant.

## Préparation et limites

Les grilles générées ne sont pas suffisamment exactes pour être chargées telles
quelles. `tools/prepare_hero_art.py` extrait leurs silhouettes opaques, sélectionne
24 poses par héros et produit des cases de 192 × 128 px, avec un ancrage commun
aux pieds (96, 120). Le facteur d’échelle reste constant entre les poses d’un héros.
La rangée latérale gauche de Mira et Nox est retournée horizontalement ; huit
poses d’action supplémentaires de Nox sont écartées. Les sources restent intactes.

Les tests vérifient transparence, absence de débordement, intégrité des fichiers,
cache et synchronisation. Ces contrôles ne remplacent pas une validation humaine
de la qualité du mouvement. Ce lot couvre les héros ; les ennemis, PNJ et décors
font encore partie du travail artistique de phase 6.
