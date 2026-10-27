# Ressources du jeu

Les PNG de ce dossier sont utilisés par Pygame. Les cartes sont des peintures, les personnages et attaques sont des couches séparées. Les particules, ombres et éléments d’interface restent dynamiques.

## Style

Illustration fantasy 2D aux contours doux : verts sauge, bois chauds, pierre et accents turquoise. Les planches ont été créées avec l'outil intégré **image_gen**, puis découpées, nettoyées et normalisées pour les dimensions du jeu. Les prompts sont conservés dans [PROMPTS.md](PROMPTS.md), [COMBAT_PROMPTS.md](COMBAT_PROMPTS.md) et [WORLD_PROMPTS.md](WORLD_PROMPTS.md).

[Personnages et objets](previews/catalogue.png) · [Attaques](previews/attack-poses.png) · [Prologue](previews/prologue.png) · [Environnements](previews/environments.png).

## Organisation

- `maps/` : peintures du camp, de la caravane, du pont, des ruines, de la porte fermée/ouverte et du décor de combat.
- `prologue/` : Cloud, Sephiroth et le fond de Nibelheim, réservés à la mise en scène du prologue.
- `animations/hero_sword_body.png` et `hero_sword_hair.png` : huit poses du coup d'épée, avec cheveux recolorables.
- `animations/wolf_claw.png` : huit poses du coup de patte.
- `animations/slime_jump.png` : huit poses de préparation, bond et écrasement.

- `characters/hero_body.png` : corps du héros, quatre directions et quatre poses par direction.
- `characters/hero_hair.png` : cheveux en nuances de gris, avec la même grille et les mêmes points d'ancrage. Pygame applique la couleur choisie dans le créateur puis superpose la couche au corps.
- `characters/` : Mira, le marchand et le voyageur.
- `enemies/` : loup, flan et Sentinelle, chacun avec quatre poses.
- `props/` : maison, tente, chariot, porte fermée/ouverte, arbre, feu, colonne, autel, rocher, panneau et caisse.
- `tilesets/dalmasca.png` : bibliothèque de textures conservée comme ressource de création ; les cartes du jeu utilisent désormais les peintures complètes.
- `effects/fire.png` : huit images du projectile de feu.
- `sources/` : planches originales de génération, conservées pour les retouches graphiques ; elles ne sont pas chargées pendant le jeu.
- `previews/` : catalogue de contrôle, également hors du chargement du jeu.

## Modifier une image

Les classes jouables sont décrites dans [CLASSES_PROMPTS.md](CLASSES_PROMPTS.md), avec un [aperçu des équipements et gestes](previews/classes.png). Chaque tenue possède ses planches `classes/<classe>.png`, `<classe>_hair.png`, `<classe>_action.png` et `<classe>_action_hair.png`. Les huit armes sont dans `weapons/`. Le manifeste fournit les repères `hands` par pose et le point `grip` par arme : ces calques sont assemblés et tournés en mémoire, pour conserver les variantes d’équipement pendant les animations.

Mira utilise également le style peint actuel : quatre poses en `characters/mira.png` et un portrait dédié en `characters/portrait_mira.png`. Voir [l’aperçu](previews/mira.png) et le [prompt de génération](MIRA_PROMPT.md).

La refonte du héros, d’Oren, du voyageur et de la Sentinelle emploie des proportions adultes et des matières peintes détaillées. Voir [l’aperçu](previews/character-refresh.png) et les [prompts de génération](CHARACTER_REFRESH_PROMPTS.md). Les portraits `characters/portrait_*.png` sont réservés aux dialogues. `animations/sentinel_strike.png` contient huit poses de frappe à la glaive ; la pose de contact est synchronisée avec les dégâts.

Les dimensions des cases, le nombre de colonnes et de lignes ainsi que la taille d'affichage sont décrits dans `manifest.json`. Les images sont des PNG RGBA avec un canal alpha. Les coordonnées des images d'animation sont calculées à partir de la grille du manifeste.

Pour remplacer un dessin en conservant le manifeste, gardez exactement la même taille de planche et les mêmes points d'ancrage des pieds. Les planches du corps et des cheveux doivent conserver une grille identique. Pour changer la résolution native, mettez à jour `cell` et conservez `display_size` si la taille à l'écran doit rester la même.

Les planches d’action possèdent aussi des points `anchors` par pose : ils indiquent où les pieds doivent rester fixés malgré le débordement d’une lame ou d’une patte. Une seule échelle est appliquée à toutes les poses pour conserver l’amplitude d’un saut ou d’un écrasement.

Les personnages du héros utilisent les lignes `down`, `left`, `up`, `right`, et les colonnes correspondent aux quatre poses de marche. Les autres personnages et ennemis utilisent une seule ligne de quatre poses. La porte utilise deux colonnes : fermée puis ouverte.

Les fichiers sont chargés une fois, les images d'animation sont découpées et mises en cache. Le redimensionnement doux permet de conserver le style illustré dans les aperçus, combats et fenêtres redimensionnées. Relancez le jeu après une modification d'asset pour vider les caches.
