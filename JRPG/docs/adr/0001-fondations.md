# ADR 0001 — Fondations isolées et dépendances dirigées

Statut : acceptée — fondations de la phase 0 validées par l’utilisateur.

## Contexte

La référence normative est [le cahier des charges](../../../CAHIER_DES_CHARGES_RPG_PYGAME_CODEX.md),
notamment les sections 0, 3, 6 et 8. Le prototype `poo/` possède déjà son contenu,
ses tests et des modifications locales. Son packaging exige Python 3.15 et mélange
plusieurs responsabilités dans la couche graphique. Une migration globale serait
risquée et dépasserait les fondations demandées.

## Décisions et motifs

- Un projet autonome `JRPG/`, distribution `technobel-jrpg`, paquet `src/JRPG`,
  Python 3.15 minimum (choix explicite de l’utilisateur). Le nom de module demandé est conservé, y compris sa casse.
  L'isolation permet de vérifier le nouveau moteur sans importer le prototype ou
  modifier son environnement. Le layout src impose une véritable installation.
- Quatre paquets définissent les responsabilités. Domaine → bibliothèque standard
  pure ; application → domaine ; infrastructure → application/domaine ;
  présentation → application/domaine. Les dépendances entre adaptateurs sont
  interdites ; `bootstrap.py` est le seul point de composition. Les imports de
  Pygame restent dans la présentation et sont différés au lancement graphique.
- Aucune entité, aucun repository, bus, port, scène abstraite ou conteneur DI sans
  besoin actuel. Les paquets métier ne contiennent que leur contrat documentaire.
  Les prochains ports appartiendront aux couches internes et seront injectés
  explicitement lorsque leurs cas d'utilisation existeront.
- Une application encapsule le cycle de vie SDL ; une configuration immuable est
  injectée au constructeur. La composition remplace l'héritage. Une fonction
  d'entrée suffit pour assembler ces deux objets, sans framework.
- Résolution logique 640 × 360 et plafond 60 FPS. À la demande de l’utilisateur,
  la fenêtre tient initialement dans 90 % du bureau et devient redimensionnable.
  Le rendu couvre toute la fenêtre avec une échelle proportionnelle, y compris
  fractionnaire. Le ratio 16:9 est conservé ; les débordements sont recadrés au
  centre pour supprimer les bandes noires, à la demande de l’utilisateur.
  Ce choix remplace
  la préférence initiale pour les échelles entières du cahier des charges.
  Aucune promesse de performances mesurées. Échap et fermeture de fenêtre quittent
  proprement ; `finally` libère SDL même si l'initialisation ou le rendu échouent.
  Le son et les scènes sont différés. Le cadrage est calculé par la configuration
  de présentation et testé indépendamment des règles métier.
- `pygame-ce` conserve le fournisseur déjà choisi dans le dépôt et fournit
  l'import `pygame`. pytest/couverture, Ruff et mypy strict contrôlent uniquement
  le nouveau projet ; un verrou uv fixe les résolutions de dépendances.
- Tests AST des frontières, incluant imports relatifs, imports dynamiques usuels
  et imports du prototype. Les couches internes refusent les bibliothèques tierces
  et les accès directs usuels aux fichiers, JSON, temps et hasard. Ce garde-fou
  n'est pas un sandbox : un alias d'import dynamique ou une opération d'I/O via
  `open()` exige toujours une revue. Un sous-processus bloque aussi Pygame pour
  vérifier l'import des fondations sans interface.
- Tests SDL avec pilote dummy : rendu réel d'une frame, événements de sortie,
  nettoyage après panne. Ils ne remplacent pas la recette visuelle desktop.

## Contenu, état, persistance et visuels

Les futures définitions JSON seront chargées/validées dans l'infrastructure ; les
instances et invariants appartiendront au domaine. L'application définira les
ports de persistance et orchestrera les transactions. La présentation résoudra
les identifiants d'assets sans introduire de chemins graphiques dans le domaine.
Aucun de ces systèmes n'est implémenté en phase 0.

Les assets et prompts existants restent des références créatives facultatives.
Leur style peint et certains personnages de franchise ne constituent pas une
charte validée pour le futur JRPG ; le cahier des charges demande un style 16-bit
original. Le fond uni évite une dépendance prématurée aux ressources du prototype.

## Conséquences et validation

Deux projets et deux environnements coexistent temporairement. Les commandes du
nouveau projet s'exécutent depuis `JRPG/`. L'ancien code n'est pas migré.
Les fondations sont validées ; la phase 1 attend une instruction de lancement. Aucun personnage,
combat, inventaire, contenu ou système de sauvegarde n'est introduit ici.
