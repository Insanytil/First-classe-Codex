# ADR 0008 — Réutilisation des sprites et monde peint vivant

## Besoin et références

L'utilisateur demande explicitement de reprendre les monstres et animations de
`poo`, puis de créer des images de cartes vivantes fortement inspirées du prototype.
Les prompts historiques `assets/WORLD_PROMPTS.md` et les rendus du prototype ont
été examinés. Les scènes camp, pont et ruines ont aussi été exécutées/capturées
avec le Pygame existant, via SDL dummy, sans installation et sans modifier `poo`.

## Ressources indépendantes du prototype

Les images de loup, flan, sentinelle, leurs séquences d'attaque, les PNJ, arbres,
piliers et certains accessoires sont copiés à l'identique dans le paquet JRPG.
Le manifeste conserve leur chemin d'origine et leur empreinte SHA-256. Les
peintures de Clairval, de la forêt et de Sylve sont de nouvelles images imagegen,
avec prompts et guides de composition archivés. Le décor de combat est repris
du prototype et cadré sur le sol pour éviter des combattants posés sur l'horizon.

Le catalogue graphique reste en présentation : `PaintedSprites` possède le
chargement, les ancrages et le cache des images redimensionnées. Il vérifie les
dimensions des atlas. `WorldArt` possède les peintures et leur recalage, tandis
que `WorldAmbience` possède le temps et les effets d'ambiance. Le domaine et
l'application ne connaissent aucun de ces objets. Aucune importation de `poo`
n'est ajoutée et les fichiers historiques ne sont pas requis au lancement.

## Géométrie et profondeur

Les guides proviennent des vraies cartes JSON, mais une image générée n'obéit pas
exactement à des coordonnées. Un simple redimensionnement global déplacerait la
rivière ou les passages par rapport aux collisions. `Registration` effectue un
recalage par bandes, continu en position et strictement croissant sur chaque axe.
Les limites du pont, des berges et des murs sont ainsi ramenées aux coordonnées
du monde. Cette transformation est calculée une fois et mise en cache. Les
originaux restent inchangés ; les points de contrôle sont explicites dans
`world_art.REGISTRATIONS`. Une autre peinture peut utiliser un autre recalage.

Le résultat demeure une illustration, pas une segmentation exacte au pixel de
chaque rocher peint. Les rives englobent les sols non praticables ; les tests de
déplacement continuent d'utiliser le JSON. Les coordonnées du monde, les passages,
les coffres et le format des sauvegardes restent inchangés. Les arbres et piliers
sont des calques séparés triés avec les personnages par la profondeur des pieds.
Le toit déjà peint n'est pas redessiné comme un second toit procédural.

Sur les formats dépassant l'étendue d'une carte, les bords peints sont prolongés
pour couvrir la fenêtre, sans bandes noires et sans déplacer les collisions.

## Animation et absence d'effets métier

Les monstres sont associés à leur identifiant de définition, pas à leur place
dans la liste. Les instances actuelles portent la convention `type-numéro`.
Loup et flan ont quatre poses d'attente, puis huit poses d'attaque reprises du
prototype. Les images sont retournées vers les héros, puisque les monstres sont
à gauche dans JRPG. La sentinelle et son attaque sont préparées dans le catalogue,
mais cela n'ajoute pas encore de boss jouable au contenu métier.

`attack_animation` contient une trajectoire et une sélection de pose pures,
inspirées de `poo.graphics.animation`. Griffes et héros utilisent la pose de
contact 4 ; le flan utilise la pose 5 pour sa réception. Toutes rejoignent le même
`Playback.IMPACT`. Le saut distingue hauteur visuelle et position de l'ombre.
Les sorts restent des gestes de lancement sur place ; l'attaque physique approche
la cible puis revient. Aucune pose ne calcule ou ne déclenche les dégâts.

L'ambiance continue au repos et dans les menus : reflets uniquement sur les
cases d'eau, vent et feuilles dans les prés, légère fumée à Clairval, poussières
lumineuses et braseros vacillants sur les murs non praticables des ruines. Les
PNJ changent de pose sans quitter leur position d'interaction. La pause de focus
arrête les mises à jour de la scène. Les effets ne consomment pas le RNG du jeu,
n'enregistrent pas d'événements métier et n'entrent pas dans les sauvegardes.

Les particules sont calculées analytiquement en nombre fixe. Le temps visuel est
borné, les atlas et tailles sont en cache, et la surface transparente d'ambiance
est réutilisée. Il n'y a pas d'accumulation de particules au fil du temps.

## Validation et limites

Tests des empreintes et dimensions, du cache, de l'orientation par identité,
du recalage sans trous, des formats très larges/hauts, des trajectoires et du
contact. Une capture complète de session avant/après rendu prouve la conservation
de l'état sauvegardable, y compris le RNG, pendant que l'image évolue au repos.

`tools/preview_living_world.py` exporte des bandes de captures des vraies scènes
Pygame, lues par `docs/previews/animations.html` sans réseau ni bibliothèque
supplémentaire. Ce livrable facilite la revue des mouvements ; il ne constitue
pas une mesure de FPS du bureau. La phase 6 globale reste en cours.
