# src/temporal_event_predictor/core/session_manager.py
# Gestion des sessions utilisateur et persistance des modèles (refactorisé)

import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from cachetools import LRUCache

from temporal_event_predictor.core.constants import (
    JWT_EXPIRATION_DAYS, SESSION_TOKEN_BYTES, MAX_MODELS_IN_CACHE,
    SecurityEventType, LogSeverity, ErrorMessages, SuccessMessages
)
from temporal_event_predictor.core.model_state import ModelState
from temporal_event_predictor.core.database import (
    init_main_database, init_session_database,
    create_session_record, get_session_record, delete_session_record,
    update_session_last_accessed, create_security_log
)
from temporal_event_predictor.core.utils.folder_manager import (
    create_session_directory, delete_session_directory,
    get_session_metadata_path, get_session_model_arrival_path,
    get_session_model_departure_path, get_session_encoder_path,
    session_exists
)
from temporal_event_predictor.core.utils.token_generator import generate_secure_token


class SessionManager:
    """Gère les sessions utilisateur et la persistance des modèles."""
    
    def __init__(self):
        """Initialise le gestionnaire de sessions."""
        # Cache LRU pour les modèles chargés en mémoire
        self._model_cache: LRUCache = LRUCache(maxsize=MAX_MODELS_IN_CACHE)
        
        # Initialiser la base de données
        init_main_database()
    
    def create_session(
        self, 
        ip_address: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crée une nouvelle session pour un utilisateur.
        
        Args:
            ip_address: Adresse IP du client
            metadata: Métadonnées additionnelles (optionnel)
        
        Returns:
            str: ID de session (token sécurisé)
        """
        # Générer un ID de session sécurisé
        session_id = generate_secure_token(SESSION_TOKEN_BYTES)
        
        # Dates
        now = datetime.utcnow()
        expires_at = now + timedelta(days=JWT_EXPIRATION_DAYS)
        
        # Créer l'enregistrement en base de données
        create_session_record(
            session_id=session_id,
            ip_address=ip_address,
            expires_at=expires_at,
            metadata=metadata
        )
        
        # Créer le répertoire de la session
        create_session_directory(session_id)
        
        # Initialiser la base de données de session
        init_session_database(session_id)
        
        # Log de sécurité
        create_security_log(
            ip_address=ip_address,
            event_type=SecurityEventType.SESSION_CREATED,
            session_id=session_id,
            event_data=json.dumps({'expires_at': expires_at.isoformat()}),
            severity=LogSeverity.INFO
        )
        
        return session_id
    
    def get_session(
        self, 
        session_id: str, 
        current_ip: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'une session.
        
        Args:
            session_id: ID de la session
            current_ip: IP actuelle du client (pour logging)
        
        Returns:
            Dict contenant les infos de session ou None si invalide/expirée
        """
        session_record = get_session_record(session_id)
        
        if not session_record:
            return None
        
        # Vérifier l'expiration
        if session_record.is_expired:
            self.delete_session(session_id)
            return None
        
        # Log si changement d'IP
        if current_ip and session_record.ip_address != current_ip:
            create_security_log(
                ip_address=current_ip,
                event_type=SecurityEventType.IP_CHANGED,
                session_id=session_id,
                event_data=json.dumps({
                    'old_ip': session_record.ip_address,
                    'new_ip': current_ip
                }),
                severity=LogSeverity.WARNING
            )
        
        # Mettre à jour le dernier accès
        update_session_last_accessed(session_id)
        
        # Convertir en dictionnaire
        return {
            'session_id': session_record.session_id,
            'ip_address': session_record.ip_address,
            'created_at': session_record.created_at.isoformat(),
            'last_accessed': session_record.last_accessed.isoformat(),
            'expires_at': session_record.expires_at.isoformat(),
            'metadata': session_record.session_metadata
        }
    
    def delete_session(self, session_id: str) -> bool:
        """
        Supprime une session et toutes ses données associées.
        
        Args:
            session_id: ID de la session
        
        Returns:
            bool: True si supprimé, False si non trouvé
        """
        session_record = get_session_record(session_id)
        
        if not session_record:
            return False
        
        # Supprimer du cache mémoire
        if session_id in self._model_cache:
            del self._model_cache[session_id]
        
        # Supprimer le répertoire et tous les fichiers
        delete_session_directory(session_id)
        
        # Log de sécurité
        create_security_log(
            ip_address=session_record.ip_address,
            event_type=SecurityEventType.SESSION_DELETED,
            session_id=session_id,
            severity=LogSeverity.INFO
        )
        
        # Supprimer l'enregistrement de la base de données
        delete_session_record(session_id)
        
        return True
    
    def save_model(
        self, 
        session_id: str, 
        model_state: ModelState
    ):
        """
        Sauvegarde un ModelState dans la session.
        
        Args:
            session_id: ID de la session
            model_state: État du modèle à sauvegarder
        """
        if not session_exists(session_id):
            raise ValueError(ErrorMessages.SESSION_NOT_FOUND)
        
        # Sauvegarder les modèles
        with open(get_session_model_arrival_path(session_id), 'wb') as f:
            pickle.dump(model_state.model_start_time, f)
        
        with open(get_session_model_departure_path(session_id), 'wb') as f:
            pickle.dump(model_state.model_end_time, f)
        
        with open(get_session_encoder_path(session_id), 'wb') as f:
            pickle.dump({
                'encoder': model_state.id_encoder,
                'id_map': model_state.id_map
            }, f)
        
        # Sauvegarder les métadonnées
        metadata = model_state.to_dict()
        
        with open(get_session_metadata_path(session_id), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Mettre en cache
        self._model_cache[session_id] = model_state
        
        # Log de sécurité
        session_record = get_session_record(session_id)
        if session_record:
            create_security_log(
                ip_address=session_record.ip_address,
                event_type=SecurityEventType.MODEL_TRAINED,
                session_id=session_id,
                event_data=json.dumps({
                    'entity_count': model_state.entity_count,
                    'data_row_count': model_state.data_row_count
                }),
                severity=LogSeverity.INFO
            )
    
    def load_model(self, session_id: str) -> Optional[ModelState]:
        """
        Charge un ModelState depuis la session.
        Utilise le cache pour éviter les rechargements fréquents.
        
        Args:
            session_id: ID de la session
        
        Returns:
            ModelState ou None si non trouvé
        """
        # Vérifier le cache d'abord
        if session_id in self._model_cache:
            return self._model_cache[session_id]
        
        # Vérifier que la session existe
        if not session_exists(session_id):
            return None
        
        # Vérifier que les fichiers de modèle existent
        metadata_path = get_session_metadata_path(session_id)
        if not metadata_path.exists():
            return None
        
        try:
            # Créer un nouvel état
            model_state = ModelState()
            
            # Charger les modèles
            with open(get_session_model_arrival_path(session_id), 'rb') as f:
                model_state.model_start_time = pickle.load(f)
            
            with open(get_session_model_departure_path(session_id), 'rb') as f:
                model_state.model_end_time = pickle.load(f)
            
            with open(get_session_encoder_path(session_id), 'rb') as f:
                encoder_data = pickle.load(f)
                model_state.id_encoder = encoder_data['encoder']
                model_state.id_map = encoder_data['id_map']
            
            # Charger les métadonnées
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                model_state.is_trained = metadata.get('is_trained', False)
                model_state.trained_at = metadata.get('trained_at')
                model_state.data_row_count = metadata.get('data_row_count', 0)
                model_state.entity_count = metadata.get('entity_count', 0)
            
            # Mettre en cache
            self._model_cache[session_id] = model_state
            
            return model_state
        
        except Exception as e:
            print(f"Erreur lors du chargement du modèle: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """
        Nettoie toutes les sessions expirées.
        
        Returns:
            Nombre de sessions supprimées
        """
        from temporal_event_predictor.core.database import get_main_engine, get_db_session
        from temporal_event_predictor.models.database import Session
        
        engine = get_main_engine()
        db_session = get_db_session(engine)
        
        try:
            # Trouver toutes les sessions expirées
            expired = db_session.query(Session).filter(
                Session.expires_at <= datetime.utcnow()
            ).all()
            
            count = 0
            for session_record in expired:
                if self.delete_session(session_record.session_id):
                    count += 1
            
            return count
        
        finally:
            db_session.close()
    
    def clear_cache(self):
        """Vide complètement le cache de modèles."""
        self._model_cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Retourne des infos sur le cache de modèles."""
        return {
            'cache_size': len(self._model_cache),
            'max_cache_size': MAX_MODELS_IN_CACHE,
            'cached_sessions': list(self._model_cache.keys())
        }


# Instance globale (mais qui gère des états isolés par session !)
session_manager = SessionManager()