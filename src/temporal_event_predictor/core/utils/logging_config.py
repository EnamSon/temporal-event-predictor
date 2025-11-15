# src/temporal_event_predictor/core/utils/logging_config.py
# Configuration centralisée du système de logging

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from temporal_event_predictor.core.constants import APP_LOG_FILE, SECURITY_LOG_FILE, LOGS_DIR, APP_NAME


# Créer le répertoire de logs
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """Configure le système de logging pour l'application."""
    
    # Format des logs
    log_format = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ========================================================================
    # Logger principal de l'application
    # ========================================================================
    app_logger = logging.getLogger(APP_NAME)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    
    # Handler console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # Handler fichier avec rotation (10 MB max, 5 fichiers)
    file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    
    # Ajouter les handlers
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)
    
    # ========================================================================
    # Logger de sécurité (séparé)
    # ========================================================================
    security_logger = logging.getLogger(f'{APP_NAME}.security')
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    
    # Handler fichier sécurité
    security_handler = RotatingFileHandler(
        SECURITY_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=10,  # Plus de backups pour la sécurité
        encoding='utf-8'
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(log_format)
    
    security_logger.addHandler(security_handler)
    security_logger.addHandler(console_handler)  # Aussi sur console
    
    # ========================================================================
    # Réduire le bruit des librairies externes
    # ========================================================================
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    
    return app_logger


def get_logger(name: str = APP_NAME) -> logging.Logger:
    """
    Récupère un logger configuré.
    
    Args:
        name: Nom du logger (par défaut: 'work_time_prediction')
    
    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


def get_security_logger() -> logging.Logger:
    """
    Récupère le logger de sécurité.
    
    Returns:
        Logger de sécurité
    """
    return logging.getLogger(f'{APP_NAME}.security')


# Initialiser le logging au chargement du module
setup_logging()