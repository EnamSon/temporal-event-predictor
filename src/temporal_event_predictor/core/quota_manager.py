# src/temporal_event_predictor/core/quota_manager.py
# Gestion et vérification des quotas par IP

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select

from temporal_event_predictor.core.database import get_main_engine, get_db_session
from temporal_event_predictor.models.database import IPQuota, Session as SessionModel
from temporal_event_predictor.core.constants import DEFAULT_QUOTAS
from temporal_event_predictor.core.utils.logging_config import get_logger
from temporal_event_predictor.core.utils.folder_manager import get_total_storage_size

logger = get_logger()


class QuotaManager:
    """Gestionnaire des quotas par IP."""
    
    def __init__(self):
        """Initialise le gestionnaire de quotas."""
        self.quotas_config = DEFAULT_QUOTAS
    
    def get_or_create_quota(self, ip_address: str) -> IPQuota:
        """
        Récupère ou crée un enregistrement de quota pour une IP.
        
        Args:
            ip_address: Adresse IP
        
        Returns:
            Objet IPQuota
        """
        engine = get_main_engine()
        db_session = get_db_session(engine)
        
        try:
            quota = db_session.query(IPQuota).filter(
                IPQuota.ip_address == ip_address
            ).first()
            
            if not quota:
                quota = IPQuota(ip_address=ip_address)
                db_session.add(quota)
                db_session.commit()
                db_session.refresh(quota)
                logger.info(f"Nouveau quota créé pour IP {ip_address}")
            
            return quota
        finally:
            db_session.close()
    
    def check_models_quota(self, ip_address: str) -> bool:
        """
        Vérifie si l'IP peut créer une nouvelle session/modèle.
        
        Args:
            ip_address: Adresse IP
        
        Returns:
            True si autorisé, False sinon
        """
        quota = self.get_or_create_quota(ip_address)
        
        if quota.is_currently_banned:
            logger.warning(f"IP {ip_address} est bannie jusqu'à {quota.banned_until}")
            return False
        
        max_models = self.quotas_config['models_per_ip']
        
        if quota.models_count >= max_models:
            logger.warning(f"IP {ip_address} a atteint la limite de {max_models} modèles")
            self._increment_violations(ip_address)
            return False
        
        return True
    
    def check_storage_quota(self, ip_address: str, additional_mb: float = 0) -> bool:
        """
        Vérifie si l'IP respecte le quota de stockage.
        
        Args:
            ip_address: Adresse IP
            additional_mb: Stockage additionnel prévu (en MB)
        
        Returns:
            True si autorisé, False sinon
        """
        quota = self.get_or_create_quota(ip_address)
        
        if quota.is_currently_banned:
            return False
        
        max_storage = self.quotas_config['max_storage_per_ip_mb']
        total_storage = quota.storage_used_mb + additional_mb
        
        if total_storage > max_storage:
            logger.warning(
                f"IP {ip_address} dépasserait le quota de stockage: "
                f"{total_storage:.2f} MB > {max_storage} MB"
            )
            self._increment_violations(ip_address)
            return False
        
        return True
    
    def check_rate_limit(self, ip_address: str, action: str) -> bool:
        """
        Vérifie les limites de taux (rate limiting).
        
        Args:
            ip_address: Adresse IP
            action: Type d'action ('request', 'train', 'predict')
        
        Returns:
            True si autorisé, False sinon
        """
        quota = self.get_or_create_quota(ip_address)
        
        if quota.is_currently_banned:
            return False
        
        # Vérifier si le reset est nécessaire
        self._reset_counters_if_needed(quota)
        
        # Vérifier les limites selon l'action
        if action == 'request':
            limit = self.quotas_config['requests_per_minute']
            if quota.requests_count >= limit:
                logger.warning(f"IP {ip_address} a atteint la limite de {limit} requêtes/minute")
                self._increment_violations(ip_address)
                return False
        
        elif action == 'train':
            limit = self.quotas_config['train_per_hour']
            if quota.train_count >= limit:
                logger.warning(f"IP {ip_address} a atteint la limite de {limit} entraînements/heure")
                self._increment_violations(ip_address)
                return False
        
        elif action == 'predict':
            limit = self.quotas_config['predictions_per_day']
            if quota.predictions_count >= limit:
                logger.warning(f"IP {ip_address} a atteint la limite de {limit} prédictions/jour")
                self._increment_violations(ip_address)
                return False
        
        return True
    
    def increment_counter(self, ip_address: str, action: str):
        """
        Incrémente un compteur d'action.
        
        Args:
            ip_address: Adresse IP
            action: Type d'action ('request', 'train', 'predict')
        """
        engine = get_main_engine()
        db_session = get_db_session(engine)
        
        try:
            quota = db_session.query(IPQuota).filter(
                IPQuota.ip_address == ip_address
            ).first()
            
            if quota:
                if action == 'request':
                    quota.requests_count += 1
                elif action == 'train':
                    quota.train_count += 1
                elif action == 'predict':
                    quota.predictions_count += 1
                
                db_session.commit()
        finally:
            db_session.close()
    
    def update_storage(self, ip_address: str):
        """
        Met à jour le stockage utilisé par une IP.
        
        Args:
            ip_address: Adresse IP
        """
        # Calculer le stockage réel utilisé
        from temporal_event_predictor.core.database import get_main_engine, get_db_session
        
        engine = get_main_engine()
        db_session = get_db_session(engine)
        
        try:
            # Récupérer toutes les sessions de cette IP
            sessions = db_session.query(SessionModel).filter(
                SessionModel.ip_address == ip_address
            ).all()
            
            total_storage = 0
            for session in sessions:
                from temporal_event_predictor.core.utils.folder_manager import get_session_storage_size
                total_storage += get_session_storage_size(session.session_id)
            
            # Mettre à jour le quota
            quota = db_session.query(IPQuota).filter(
                IPQuota.ip_address == ip_address
            ).first()
            
            if quota:
                quota.storage_used_mb = total_storage
                db_session.commit()
                logger.debug(f"Stockage mis à jour pour {ip_address}: {total_storage:.2f} MB")
        
        finally:
            db_session.close()
    
    def _reset_counters_if_needed(self, quota: IPQuota):
        """
        Réinitialise les compteurs si nécessaire (basé sur last_reset).
        
        Args:
            quota: Objet IPQuota
        """
        now = datetime.utcnow()
        time_since_reset = now - quota.last_reset
        
        # Réinitialiser toutes les heures
        if time_since_reset > timedelta(hours=1):
            engine = get_main_engine()
            db_session = get_db_session(engine)
            
            try:
                quota.requests_count = 0
                quota.train_count = 0
                quota.predictions_count = 0
                quota.last_reset = now
                
                db_session.commit()
                logger.debug(f"Compteurs réinitialisés pour {quota.ip_address}")
            finally:
                db_session.close()
    
    def _increment_violations(self, ip_address: str):
        """
        Incrémente le compteur de violations et bannit si nécessaire.
        
        Args:
            ip_address: Adresse IP
        """
        engine = get_main_engine()
        db_session = get_db_session(engine)
        
        try:
            quota = db_session.query(IPQuota).filter(
                IPQuota.ip_address == ip_address
            ).first()
            
            if quota:
                quota.violations_count += 1
                
                ban_threshold = self.quotas_config['ban_after_violations']
                
                if quota.violations_count >= ban_threshold and not quota.is_banned:
                    # Bannir l'IP
                    ban_duration = timedelta(hours=self.quotas_config['ban_duration_hours'])
                    quota.is_banned = True
                    quota.banned_until = datetime.utcnow() + ban_duration
                    
                    logger.error(
                        f"IP {ip_address} BANNIE pour {ban_duration.total_seconds()/3600}h "
                        f"({quota.violations_count} violations)"
                    )
                
                db_session.commit()
        finally:
            db_session.close()
    
    def unban_ip(self, ip_address: str):
        """
        Débannit une IP (fonction admin).
        
        Args:
            ip_address: Adresse IP
        """
        engine = get_main_engine()
        db_session = get_db_session(engine)
        
        try:
            quota = db_session.query(IPQuota).filter(
                IPQuota.ip_address == ip_address
            ).first()
            
            if quota:
                quota.is_banned = False
                quota.banned_until = None
                quota.violations_count = 0
                db_session.commit()
                
                logger.info(f"IP {ip_address} débannie")
        finally:
            db_session.close()


# Instance globale
quota_manager = QuotaManager()