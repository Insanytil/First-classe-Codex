# Cahier des charges — RPG Fantasy 2D (Python / Pygame)

> **Version :** 1.0  
> **Destinataire :** Codex / équipe de développement  
> **Nature :** Spécification fonctionnelle, technique et architecturale  
> **Objectif :** Construire un JRPG 2D solo, inspiré des Final Fantasy classiques, avec une POO exemplaire, un domaine indépendant de Pygame, et une réalisation incrémentale.

## 0. Instructions de travail pour Codex

Ce document est la référence du projet. Avant de coder :

1. Examiner la structure existante du dépôt et préserver les choix déjà en place lorsqu'ils respectent ce cahier des charges.
2. Proposer un plan d'implémentation découpé en petites étapes vérifiables. Commencer par la **phase 0**, et ne pas implémenter tout le jeu d'un seul coup.
3. Pour chaque étape : expliquer les décisions de conception, coder, ajouter les tests, exécuter les contrôles disponibles, puis résumer le résultat et les limites.
4. Maintenir des frontières d'architecture strictes. **`domain/` et `application/` ne doivent jamais importer `pygame`.**
5. Utiliser les annotations de types, la composition et l'injection explicite de dépendances. Favoriser des abstractions justifiées, pas des couches artificielles.
6. Séparer strictement le **contenu** (définitions JSON), l'**état de jeu** (instances métier), la **persistance** et la **présentation**.
7. Créer des placeholders temporaires quand les assets définitifs n'existent pas ; ne jamais bloquer l'avancement du moteur sur leur génération.
8. Garder le projet exécutable et les tests au vert après chaque étape.
9. Lorsqu'une règle n'est pas spécifiée, choisir une solution simple, cohérente et documenter ce choix dans une ADR (`docs/adr/`). Ne pas inventer des fonctionnalités massives hors périmètre MVP.
10. Ne jamais déclarer une phase terminée sans satisfaire ses critères d'acceptation.

**Premier travail attendu :** analyser le dépôt, définir le squelette Python installable, les frontières de modules, la configuration de qualité (pytest, Ruff, typage), l'entrée Pygame minimale, les premières vérifications d'architecture et un README de démarrage. **Ne pas commencer par créer les dizaines de classes du jeu.**

---

## 1. Vision et portée

Créer un RPG fantasy 2D solo inspiré de **Final Fantasy VI**, **Final Fantasy IX** et **Chrono Trigger** : exploration de cartes interconnectées, équipe de héros, combat tactique au tour par tour, inventaire, équipements, compétences, progression, loot, quêtes, dialogues, PNJ, magasins, boss et sauvegardes.

### Objectifs

- **Gameplay :** un JRPG agréable, stratégique, extensible et jouable de bout en bout.
- **Architecture :** POO de haute qualité ; séparation Domain / Application / Infrastructure / Presentation, SOLID appliqué avec discernement.
- **Testabilité :** toutes les règles métier fonctionnent en Python pur, sans fenêtre ni dépendance Pygame.
- **Extensibilité :** ajouter classes, personnages, ennemis, objets, sorts, cartes et quêtes principalement via des données et composants réutilisables.
- **Production :** assets générés, contrôlés, normalisés et liés au contenu via des identifiants.

### Décisions initiales

| Sujet | Décision |
|---|---|
| Genre | JRPG fantasy 2D solo |
| Vue exploration | Dessus, cartes à tuiles |
| Combat | Écran dédié, tour par tour, ordre d'action basé sur les règles de vitesse |
| Plateformes cibles | Windows, Linux, macOS |
| Langage | Python 3.12+ |
| Rendu, entrée, son | Pygame |
| Résolution logique initiale | 640 × 360, mise à l'échelle entière si possible |
| Cible de fluidité | 60 FPS sur machine de référence à définir |
| Tuiles | 32 × 32 pixels |
| Format de contenu | JSON validé au chargement |
| Sauvegarde | JSON versionné, écrit de façon sûre |
| Tests | pytest |
| Qualité | Ruff, mypy ou Pyright, couverture, CI |
| Distribution | Exécutable desktop (outil à valider, ex. PyInstaller) |

