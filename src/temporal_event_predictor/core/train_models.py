# src/temporal_event_predictor/core/train_models.py
# Logique d'entraînement des modèles ML (sans état global)

from sklearn.ensemble import RandomForestRegressor  # type: ignore

from temporal_event_predictor.core.constants import (
    FEATURES, DFCols, ML_N_ESTIMATORS, ML_RANDOM_STATE, 
    ML_N_JOBS, ML_MAX_DEPTH
)
from temporal_event_predictor.core.database import get_all_data
from temporal_event_predictor.core.model_state import ModelState
from temporal_event_predictor.core.exceptions import NoDataFoundError


def train_models(session_id: str) -> ModelState:
    """
    Entraîne les modèles ML pour une session donnée.
    
    Args:
        session_id: ID de la session
    
    Returns:
        ModelState: Nouvel état de modèle entraîné
    
    Raises:
        NoDataFoundError: Si aucune donnée n'est disponible
    """
    # Charger les données depuis la base de données de la session
    df = get_all_data(session_id)
    
    if df.empty:
        raise NoDataFoundError(
            "Impossible d'entraîner : aucune donnée trouvée dans la base de données."
        )
    
    # Créer un nouvel état de modèle (pas d'état global !)
    model_state = ModelState()
    
    # 1. Encodage des IDs employés
    all_entity_ids = df[DFCols.ID].unique()
    model_state.id_encoder.fit(all_entity_ids)
    df[DFCols.ID_ENCODED] = model_state.id_encoder.transform(df[DFCols.ID])
    
    # 2. Créer le mapping ID réel -> ID encodé
    model_state.id_map = {
        real_id: int(encoded_id)  # Conversion explicite en int
        for real_id, encoded_id in zip(
            all_entity_ids,
            model_state.id_encoder.transform(all_entity_ids)
        )
    }
    
    # 3. Préparer les features
    X = df[FEATURES]
    
    # 4. Entraîner le modèle pour les heures d'arrivée
    y_start = df[DFCols.START_TIME_BY_MINUTES]
    model_state.model_start_time = RandomForestRegressor(
        n_estimators=ML_N_ESTIMATORS,
        random_state=ML_RANDOM_STATE,
        n_jobs=ML_N_JOBS,
        max_depth=ML_MAX_DEPTH
    )
    model_state.model_start_time.fit(X, y_start)
    
    # 5. Entraîner le modèle pour les heures de départ
    y_end = df[DFCols.END_TIME_BY_MINUTES]
    model_state.model_end_time = RandomForestRegressor(
        n_estimators=ML_N_ESTIMATORS,
        random_state=ML_RANDOM_STATE,
        n_jobs=ML_N_JOBS,
        max_depth=ML_MAX_DEPTH
    )
    model_state.model_end_time.fit(X, y_end)
    
    # 6. Mettre à jour les métadonnées
    from datetime import datetime
    model_state.is_trained = True
    model_state.trained_at = datetime.now().isoformat()
    model_state.data_row_count = len(df)
    model_state.entity_count = len(model_state.id_map)
    
    return model_state


def get_model_info(model_state: ModelState) -> dict:
    """
    Retourne les informations sur un modèle entraîné.
    
    Args:
        model_state: État du modèle
    
    Returns:
        Dictionnaire avec les infos du modèle
    """
    if not model_state.is_trained:
        return {
            'is_trained': False,
            'message': 'Modèle non entraîné'
        }
    
    return {
        'is_trained': True,
        'trained_at': model_state.trained_at,
        'data_row_count': model_state.data_row_count,
        'entity_count': model_state.entity_count,
        'features': FEATURES,
        'model_type': 'RandomForestRegressor',
        'model_params': {
            'n_estimators': ML_N_ESTIMATORS,
            'max_depth': ML_MAX_DEPTH,
            'random_state': ML_RANDOM_STATE
        }
    }