# src/temporal_event_predictor/core/security/admin_auth.py
# Authentification et autorisation pour les endpoints admin

import secrets
import os
from fastapi import Header, HTTPException, status
from typing import Optional

from temporal_event_predictor.core.utils.logging_config import get_security_logger

logger = get_security_logger()


class AdminAuth:
    """Gestion de l'authentification admin."""
    
    def __init__(self):
        """Initialise l'authentification admin."""
        self._admin_token: Optional[str] = None
        self._is_dev_mode: bool = False
        self._load_admin_token()
    
    def _load_admin_token(self):
        """Charge le token admin depuis la variable d'environnement."""
        self._admin_token = os.getenv('ADMIN_TOKEN')
        
        if not self._admin_token:
            # Mode développement : générer un token éphémère
            self._is_dev_mode = True
            self._admin_token = secrets.token_urlsafe(32)
            
            logger.warning("Mode développement activé")
            logger.warning(f"Token admin éphémère généré: {self._admin_token}")
            logger.warning("Pour la production, définissez: export ADMIN_TOKEN='your-secure-token'")
        else:
            logger.info("Token admin chargé depuis la variable d'environnement ADMIN_TOKEN")
    
    def verify_token(self, token: str) -> bool:
        """
        Vérifie si le token fourni est valide.
        
        Args:
            token: Token à vérifier
        
        Returns:
            True si valide, False sinon
        """
        if not self._admin_token:
            logger.error("Tentative de vérification sans token configuré")
            return False
        
        # Utiliser secrets.compare_digest pour éviter les timing attacks
        is_valid = secrets.compare_digest(token, self._admin_token)
        
        if not is_valid:
            logger.warning(f"Tentative d'accès admin avec token invalide (début: {token[:8]}...)")
        
        return is_valid
    
    def get_token(self) -> Optional[str]:
        """Retourne le token admin (pour affichage au démarrage)."""
        return self._admin_token
    
    def is_dev_mode(self) -> bool:
        """Indique si on est en mode développement."""
        return self._is_dev_mode


# Instance globale
admin_auth = AdminAuth()


def verify_admin_token(x_admin_token: str = Header(..., alias="X-Admin-Token")) -> str:
    """
    Dépendance FastAPI pour vérifier le token admin.
    
    Args:
        x_admin_token: Token admin fourni dans le header
    
    Returns:
        Token si valide
    
    Raises:
        HTTPException: Si le token est invalide
    """
    if not admin_auth.verify_token(x_admin_token):
        logger.warning("Accès admin refusé - Token invalide")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token admin invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("Accès admin autorisé")
    return x_admin_token