---

## 2. Fonctionnalités métier

### 2.1 Personnages, classes et progression

Chaque personnage jouable possède une **identité stable**, un nom, une classe, un niveau, des points d'expérience, des HP/PV, MP/PM, des caractéristiques, compétences, équipements et états actifs.

Statistiques de départ : `hp`, `mp`, `strength`, `defense`, `magic`, `resistance`, `speed`, `accuracy`, `evasion`, `critical`.

Les statistiques effectives prennent en compte valeurs de base, équipement, bonus et malus. Les invariants (PV bornés, dépenses valides, progression cohérente) sont maintenus par le domaine.

Classes initiales : **guerrier** (défense/attaque physique), **mage** (éléments et dégâts magiques), **soigneur** (soins, soutien), **voleur** (vitesse, esquive et critiques).

- CHAR-01 — Créer et gérer plusieurs personnages jouables. **MVP**
- CHAR-02 — Affecter une définition de classe et ses restrictions. **MVP**
- CHAR-03 — Caractéristiques de base, effectives, PV/PM. **MVP**
- CHAR-04 — Expérience et montée en niveau. **MVP**
- CHAR-05 — Apprentissage et utilisation des compétences. **MVP**
- CHAR-06 — Équipement/déséquipement et recalcul des statistiques. **MVP**
- CHAR-07 — Altérations d'état. **MVP**
- CHAR-08 — Arbres ou parcours de progression individuels. **V2**
- CHAR-09 — Classes évoluées / jobs. **V3**

**Principe POO :** les classes de gameplay sont des définitions de contenu ou des stratégies de progression, **pas** une hiérarchie systématique de sous-classes `Warrior(Character)`, `Mage(Character)`, etc.

### 2.2 Équipe

- Groupe actif de **4** personnages maximum ; personnages recrutés supplémentaires en réserve (la réserve complète peut arriver en V2).
- Ordre de l'équipe modifiable, leader d'exploration identifiable.
- HP, MP, équipement, états et XP individualisés.
- Défaite si tous les combattants actifs sont hors combat, sauf règle scénaristique explicite.
- `Party` doit protéger ses propres invariants (unicité des membres, taille limite, etc.).

### 2.3 Inventaire

Catégories : consommables, armes, armures, accessoires, objets de quête, matériaux, objets spéciaux.

- INV-01 — Ajouter / retirer des objets.
- INV-02 — Gérer les quantités empilables.
- INV-03 — Refuser quantités négatives et suppressions impossibles.
- INV-04 — Utiliser un consommable sur une cible valide.
- INV-05 — Trier / filtrer dans l'interface.
- INV-06 — Gérer objets uniques et instances individuelles si nécessaire.
- INV-07 — Empêcher l'utilisation d'un objet incompatible avec le contexte.
- INV-08 — Transférer un équipement entre inventaire et personnage de manière atomique.

**Distinction essentielle :** `ItemDefinition` décrit un type, `ItemInstance` représente au besoin un exemplaire unique, et une pile d'objets identiques possède sa quantité. Ne pas donner arbitrairement une identité d'instance à chaque potion.

### 2.4 Équipements

Emplacements : `weapon`, `off_hand`, `head`, `body`, `accessory_1`, `accessory_2`.

Exigences : restrictions de classes, bonus/malus de stats, résistances, effets passifs possibles ; maintien d'un état cohérent lors des transferts ; affichage comparatif dans l'UI. Sets, enchantements et améliorations reportés à V2/V3.

### 2.5 Combat au tour par tour

Actions : **Attaquer**, **Compétence / Magie**, **Défendre**, **Objet**, **Fuir**, **Passer**.

Fonctionnalités :

- Ordre d'action calculé à partir de règles explicites et testables.
- Commandes validées avant mutation : acteur actif, coût de MP, ciblage, disponibilité, restrictions d'état.
- Cibles ennemies/alliées, individuelles/multiples.
- Dégâts physiques et magiques, soins et résurrection.
- Critiques, précision, esquive, défense, vulnérabilités, résistances et immunités élémentaires.
- États temporaires (poison, brûlure, sommeil, paralysie, silence, buffs/debuffs) avec durée, déclenchement et règles d'empilement.
- Actions des ennemis passant par les **mêmes validations** que celles du joueur.
- Conditions de victoire/défaite/fuite, récompenses et journal d'événements.
- Résultat métier de chaque action indépendant de ses animations.

