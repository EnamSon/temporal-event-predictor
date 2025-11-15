# src/temporal_event_predictor/core/utils/token_generator.py
# Génération de tokens et identifiants sécurisés

import secrets
import hashlib
from datetime import datetime


def generate_secure_token(num_bytes: int = 32) -> str:
    """
    Génère un token sécurisé cryptographiquement.

    Args:
        num_bytes: Nombre de bytes aléatoires (défaut: 32 = 64 hex chars)

    Returns:
        Token hexadécimal sécurisé
    """
    # Générer des bytes aléatoires
    random_bytes = secrets.token_bytes(num_bytes)

    # Ajouter un timestamp pour garantir l'unicité
    timestamp = str(datetime.utcnow().timestamp()).encode()

    # Créer un hash SHA256
    hash_obj = hashlib.sha256(random_bytes + timestamp)

    return hash_obj.hexdigest()


def generate_session_id() -> str:
    """
    Génère un ID de session sécurisé.
    
    Returns:
        ID de session (64 caractères hexadécimaux)
    """
    return generate_secure_token(32)


def generate_short_id(length: int = 16) -> str:
    """
    Génère un ID court pour usage général.
    
    Args:
        length: Longueur en caractères hex (défaut: 16)
    
    Returns:
        ID court hexadécimal
    """
    num_bytes = length // 2
    return secrets.token_hex(num_bytes)


def verify_token_format(token: str, expected_length: int = 64) -> bool:
    """
    Vérifie qu'un token a le format attendu.
    
    Args:
        token: Token à vérifier
        expected_length: Longueur attendue en caractères
    
    Returns:
        True si le format est valide, False sinon
    """
    if not token or len(token) != expected_length:
        return False
    
    # Vérifier que c'est bien de l'hexadécimal
    try:
        int(token, 16)
        return True
    except ValueError:
        return False