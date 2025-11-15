# src/temporal_event_predictor/api/middleware/quota_middleware.py
# Middleware pour vérifier les quotas automatiquement

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from temporal_event_predictor.core.quota_manager import quota_manager
from temporal_event_predictor.core.utils.logging_config import get_logger

logger = get_logger()


class QuotaMiddleware(BaseHTTPMiddleware):
    """Middleware pour vérifier les quotas sur chaque requête."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Vérifie les quotas avant de traiter la requête.
        
        Args:
            request: Requête HTTP
            call_next: Fonction suivante dans la chaîne
        
        Returns:
            Réponse HTTP
        """
        # Récupérer l'IP du client
        client_ip = request.client.host if request.client else "unknown"
        
        # Ignorer les endpoints publics (health, docs, etc.)
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Vérifier si l'IP est bannie
        quota = quota_manager.get_or_create_quota(client_ip)
        if quota.is_currently_banned:
            logger.warning(f"Requête bloquée: IP {client_ip} est bannie")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP bannie jusqu'à {quota.banned_until}. "
                       f"Raison: Trop de violations des quotas."
            )
        
        # Vérifier le rate limiting général
        if not quota_manager.check_rate_limit(client_ip, 'request'):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de requêtes. Veuillez réessayer plus tard."
            )
        
        # Incrémenter le compteur de requêtes
        quota_manager.increment_counter(client_ip, 'request')
        
        # Traiter la requête
        response = await call_next(request)
        
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """
        Vérifie si un endpoint est public (pas de quota).
        
        Args:
            path: Chemin de l'endpoint
        
        Returns:
            True si public
        """
        public_paths = [
            '/docs',
            '/redoc',
            '/openapi.json',
            '/api/',
            '/api/health',
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)