**Machine à états initiale :**

`INITIALIZING → TURN_READY → AWAITING_ACTION → RESOLVING → TURN_END → (TURN_READY | FINISHED)`.

Les transitions illégales sont rejetées sans état partiellement modifié. Une commande produit un résultat structuré (`BattleActionResult`) et des événements métier exploitables par Pygame.

**IA :** profils basique (choix valide), tactique (priorités et faiblesses), boss à phases (V2). Initialement, privilégier l'IA basique avec stratégie injectable.

**Compétences :** assemblage de coûts, règles de ciblage et effets typés (dégâts, soins, état, bonus, etc.). Éviter les branches géantes sur le nom d'une compétence.

### 2.6 Loot et récompenses

- Tables de loot pondérées, drops garantis et aléatoires.
- Niveaux de rareté : commun, inhabituel, rare, épique, légendaire.
- Expérience et monnaie après victoire ; récompenses de quêtes et coffres.
- Récompense d'un coffre unique **une seule fois**, sans duplication par sauvegarde/chargement.
- Source aléatoire injectable pour tests déterministes.

### 2.7 Exploration, cartes et monde

- Monde en **cartes interconnectées** : village, routes/forêt, grotte/ruines, donjon/château à terme.
- Tuiles, couches de rendu, collisions, caméra et transitions entre zones.
- Personnage contrôlable, points d'apparition, PNJ, coffres, déclencheurs de combat et événements.
- État du monde persistant (coffres ouverts, événements joués, progression).
- Architecture compatible ultérieurement avec pathfinding, météo et cycle jour/nuit.

Références : `MAP-01` déplacement ; `MAP-02` caméra ; `MAP-03` collisions ; `MAP-04` transitions ; `MAP-05` PNJ ; `MAP-06` coffres ; `MAP-07` combats ; `MAP-08` événements ; `MAP-09` couches ; `MAP-10` persistance du monde.

### 2.8 PNJ et dialogues

- Dialogues à nœuds avec choix, préconditions et conséquences.
- PNJ fournissant quête, commerce, objet, information ou événement.
- Réponses conditionnelles à l'avancement de l'histoire.
- Les fichiers JSON de dialogues **n'exécutent pas du code Python arbitraire** : ils déclarent des opérations connues et validées.

### 2.9 Quêtes

Types : principales, secondaires, personnages, exploration, collecte, chasse.

États initiaux : `LOCKED → AVAILABLE → ACTIVE → COMPLETED → REWARDED`. Échec/abandon en extension si nécessaire.

Objectifs paramétrables : éliminer des ennemis, collecter/livrer, visiter un lieu, parler à un PNJ, ouvrir/interagir, tuer un boss, terminer une autre quête.

- Mise à jour via événements métier (`EnemyDefeated`, `ItemCollected`, `MapEntered`, etc.).
- Progression sauvegardée, objectifs vérifiés et récompenses distribuées **exactement une fois**.
- Les quêtes ne dépendent pas des classes de présentation ou d'un écran de combat.

### 2.10 Économie / marchands

Monnaie globale, boutiques proposant achat/vente avec prix, stocks et restrictions. Transactions contrôlées et atomiques : impossible d'acheter sans fonds ou de vendre un objet absent.

### 2.11 Sauvegarde / chargement

Minimum **3 emplacements**. Conserver : personnages, niveaux, états, équipe, équipement, inventaire, monnaie, carte et position, quêtes, état du monde, drapeaux narratifs, temps de jeu et version du format.

- Validation des données chargées ; erreurs explicites.
- Écriture vers fichier temporaire puis remplacement atomique quand le système le permet.
- Tests de sauvegarde/chargement (*round-trip*) et de fichier corrompu.
- Stratégie de migration lorsque le schéma évolue.
- Ne pas mélanger fichiers de définition des objets et instantané de l'état du joueur.

