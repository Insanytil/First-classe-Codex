# Validation de phase 2 — combat autonome

La phase 1 a été validée par l’utilisateur, qui a autorisé cette phase.
Référence : cahier des charges, phase 2. Décisions et règles provisoires :
[ADR 0003](adr/0003-combat-autonome.md).

## Périmètre réalisé

- Machine à états, ordre de vitesse déterministe et jetons de tour anti-rejeu.
- Commandes validées avant publication, avec résolution sur instantanés locaux.
- Compétences apprises, coûts PM, ciblage et effets composables.
- Attaque, garde, objets, fuite et passage de tour.
- Dégâts physiques/magiques, critiques, toucher, esquive et résistances élémentaires.
- Soins, résurrection et KO ; poison, brûlure, sommeil, paralysie, silence, buffs/debuffs.
- IA basique injectable utilisant les mêmes commandes et validations.
- Victoire/défaite/fuite, résultat structuré et journal d’événements métier.
- Drops garantis, tirages pondérés et raretés de contenu.
- Règlement applicatif des ressources, consommables, XP et monnaie, sans doublons en mémoire.

## Vérifications locales

Windows, Python 3.15.2, outils préalablement installés par l’utilisateur.
Aucune dépendance ou version de Python installée par l’agent.

| Contrôle | Résultat |
| --- | --- |
| Ruff lint et formatage | OK |
| mypy strict | OK, 30 fichiers source |
| pytest complet | 105 tests réussis |
| Couverture globale, branches incluses | 95 % |
| Machine de combat | 97 % |
| Effets | 98 % |
| Modèle et contrats de combat | 91 % |
| Loot et récompenses | 98 % |
| Règlement applicatif | 90 % |
| IA basique | 100 % |
| Combat et règlement avec import Pygame bloqué | OK |
| Exemple console `examples/battle.py` | OK |

Scénarios contrôlés : refus sans mutation des cibles/actions/coûts invalides,
absence de double action par rejeu, exclusion des KO, coût payé une seule fois,
consommable retiré une seule fois, cible multiple complète, résurrection, durées
et rafraîchissement d’états, garde, immunité/résistance/vulnérabilité, fuite interdite,
issues de combat, mêmes événements à graine fixe, récompense idempotente même avec
deux sessions sur le même combat. Un conflit de définition ou une modification
externe du groupe refuse le règlement sans écraser l’état du joueur.

Un générateur défaillant après un premier effet déjà résolu sur la copie ne
publie aucun coût, dégât ou événement partiel. Un test de régression vérifie aussi
l’addition des bonus temporaires et des malus permanents avant bornage, ainsi que
la lecture de l’état courant du lanceur entre effets composés.

La démonstration à graine 7 termine par :

```text
Résultat : victory, XP 120, or 25
PV 96/160, PM 24/40, potions 1
```

## Limites et arrêt

L’idempotence est en mémoire ; aucune sauvegarde ou migration n’est livrée.
Les états temporaires ne persistent pas après combat. L’IA n’est pas tactique et
les formules restent à équilibrer. Les données de démonstration sont des valeurs
Python, pas un catalogue JSON ou une aventure jouable.

Aucune UI de combat, exploration ou quête n’est ajoutée. La fenêtre conserve le
comportement des fondations. Pas de nouveau build exécuté par l’agent, car cette
opération peut installer des dépendances de build. Pas de résultat CI distant
présumé, ni de validation Linux/macOS pour ces nouvelles sources.

Statut : phase 2 validée par l’utilisateur, qui a autorisé la phase 3.
Suite : [validation de phase 3](VALIDATION_PHASE_3.md).
