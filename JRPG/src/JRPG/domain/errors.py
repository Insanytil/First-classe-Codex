"""Erreurs identifiables par les futurs cas d'utilisation et interfaces."""


class DomainError(ValueError):
    """Une règle métier interdit l'opération ; aucun changement partiel."""


class InvalidQuantity(DomainError):
    """Une quantité doit être un entier strictement positif."""


class MissingItem(DomainError):
    """Le sac ne contient pas assez d'exemplaires."""


class IncompatibleEquipment(DomainError):
    """La classe ou l'emplacement refuse cet équipement."""


class InsufficientMana(DomainError):
    """Les PM disponibles ne couvrent pas le coût."""


class CharacterKnockedOut(DomainError):
    """Cette opération nécessite un personnage conscient."""