### 2.12 Interfaces et contrôles

Écrans : menu principal, exploration, combat, inventaire, équipements, fiches de personnages, équipe, journal de quêtes, carte, commerce, sauvegarde et options.

Contrôles clavier centralisés et reconfigurables à terme ; manette en V2. L'interface doit rester cohérente et afficher les motifs d'actions indisponibles.

---

## 3. Architecture logicielle — exigences majeures

### 3.1 Couches et direction des dépendances

```text
           ┌───────────────────────────────┐
           │ Presentation (Pygame)          │
           │ Scenes, render, input, UI      │
           └───────────────┬───────────────┘
                           │
                           v
           ┌───────────────────────────────┐
           │ Application                    │
           │ Use cases, commands, ports     │
           └───────────────┬───────────────┘
                           │
                           v
           ┌───────────────────────────────┐
           │ Domain                         │
           │ Entities, value objects, rules │
           └───────────────────────────────┘

Infrastructure (JSON, asset pipeline, RNG, persistence)
  implements ports defined by inner layers and is wired
  at the composition root / bootstrap.
```

Règles :

1. Le **domaine** ne dépend ni de Pygame, ni de JSON, ni de fichiers, ni d'horloge réelle.
2. L'**application** orchestre les cas d'utilisation et définit des ports vers l'extérieur.
3. L'**infrastructure** implémente les ports de stockage, contenu, random et configuration.
4. La **présentation** convertit actions utilisateur ↔ commandes métier et résultats ↔ animations.
5. L'assemblage des dépendances se fait au point d'entrée (`bootstrap.py`).
6. Les tests de domaine ne doivent pas nécessiter l'initialisation d'un affichage.

### 3.2 Modèle de domaine candidat

**Entités :** `Character`, `Party`, `Inventory`, `EquipmentSet`, `Battle`, `Combatant`, `Quest`, `WorldState`, `GameSession`.

**Définitions immuables :** `CharacterDefinition`, `ClassDefinition`, `EnemyDefinition`, `ItemDefinition`, `SkillDefinition`, `QuestDefinition`, `MapDefinition`.

**Objets-valeurs :** `CharacterStats`, `MapPosition`, `ItemQuantity`, `DamageResult`, `BattleTarget`, `ExperienceReward`, résistances élémentaires.

**Services de domaine lorsque nécessaires :** `DamageCalculator`, `TurnOrderCalculator`, `LootGenerator`, `ExperienceCalculator`, `EquipmentRules`.

**Ports possibles :** `SaveRepository`, `ContentRepository`, `RandomSource`, `Clock`, `EventPublisher`. Les interfaces graphiques (`InputSource`, `AssetProvider`) restent à la périphérie et ne sont pas des contrats du domaine.

Il s'agit de **concepts à affiner** : ne pas créer une classe pour chaque nom si elle n'a pas de comportement, de données ou de frontière d'abstraction justifiés.

### 3.3 Principes POO

- Responsabilité unique, cohésion élevée, couplage faible.
- Encapsulation et invariants maintenus par les objets responsables.
- Préférer **composition** et stratégie à une profondeur d'héritage artificielle.
- Utiliser `dataclass(frozen=True)` pour les objets-valeurs adaptés ; ne pas rendre automatiquement toutes les entités immuables.
- `Enum`/types explicites pour les états, événements, slots, raretés.
- Polymorphisme au niveau des comportements réels (IA, calculs, effets, validation), pas pour distinguer chaque objet du catalogue.
- Injection de dépendances simple et explicite, sans conteneur DI surdimensionné.
- Erreurs métier identifiables (`InsufficientMana`, `InvalidTarget`, etc.) plutôt qu'exceptions génériques silencieuses.
- Transactions métier sûres (équipement, boutique, récompenses).
- Documenter les compromis dans des ADR courtes.

### 3.4 Contrat de combat

Le cœur métier doit exposer un mécanisme conceptuellement semblable à :

