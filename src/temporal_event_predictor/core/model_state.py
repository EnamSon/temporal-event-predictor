# src/temporal_event_predictor/core/model_state.py
# Classe d'état de modèle ML (non globale, isolée par session)

from typing import Any, Dict
from sklearn.preprocessing import LabelEncoder  # type: ignore


class ModelState:
    """
    État d'un modèle ML spécifique.
    Chaque session a sa propre instance de ModelState.
    """
    
    def __init__(self):
        """Initialise un nouvel état de modèle vide."""
        # Modèles ML
        self.model_start_time: Any | None = None
        self.model_end_time: Any | None = None
        
        # Encodeur et mapping des IDs
        self.id_encoder: LabelEncoder = LabelEncoder()
        self.id_map: Dict[str, int] = {}  # ID réel -> ID encodé
        
        # État d'entraînement
        self.is_trained: bool = False
        
        # Métadonnées
        self.trained_at: str | None = None
        self.data_row_count: int = 0
        self.entity_count: int = 0
    
    def reset(self) -> None:
        """Réinitialise complètement l'état du modèle."""
        self.model_start_time = None
        self.model_end_time = None
        self.id_encoder = LabelEncoder()
        self.id_map = {}
        self.is_trained = False
        self.trained_at = None
        self.data_row_count = 0
        self.entity_count = 0
    
    def is_id_known(self, entity_id: str) -> bool:
        """
        Vérifie si un ID est connu dans le système.
        
        Args:
            entity_id: ID de l'entité
        
        Returns:
            True si l'entité est connue, False sinon
        """
        return entity_id in self.id_map
    
    def get_encoded_id(self, entity_id: str) -> int:
        """
        Retourne l'ID encodé d'une entité.
        
        Args:
            entity_id: ID de l'entité
        
        Returns:
            ID encodé
        
        Raises:
            KeyError: Si l'ID n'existe pas
        """
        return self.id_map[entity_id]
    
    def get_all_entity_ids(self) -> list[str]:
        """
        Retourne la liste de tous les IDs connus.
        
        Returns:
            Liste des IDs
        """
        return list(self.id_map.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'état du modèle en dictionnaire (pour métadonnées).
        
        Returns:
            Dictionnaire avec les infos du modèle
        """
        return {
            'is_trained': self.is_trained,
            'trained_at': self.trained_at,
            'data_row_count': self.data_row_count,
            'entity_count': self.entity_count,
            'entity_ids': self.get_all_entity_ids()
        }
    
    def __repr__(self) -> str:
        """Représentation string de l'état."""
        return (
            f"<ModelState(trained={self.is_trained}, "
            f"entities={self.entity_count}, "
            f"data_points={self.data_row_count})>"
        )