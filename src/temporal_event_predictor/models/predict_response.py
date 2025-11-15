# src/temporal_event_predictor/models/predict_response.py
# Modèle Pydantic pour la réponse de prédiction

from pydantic import BaseModel
from typing import List

class PredictedDay(BaseModel):
    """
    Définit la structure de données pour un jour prédit ou historique.
    """
    date: str
    weekday: str
    start_time: str
    end_time: str
    historical: bool

class PredictionResponse(BaseModel):
    """
    Conteneur pour la liste des prédictions.
    """
    predictions: List[PredictedDay]