```python
result = battle.execute(command, random_source)
# result contient les changements / événements permettant
# à la présentation de jouer les animations correspondantes.
```

La signature précise appartient à l'implémentation. Un test doit pouvoir enchaîner un combat complet sans importer Pygame. Les animations ne calculent jamais les dégâts.

### 3.5 Événements métier

Événements envisageables : `EnemyDefeated`, `BattleWon`, `ItemCollected`, `LevelGained`, `QuestObjectiveCompleted`, `MapEntered`, `ChestOpened`.

Un dispatcher synchrone, typé et local suffit au MVP. La livraison d'un événement ne doit pas permettre de verser accidentellement deux fois les récompenses. Les opérations composites nécessitant cohérence sont orchestrées au niveau applicatif.

### 3.6 Organisation du code

```text
fantasy_rpg/
├── pyproject.toml
├── README.md
├── docs/
│   ├── requirements/
│   ├── architecture/
│   ├── game-design/
│   └── adr/
├── src/
│   └── fantasy_rpg/
│       ├── domain/
│       │   ├── characters/
│       │   ├── party/
│       │   ├── inventory/
│       │   ├── equipment/
│       │   ├── combat/
│       │   ├── skills/
│       │   ├── effects/
│       │   ├── quests/
│       │   ├── world/
│       │   ├── economy/
│       │   └── shared/
│       ├── application/
│       │   ├── commands/
│       │   ├── queries/
│       │   ├── use_cases/
│       │   ├── ports/
│       │   └── events/
│       ├── infrastructure/
│       │   ├── persistence/
│       │   ├── content/
│       │   ├── random/
│       │   └── configuration/
│       ├── presentation/
│       │   └── pygame/
│       │       ├── scenes/
│       │       ├── rendering/
│       │       ├── animations/
│       │       ├── ui/
│       │       ├── input/
│       │       └── audio/
│       └── bootstrap.py
├── assets/
│   ├── characters/
│   ├── enemies/
│   ├── tilesets/
│   ├── backgrounds/
│   ├── ui/
│   ├── animations/
│   ├── music/
│   └── sounds/
├── content/
│   ├── characters/
│   ├── classes/
│   ├── enemies/
│   ├── items/
│   ├── skills/
│   ├── loot_tables/
│   ├── quests/
│   ├── dialogues/
│   └── maps/
├── tools/
│   ├── asset_pipeline/
│   └── content_validation/
└── tests/
    ├── unit/
    ├── integration/
    ├── architecture/
    └── end_to_end/
```

Cette arborescence est indicative : éviter les dossiers vides et réorganiser par fonctionnalités si cela favorise la cohésion.

### 3.7 Patterns potentiellement adaptés

| Pattern | Utilisation justifiée |
|---|---|
| State | États du combat / scènes |
| Strategy | Règles de ciblage et comportements IA |
| Command | Actions de jeu validables |
| Factory | Création d'instances à partir de définitions |
| Repository | Persistance / chargement |
| Domain Events / Observer | Découplage inter-systèmes |
| Dependency Injection | Assemblage des services |
| Composite | Effets composés si besoin réel |

Ne pas imposer de pattern s'il complique davantage le code qu'il ne le simplifie.

---

## 4. Contenu et assets générés

### 4.1 Direction artistique

- Pixel art fantasy cohérent, inspiré des JRPG 16-bit sans copier d'assets protégés.
- Vue du dessus pour l'exploration ; écran dédié pour les affrontements.
- Sprites lisibles, animations courtes, menus clairs.
- Convention constante pour la perspective, proportions, palette et résolution.

### 4.2 Formats et conventions

| Ressource | Convention proposée |
|---|---|
| Personnages | PNG transparent, spritesheet d'animations |
| Ennemis | PNG transparent, éventuellement plusieurs frames |
| Tuiles | PNG, grille 32 × 32 |
| Fonds | PNG |
| Éléments UI | PNG et polices avec licence adaptée |
| Musiques | OGG |
| Effets sonores | WAV ou OGG |
| Métadonnées | JSON |

### 4.3 Pipeline

