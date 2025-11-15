# src/temporal_event_predictor/models/predict_request.py
# Modèle Pydantic pour la requête de prédiction

from pydantic import BaseModel

class PredictionRequest(BaseModel):
    """
    Définit la structure de la requête pour la prédiction des horaires.
    """
    id: str
    target_date: str # Format attendu : jj/mm/aaaa
    window_size: int = 31
