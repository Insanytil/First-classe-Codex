# ADR 0002 — Fondations métier composées et transferts atomiques

Statut : acceptée par l’utilisateur avant la phase 2.

Référence : cahier des charges, sections 2.1–2.4, 3 et phase 1.

## Décisions

- `Character` est une entité avec identité stable, état privé et opérations
  explicites. `CharacterDefinition`, `ClassDefinition`, `CharacterStats`,
  `StatModifiers`, `ItemDefinition` et `ItemQuantity` sont des valeurs immuables.
  Les définitions ne contiennent aucun PV courant, XP ou quantité de sac.
  Une définition de personnage représente un héros recruté unique : son id sert
  d'identité au personnage. Les ennemis multiples et leurs identités d'instances
  seront traités avec les besoins du combat, sans les anticiper.
- Guerrier, mage, soigneur et voleur sont des données de test de la même classe
  `ClassDefinition` ; aucune sous-classe par métier. Les valeurs sont des jeux
  de données de validation, pas un catalogue équilibré ni du contenu JSON final.
- Les dix caractéristiques sont des entiers. HP max >=1, autres valeurs >=0,
  précision/esquive/critique en pourcentages [0,100]. Les modificateurs signés
  sont additionnés avant bornage pour éviter des résultats dépendant de l'ordre
  des équipements. Aucun calcul de dégâts ou jet de toucher n'est introduit.
- `ProgressionRules` est une valeur injectée, pas un singleton. Règle provisoire :
  seuil XP cumulée = 100 × niveau × (niveau−1) / 2, niveau maximum 99. Le gain
  peut franchir plusieurs niveaux ; l'XP est plafonnée au seuil du niveau maximal.
  La croissance par niveau appartient à la définition de classe et est positive
  ou nulle. Le facteur XP et le plafond sont configurables. Ces valeurs restent
  à équilibrer, sans changement du mécanisme.
- Monter de niveau ou équiper un bonus de ressources n'offre aucun soin gratuit.
  Retirer un bonus borne les PV/PM courants aux nouveaux maxima. Les PV ne
  deviennent jamais négatifs et les dépenses de PM insuffisantes sont rejetées.
  Les soins ordinaires ne ressuscitent pas. Les effets, compétences et règles de
  résurrection seront introduits avec le combat, pas sous forme de stubs.
- `Party` contient au plus quatre identités distinctes. Son ordre est explicite,
  le premier membre est leader. Une équipe vide est autorisée pour sa construction,
  n'a pas de leader et n'est pas considérée comme entièrement KO. Une réserve
  n'est pas implémentée. Une vue tuple empêche de modifier l'ordre par accident.
- Un inventaire stocke des piles par id de définition, équipements compris tant
  qu'ils sont identiques. Il refuse toute définition contradictoire pour un id
  déjà présent. Les exemplaires uniques n'ont pas de besoin actuel (pas d'usure,
  enchantement, qualité individuelle), donc aucune classe `ItemInstance` fictive.
- Les six slots sont des valeurs d'enum. Une définition d'équipement déclare les
  slots valides et les classes autorisées ; un ensemble vide de restrictions de
  classes signifie « toutes ». Un accessoire peut déclarer les deux slots, mais
  une opération n'en équipe qu'un exemplaire dans un seul slot.
- `Inventory.exchange` prépare toutes les suppressions/insertions sur une copie,
  vérifie quantités et cohérence des définitions, puis publie le nouvel état.
  `Character.equip` et `unequip` préparent leur nouvel équipement, demandent ce
  transfert atomique, puis publient le nouvel équipement et bornent les ressources.
  Dans ce modèle synchrone en mémoire, les erreurs métier prévues surviennent
  avant les mutations. Le modèle n'offre pas de transactions concurrentes ni de
  garantie face à un échec matériel/mémoire. Une future transaction de boutique
  sera orchestrée par un cas d'utilisation applicatif.
- Aucun `EquipmentSet`, repository, port ou service applicatif n'est ajouté pour
  déléguer sans autre responsabilité. Le personnage encapsule actuellement ses
  slots et la transaction de domaine. Une extraction restera possible si un
  véritable comportement ou un autre propriétaire la justifie.

## Frontières et validation

Les règles n'importent que la bibliothèque standard pure et le domaine. Ni JSON,
ni Pygame, fichier, hasard ou horloge. Un sous-processus bloque Pygame et importe
récursivement les couches internes avant de manipuler un personnage.
Les tests vérifient indépendance des instances, bornes, refus sans mutations,
seuils XP, croissance multi-niveaux, équipe et conservation d'objets par échanges.

Hors phase 1 : usage de consommables en combat, compétences, états temporaires,
résistances élémentaires et passifs, interface d'équipement, chargement JSON et
sauvegardes. Ils suivront les phases dédiées ; aucun de ces systèmes n'est simulé
par des abstractions vides. La fenêtre reste celle des fondations, sans gameplay.