1. Rédiger une charte artistique commune et des prompts de référence.
2. Générer les assets (personnages, ennemis, environnement, icônes, UI).
3. Normaliser dimensions, fond transparent, marges, spritesheets et noms.
4. Vérifier visuellement les perspectives et les animations : la génération n'est pas garantie exploitable telle quelle.
5. Enregistrer un `asset_id` stable dans un manifeste ; ne jamais lier la logique métier à un chemin d'image.
6. Documenter provenance, licences/droits et transformations.

Les placeholders sont autorisés pendant le développement, et un contrôleur de chargement doit signaler les ressources manquantes proprement.

---

## 5. Données de jeu et validations

Les définitions de contenu sont stockées en JSON et chargées via un adaptateur validant types, champs obligatoires, références et règles métiers élémentaires.

Exemple **indicatif** d'item :

```json
{
  "id": "iron_sword",
  "name": "Épée de fer",
  "type": "equipment",
  "rarity": "common",
  "equipment_slot": "weapon",
  "stat_modifiers": {"strength": 5},
  "allowed_classes": ["warrior", "paladin"],
  "sell_price": 25,
  "asset_id": "items/iron_sword"
}
```

Les identifiants sont persistants. Les modifications de contenu susceptibles d'affecter les sauvegardes requièrent migrations ou compatibilité. Des outils de validation doivent détecter références absentes, doublons d'identifiants, nombres invalides, probabilités incohérentes et assets manquants.

---

## 6. Qualité, outils et tests

### Outils

- `pytest` pour unités/intégration, `pytest-cov` pour la couverture.
- `ruff` pour lint et formatage.
- `mypy` ou `pyright` (choix unique documenté) pour le typage.
- Git + GitHub Actions pour contrôle à chaque modification.
- Packaging desktop en fin de MVP.
- Outil de cartes externe tel que Tiled possible, via format de données importé/validé.

### Tests obligatoires du domaine

- Impossible de dépenser plus de MP que disponibles.
- Un personnage KO ne peut pas agir, sauf compétence/règle autorisée.
- Impossible d'agir deux fois pour un même tour.
- Ciblage et ordre des tours valides.
- Dégâts, critiques, résistances et effets reproductibles avec aléatoire injecté.
- Un consommable absent ne peut pas être utilisé.
- Un équipement incompatible ne peut pas être équipé.
- Les échanges inventaire/équipement ne créent ni ne détruisent des objets involontairement.
- Les achats/ventes insuffisamment financés sont rejetés.
- Un coffre unique et une quête ne donnent leurs récompenses qu'une fois.
- Sauvegarder puis charger restitue l'état attendu ; un fichier corrompu est correctement signalé.
- Aucun import Pygame depuis `domain/` ou `application/`.

**Objectif :** viser 90 % de couverture dans les modules métier les plus critiques, sans confondre couverture et qualité. Exiger tests pertinents, typage, lint et absence de régressions.

---

## 7. MVP : contenu et parcours complet

Le MVP doit durer environ **30 à 60 minutes** et être réalisable de bout en bout.

| Système | Contenu MVP |
|---|---|
| Personnages | 4 héros, 4 classes |
| Équipe | 4 actifs |
| Exploration | 3 cartes interconnectées |
| Ennemis | 5 types + 1 boss |
| Compétences | 12 |
| Objets | 15 |
| Équipements | 10 |
| Quêtes | 1 principale + 3 secondaires |
| PNJ | 5 interactifs |
| Combat | Tour par tour, IA simple, effets et loot |
| Inventaire | Consommables et équipement |
| Sauvegardes | 3 slots |

### Parcours MVP

1. **Village** : rencontre des personnages, équipement, PNJ, boutique et prise de quête.
2. **Forêt** : exploration, rencontres, coffres, loot, quêtes secondaires.
3. **Ruines** : progression, boss, artefact final et validation de la quête principale.
4. **Fin jouable** : récompenses, progression et possibilité de sauvegarder/recharger.

Le jeu doit rester fonctionnel à chaque jalon et ne pas nécessiter de produire toute la bibliothèque d'assets avant les tests.

### Extensions

