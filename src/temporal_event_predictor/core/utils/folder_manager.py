# src/temporal_event_predictor/core/utils/folder_manager.py

from temporal_event_predictor.core.constants import (
    APP_ROOT_DIR, DATA_DIR, LOGS_DIR, CONFIG_DIR, SESSIONS_DIR, QUOTAS_DIR,
    SESSIONS_DIR,
    SESSION_METADATA_FILE,
    SESSION_MODEL_ARRIVAL_FILE,
    SESSION_MODEL_DEPARTURE_FILE,
    SESSION_ENCODER_FILE,
    SESSION_DATA_DB_FILE
)
from pathlib import Path
import shutil

def get_session_dir(session_id: str) -> Path:
    """
    Retourne le chemin du répertoire d'un modèle spécifique.
    
    Args:
        model_id: Identifiant unique du modèle
        
    Returns:
        Path vers le répertoire du modèle
    """
    return SESSIONS_DIR / session_id


def get_session_file_path(session_id: str, filename: str) -> Path:
    """
    Retourne le chemin complet d'un fichier dans le répertoire d'un modèle.
    
    Args:
        model_id: Identifiant unique du modèle
        filename: Nom du fichier (utiliser les constantes MODEL_*_FILE)
        
    Returns:
        Path vers le fichier
    """
    return get_session_dir(session_id) / filename


def ensure_directories_exist():
    """
    Crée tous les répertoires nécessaires s'ils n'existent pas.
    À appeler au démarrage de l'application.
    """
    directories = [
        APP_ROOT_DIR,
        DATA_DIR,
        LOGS_DIR,
        CONFIG_DIR,
        SESSIONS_DIR,
        QUOTAS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_session_metadata_path(session_id: str) -> Path:
    """Retourne le chemin du fichier metadata.json."""
    return get_session_dir(session_id) / SESSION_METADATA_FILE


def get_session_model_arrival_path(session_id: str) -> Path:
    """Retourne le chemin du modèle d'arrivée."""
    return get_session_dir(session_id) / SESSION_MODEL_ARRIVAL_FILE


def get_session_model_departure_path(session_id: str) -> Path:
    """Retourne le chemin du modèle de départ."""
    return get_session_dir(session_id) / SESSION_MODEL_DEPARTURE_FILE


def get_session_encoder_path(session_id: str) -> Path:
    """Retourne le chemin du fichier encoder."""
    return get_session_dir(session_id) / SESSION_ENCODER_FILE


def get_session_data_db_path(session_id: str) -> Path:
    """Retourne le chemin de la base de données de session."""
    return get_session_dir(session_id) / SESSION_DATA_DB_FILE


def create_session_directory(session_id: str) -> Path:
    """
    Crée le répertoire d'une session s'il n'existe pas.
    
    Args:
        session_id: ID de la session
    
    Returns:
        Path du répertoire créé
    """
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def delete_session_directory(session_id: str) -> bool:
    """
    Supprime complètement le répertoire d'une session.
    
    Args:
        session_id: ID de la session
    
    Returns:
        True si supprimé, False si n'existait pas
    """
    session_dir = get_session_dir(session_id)
    
    if session_dir.exists():
        shutil.rmtree(session_dir)
        return True
    
    return False


def session_exists(session_id: str) -> bool:
    """
    Vérifie si le répertoire d'une session existe.
    
    Args:
        session_id: ID de la session
    
    Returns:
        True si existe, False sinon
    """
    return get_session_dir(session_id).exists()


def get_session_storage_size(session_id: str) -> float:
    """
    Calcule la taille totale du stockage d'une session en MB.
    
    Args:
        session_id: ID de la session
    
    Returns:
        Taille en MB
    """
    session_dir = get_session_dir(session_id)
    
    if not session_dir.exists():
        return 0.0
    
    total_size = 0
    for file_path in session_dir.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    
    return total_size / (1024 * 1024)  # Conversion en MB


def list_all_session_ids() -> list[str]:
    """
    Liste tous les IDs de session ayant un répertoire.
    
    Returns:
        Liste des session_id
    """
    if not SESSIONS_DIR.exists():
        return []
    
    return [
        folder.name 
        for folder in SESSIONS_DIR.iterdir() 
        if folder.is_dir()
    ]


def get_total_storage_size() -> float:
    """
    Calcule la taille totale de tous les répertoires de session en MB.
    
    Returns:
        Taille totale en MB
    """
    if not SESSIONS_DIR.exists():
        return 0.0
    
    total_size = 0
    for session_dir in SESSIONS_DIR.iterdir():
        if session_dir.is_dir():
            for file_path in session_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
    
    return total_size / (1024 * 1024)


def cleanup_orphaned_directories():
    """
    Supprime les répertoires de sessions qui n'ont pas d'entrée en base de données.
    Utile après une corruption ou suppression manuelle.
    
    Returns:
        Nombre de répertoires supprimés
    """
    from temporal_event_predictor.core.database import get_session_record
    
    deleted_count = 0
    
    for session_id in list_all_session_ids():
        # Vérifier si la session existe en base
        if not get_session_record(session_id):
            # Session orpheline, supprimer le répertoire
            if delete_session_directory(session_id):
                deleted_count += 1
    
    return deleted_count
