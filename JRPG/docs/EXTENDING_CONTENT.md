# Étendre le contenu de JRPG

Les chemins ci-dessous sont relatifs à `JRPG/`. Après modification, lancer :

```bash
uv run --no-sync python tools/audit_content.py
uv run --no-sync pytest --basetemp=.test-tmp
uv run --no-sync ruff check .
uv run --no-sync mypy
```

Le contenu doit être dans le paquet `src/JRPG/infrastructure/content/`, jamais
dans un dossier attendu relativement au répertoire de lancement. Les identifiants
sont stables et uniques dans leur catalogue. Les textes JSON ne sont pas exécutés.

## Compétence

Ajouter une entrée à `combat.json`, puis référencer son identifiant dans `skills`
du héros ou de l'ennemi. `description` est l'aide affichée pendant la sélection.

```json
{
  "id": "frost",
  "name": "Givre entravant",
  "description": "Dégâts de glace et -5 vitesse à la cible pendant 3 tours.",
  "cost": 7,
  "magical": true,
  "effects": [
    {"kind": "damage", "power": 14, "magical": true, "element": "ice"},
    {"kind": "status", "status": "frost_slow"}
  ]
}
```

Le ciblage par défaut est un ennemi conscient. `targeting` peut déclarer
`side` (`enemy`, `ally`, `self`), `life` (`alive`, `ko`) et `multiple`.
Les effets disponibles sont `damage`, `heal`, `revive`, `mana`, `cure`, `status`.
Les états sont déclarés dans `statuses`, avec durée et éventuels modificateurs.
Leur durée diminue à chaque fin de tour du porteur, y compris le tour d'application
si le porteur est lui-même le lanceur. `required_status` impose une préparation
vérifiée par le moteur. Pour un nouvel effet, implémenter le protocole `Effect`
dans le domaine, puis l'ajouter explicitement à la compilation JSON et le tester.

## Ennemi et profil de rencontre

Ajouter un ennemi à `combat.json` : `id`, `name`, `stats`, `skills`, `resistances`,
`profile`. Les statistiques requièrent PV, PM, force, défense, magie, résistance
et vitesse. Les résistances sont des pourcentages : 50 résiste, 150 est vulnérable.
Le profil `regular` suffit pour les nouveaux ennemis ordinaires.

Placer ensuite son identifiant dans `objects[].enemies` d'une carte. Tous les
ennemis de cette rencontre doivent partager le même profil. Le profil définit
la fuite, les récompenses et, si besoin, la séquence `telegraph` du boss.

Pour les images, ajouter un atlas embarqué et ses métadonnées dans
`presentation/painted_sprites.py` : dimensions de case, nombre, ancrage, dossier,
début de la séquence d'action, puis association dans `ENEMY_SHEETS`. Les atlas
sont des bandes horizontales ; les quatre premières poses servent à l'attente
quand elles sont communes à l'action. Le découpage des trois nouvelles créatures
est reproductible avec `tools/prepare_creature_art.py`. Conserver les sources,
les prompts et les empreintes dans le manifeste.

## Objet ou équipement

Un consommable est déclaré dans `combat.json.consumables` avec une définition
d'objet et une capacité à coût nul. Le rendre disponible via boutique, coffre
ou récompense. Les soins, résurrections et restaurations de PM peuvent être
utilisés hors combat ; les autres effets sont refusés dans ce contexte.

Un équipement est déclaré dans `adventure.json.equipment`, avec catégorie,
emplacements, restrictions de classe et modificateurs. Exemple :

```json
{
  "id": "round_shield",
  "name": "Bouclier rond",
  "category": "armor",
  "slots": ["off_hand"],
  "classes": ["guerrier"],
  "modifiers": {"defense": 5, "resistance": 2, "accuracy": -2}
}
```

L'ajouter à une boutique, un coffre ou une récompense. Les sauvegardes référencent
uniquement l'identifiant ; elles ne définissent pas ses statistiques.

## Carte et quête

Les cartes sont décrites dans `content/maps/`. Sol, collisions et objets doivent
rester cohérents : les pieds déterminent la collision, les images restent une
projection visuelle. Pour une nouvelle peinture, déclarer son recalage dans
`world_art.REGISTRATIONS` et conserver son guide de composition. Les trois cartes
existantes sont chargées explicitement par `JsonMapLoader.load()` ; une quatrième
carte demanderait aussi son enregistrement dans cette liste et des passages liés.

Une quête est déclarée dans `adventure.json.quests`, avec `kind` (`main` ou `side`),
objectifs, éventuels prérequis et récompense. Les objectifs réutilisent les faits
du monde : carte visitée, PNJ rencontré, coffre ouvert, rencontre vaincue ou drapeau.
Plusieurs sujets avec `required` permettent une chasse à plusieurs rencontres.
Ajouter dans un dialogue les opérations `accept_quest` et `claim_quest`, conditionnées
par les statuts appropriés. Les prérequis deviennent disponibles après remise de
la récompense de la quête précédente. Lier le dialogue au PNJ dans `npc_dialogues`.

Pour restreindre un combat, utiliser `encounter_gates` et une condition narrative,
avec un message de refus. Les mutations restent dans les services applicatifs,
jamais dans le rendu. Pour faire évoluer les sauvegardes de développement sans
migration, augmenter `GameSnapshotMapper.CONTENT_VERSION` et documenter la rupture.