**V2 :** réserve de personnages, monde élargi, IA tactique, craft, quêtes à embranchements, compétences passives, journal enrichi, bestiaire, manette.

**V3 :** jobs évolués, invocations, combinaisons de compétences, boss multi-phases, réputation, événements dynamiques, systèmes avancés d'équipement.

---

## 8. Feuille de route d'implémentation pour Codex

### Phase 0 — Fondations

- [ ] Initialiser projet Python sous `src/`, packaging et point d'entrée.
- [ ] Configurer pytest, Ruff, typage et CI.
- [ ] Poser les frontières Domain / Application / Infrastructure / Presentation.
- [ ] Créer une fenêtre Pygame minimale et sa boucle (avec fermeture propre).
- [ ] Ajouter un test d'architecture interdisant Pygame dans le domaine et l'application.
- [ ] Écrire README (installation, lancer, tests, qualité) et première ADR.

**Livrable :** fenêtre minimale + outil de test et d'analyse exécutables.

### Phase 1 — Fondations métier

- [ ] Caractéristiques et objets-valeurs.
- [ ] Personnages, classes et progression.
- [ ] Équipe et invariants.
- [ ] Inventaire, items et équipements.
- [ ] Jeux de données de test et couverture unitaire.

**Livrable :** manipuler des personnages, objets et équipements sans interface graphique.

### Phase 2 — Combat autonome

- [ ] États, commandes, validation et ordonnancement des tours.
- [ ] Calcul de dégâts, compétences, effets et ressources.
- [ ] IA ennemie basique.
- [ ] Conditions de victoire/défaite/fuite.
- [ ] Loot, récompenses, événements et tests de combats complets.

**Livrable :** combat simulable automatiquement en Python pur, déterministe à graine fixe.

### Phase 3 — UI de combat Pygame

- [ ] `BattleScene`, affichage combattants et UI des actions.
- [ ] Adaptation événements métier → animations/effets visuels.
- [ ] Navigation clavier, journal et feedback de validation.

**Livrable :** une bataille jouable avec placeholders.

### Phase 4 — Exploration

- [ ] Cartes, tiles, caméra et collisions.
- [ ] Interactions, transitions, rencontres et PNJ.
- [ ] Monde persistant pour coffres et événements.

**Livrable :** déambuler entre 3 cartes, interagir et déclencher un combat.

### Phase 5 — Boucle de progression

- [ ] Quêtes, objectifs, dialogues et événements.
- [ ] Boutiques, coffres et transactions.
- [ ] Menu inventaire/équipements/personnages.
- [ ] Sauvegardes/chargements validés et versionnés.

**Livrable :** mini-aventure complète jouable avec persistance.

### Phase 6 — Contenu et finition

- [ ] Charte visuelle et intégration des assets générés.
- [ ] Contenu du village, de la forêt et des ruines.
- [ ] Boss, quêtes, équilibrage et simulations.
- [ ] Son, interface finale, performances, corrections.
- [ ] Build desktop et guide utilisateur.

**Livrable :** MVP distribuable de 30–60 minutes.

**Règle de progression :** valider chaque phase avant la suivante. Développer les fonctionnalités verticalement et éviter l'introduction prématurée de systèmes V2/V3.

---

## 9. Exigences non fonctionnelles

| Axe | Exigence | Critère de contrôle |
|---|---|---|
| Performances | Cible de 60 FPS | Mesures sur la configuration cible |
| Portabilité | Windows / Linux / macOS | Exécutions de validation |
| Couplage | Zéro Pygame dans les règles métier | Tests d'architecture |
| Extension | Ajouter du contenu sans modifier les systèmes centraux | Test d'ajout d'item/ennemi/compétence |
| Fiabilité | Sauvegarde sûre, validation au chargement | Tests round-trip/corruption |
| Reproductibilité | RNG injectable | Combat identique avec même graine |
| UX | Navigation claire au clavier | Tests manuels des parcours |
| Données | Aucun Python arbitraire depuis JSON | Validation des schémas |
| Traçabilité | Logs et erreurs exploitables | Scénarios de panne |

---

## 10. Risques, arbitrages et garde-fous

