# src/temporal_event_predictor/core/predictions.py
# Logique de prédiction du Machine Learning (sans état global)

from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

from temporal_event_predictor.core.constants import (
    FEATURES, DFCols, DATE_FORMAT, WEEKDAY_NAMES, NA_VALUE
)
from temporal_event_predictor.core.database import get_all_data
from temporal_event_predictor.core.utils.time_converter import minutes_to_time
from temporal_event_predictor.core.exceptions import ModelNotTrainedError, IDNotFoundError
from temporal_event_predictor.core.model_state import ModelState
from temporal_event_predictor.core.utils.temporal_features import get_week_of_month
from temporal_event_predictor.core.ml.occurrence_features import create_occurrence_extractor
from temporal_event_predictor.core.utils.logging_config import get_logger

logger = get_logger()


def generate_predictions(
    model_state: ModelState,
    session_id: str,
    entity_id: str,
    dates_to_predict: List[datetime]
) -> List[Dict[str, Any]]:
    """
    Génère les prédictions pour une liste de dates données.
    Mélange les données historiques réelles et les prédictions ML.
    Retourne NA pour les jours où aucun événement n'a jamais eu lieu.
    
    Args:
        model_state: État du modèle entraîné
        session_id: ID de la session
        entity_id: ID de l'entité (employé, client, événement, etc.)
        dates_to_predict: Liste des dates à prédire
    
    Returns:
        Liste de dictionnaires avec les prédictions
    
    Raises:
        ModelNotTrainedError: Si le modèle n'est pas entraîné
        IDNotFoundError: Si l'ID est inconnu
    """
    # Vérifications préalables
    if not model_state.is_trained:
        raise ModelNotTrainedError()
    
    if not model_state.model_start_time or not model_state.model_end_time:
        raise ModelNotTrainedError("Modèles ML non initialisés")
    
    if not model_state.is_id_known(entity_id):
        raise IDNotFoundError(entity_id)
    
    # 1. Récupérer l'historique de l'entité
    all_data = get_all_data(session_id)
    entity_history = all_data[all_data[DFCols.ID] == entity_id]
    
    if entity_history.empty:
        logger.warning(f"Aucun historique pour l'entité {entity_id}")
        raise IDNotFoundError(entity_id)
    
    # Créer l'extracteur de features d'occurrence
    occurrence_extractor = create_occurrence_extractor()
    
    historical_data_map = {
        row[DFCols.DATE].strftime(DATE_FORMAT): {
            DFCols.START_TIME_BY_MINUTES: row[DFCols.START_TIME_BY_MINUTES],
            DFCols.END_TIME_BY_MINUTES: row[DFCols.END_TIME_BY_MINUTES]
        }
        for _, row in entity_history.iterrows()
    }
    
    # 2. Identifier les dates qui nécessitent des prédictions
    future_data = []
    for date in dates_to_predict:
        date_str = date.strftime(DATE_FORMAT)
        if date_str not in historical_data_map:
            # Créer les features temporelles pour cette date
            features = {
                DFCols.ID_ENCODED: model_state.get_encoded_id(entity_id),
                DFCols.DAY_OF_WEEK: date.weekday(),
                DFCols.WEEK_OF_MONTH: get_week_of_month(date),
                DFCols.WEEK_OF_YEAR: date.isocalendar()[1],
                DFCols.MONTH: date.month,
                DFCols.DAY_OF_YEAR: date.timetuple().tm_yday,
                DFCols.DATE: date  # Conserver pour le mapping
            }
            future_data.append(features)
    
    # 3. Générer les prédictions pour les dates futures
    if future_data:
        future_df = pd.DataFrame(future_data)
        X_future = future_df[FEATURES]
        
        # Prédictions
        pred_start_minutes = model_state.model_start_time.predict(X_future)
        pred_end_minutes = model_state.model_end_time.predict(X_future)
    else:
        # Aucune prédiction nécessaire, toutes les dates sont historiques
        pred_start_minutes = []
        pred_end_minutes = []
    
    # 4. Construire les résultats
    results = []
    pred_idx = 0
    
    for date in dates_to_predict:
        date_str = date.strftime(DATE_FORMAT)
        weekday = WEEKDAY_NAMES[date.weekday()]
        
        if date_str in historical_data_map:
            # Utiliser les données historiques réelles
            data = historical_data_map[date_str]
            start_minutes = data[DFCols.START_TIME_BY_MINUTES]
            end_minutes = data[DFCols.END_TIME_BY_MINUTES]
            is_historical = True
            
            results.append({
                "date": date_str,
                "weekday": weekday,
                "start_time": minutes_to_time(start_minutes),
                "end_time": minutes_to_time(end_minutes),
                "historical": is_historical
            })
        else:
            # Vérifier si on doit prédire pour ce jour
            should_predict, confidence, reason = occurrence_extractor.should_predict_event(
                entity_id=entity_id,
                target_date=date,
                history=entity_history,
                min_occurrence_count=2,
                min_occurrence_rate=0.15
            )
            
            if not should_predict:
                # Pas assez de données pour prédire -> retourner NA
                logger.debug(f"Pas de prédiction pour {entity_id} le {date_str}: {reason}")
                results.append({
                    "date": date_str,
                    "weekday": weekday,
                    "start_time": NA_VALUE,
                    "end_time": NA_VALUE,
                    "historical": False
                })
                continue
            
            # Utiliser les données prédites
            if pred_idx < len(pred_start_minutes):
                start_minutes = float(pred_start_minutes[pred_idx])
                end_minutes = float(pred_end_minutes[pred_idx])
                pred_idx += 1
            else:
                # Cas d'erreur (ne devrait pas arriver)
                start_minutes = None
                end_minutes = None
            
            is_historical = False
            
            # Validation des prédictions
            if start_minutes is not None and end_minutes is not None:
                # Vérifier que les valeurs sont sensées
                if start_minutes < 0 or end_minutes < 0 or end_minutes <= start_minutes:
                    # Prédiction invalide, retourner NA
                    start_time_str = NA_VALUE
                    end_time_str = NA_VALUE
                else:
                    start_time_str = minutes_to_time(start_minutes)
                    end_time_str = minutes_to_time(end_minutes)
            else:
                start_time_str = NA_VALUE
                end_time_str = NA_VALUE
            
            results.append({
                "date": date_str,
                "weekday": weekday,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "historical": is_historical
            })
    
    return results


def predict_single_day(
    model_state: ModelState,
    session_id: str,
    entity_id: str,
    target_date: datetime
) -> Dict[str, Any]:
    """
    Génère une prédiction pour une seule date.
    
    Args:
        model_state: État du modèle entraîné
        session_id: ID de la session
        entity_id: ID de l'entité
        target_date: Date cible pour la prédiction
    
    Returns:
        Dictionnaire avec la prédiction
    """
    predictions = generate_predictions(
        model_state,
        session_id,
        entity_id,
        [target_date]
    )
    
    return predictions[0] if predictions else {
        "date": target_date.strftime(DATE_FORMAT),
        "start_time": "00:00",
        "end_time": "00:00",
        "historical": False,
        "error": "Impossible de générer une prédiction"
    }