| Risque | Mitigation |
|---|---|
| Périmètre trop grand | MVP et étapes courtes |
| Surarchitecture | Abstractions seulement si justifiées |
| Couplage Pygame/métier | Tests d'architecture et ports explicites |
| Multiplication des classes | Composition et données de définition |
| Explosion des cas de compétences | Effets typés/composables |
| Assets incohérents | Charte et pipeline de validation |
| Déséquilibre | Simulations de combat automatisées |
| Régressions | CI, tests de domaine et revues |
| Perte de sauvegardes | Format versionné, écriture sûre, migrations |
| Duplication de loot | Règles de récompense idempotentes |

---

## 11. Critères de recette MVP

### Architecture
- [ ] Le moteur métier fonctionne sans Pygame.
- [ ] Les dépendances entre couches sont contrôlées automatiquement.
- [ ] Les règles importantes sont testées sans UI.
- [ ] L'ajout de contenu passe majoritairement par définitions structurées.

### Gameplay
- [ ] Le joueur se déplace sur les trois cartes et interagit avec des PNJ.
- [ ] Quatre héros participent aux combats et peuvent progresser.
- [ ] Les actions, compétences, ressources et états sont cohérents.
- [ ] Un boss peut être vaincu et l'aventure terminée.

### Inventaire / monde / quêtes
- [ ] Le joueur récolte, consomme et équipe les objets.
- [ ] Les restrictions d'équipement sont respectées.
- [ ] Les objectifs des quêtes progressent correctement.
- [ ] Coffres et quêtes ne dupliquent jamais leurs récompenses.

### Robustesse
- [ ] Sauvegarde/chargement sur trois emplacements.
- [ ] Les contenus JSON sont validés, les erreurs expliquées.
- [ ] Les tests, le lint et le typage passent.
- [ ] Aucun défaut bloquant connu n'empêche de terminer le MVP.

### Livraison
- [ ] Menu principal, exploration, combat, inventaire, équipements, personnages, quêtes et options accessibles.
- [ ] Assets cohérents et intégrés.
- [ ] README et documentation d'extension à jour.
- [ ] Exécutable livré sur la ou les plateformes effectivement validées.

---

## 12. Livrables finaux

1. Code source complet du moteur RPG et de l'application Pygame.
2. Documentation d'architecture (dépendances, responsabilités, ADR).
3. Document de game design : statistiques, formules, effets, équilibre.
4. Assets et métadonnées organisés, traçables et contrôlés.
5. Contenu JSON validé (personnages, monstres, cartes, quêtes, etc.).
6. Tests unitaires, intégration, architecture et CI.
7. Sauvegardes fiables, versionnées.
8. MVP exécutable.
9. Guide d'extension du jeu (ajout d'ennemis, compétences, items, cartes et quêtes).

---

## 13. Décisions architecturales de départ

1. **Le moteur de combat est prioritaire** : valider les règles et tests avant les scènes élaborées.
2. **Definitions ≠ Instances ≠ Affichage** : les trois concepts sont distincts.
3. **Composition > héritage excessif** : stratégie, objets-valeurs et entités riches.
4. **Pygame = adaptateur de présentation** : le domaine doit rester utilisable en console ou dans un simulateur.
5. **Vertical slice avant expansion** : terminer une aventure courte avant de multiplier le contenu.
6. **Validation tôt** : assets et JSON validés automatiquement, pas en toute fin de développement.

## 14. Commande initiale suggérée pour Codex

> Lis `CAHIER_DES_CHARGES_RPG_PYGAME_CODEX.md` comme spécification de référence. Inspecte d'abord le dépôt. Propose un plan concis pour la phase 0 et implémente uniquement cette phase : packaging Python sous `src/`, outillage de qualité, structure de couches minimale sans dossiers/classes fictifs, point d'entrée et fenêtre Pygame avec fermeture propre, premiers tests dont une vérification des frontières d'import, README avec commandes de lancement et première ADR. Exécute les tests et contrôles que permet l'environnement, puis explique les décisions techniques et les étapes restantes. Ne commence pas à coder les combats avant validation de la phase 0.
