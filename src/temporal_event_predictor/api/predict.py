# src/temporal_event_predictor/api/predict.py
# Route de prédiction avec gestion de session

from fastapi import APIRouter, HTTPException, Header, Request
from datetime import datetime, timedelta

from temporal_event_predictor.models.predict_request import PredictionRequest
from temporal_event_predictor.models.predict_response import PredictionResponse, PredictedDay
from temporal_event_predictor.core.predictions import generate_predictions
from temporal_event_predictor.core.exceptions import ModelNotTrainedError, IDNotFoundError
from temporal_event_predictor.core.session_manager import session_manager
from temporal_event_predictor.core.database import create_security_log
from temporal_event_predictor.core.constants import (
    DATE_FORMAT, SecurityEventType, LogSeverity, ErrorMessages, WEEKDAY_NAMES
)


router = APIRouter()


@router.post("/predict/", response_model=PredictionResponse)
async def predict_schedule(
    http_request: Request,
    request: PredictionRequest,
    session_id: str = Header(..., alias="X-Session-ID"),
):
    """
    Génère des prédictions de temps pour une entité.
    Charge automatiquement le modèle depuis la session.
    
    Args:
        request: Données de la requête (id, target_date, window_size)
        session_id: ID de session (requis dans le header)
        http_request: Requête HTTP (pour logging IP)
    
    Returns:
        PredictionResponse: Liste des prédictions
    """
    # Obtenir l'IP du client
    client_ip = http_request.client.host if http_request.client else "unknown"
    
    # Valider la session
    session = session_manager.get_session(session_id, current_ip=client_ip)
    if not session:
        raise HTTPException(status_code=404, detail=ErrorMessages.SESSION_INVALID)
    
    # Charger le modèle depuis la session (avec cache)
    model_state = session_manager.load_model(session_id)
    if not model_state or not model_state.is_trained:
        raise HTTPException(
            status_code=400,
            detail="Aucun modèle entraîné trouvé pour cette session. Veuillez d'abord entraîner un modèle via POST /api/train/"
        )
    
    try:
        # Parser la date cible
        target_date = datetime.strptime(request.target_date, DATE_FORMAT)
        
        # Générer la plage de dates
        half_window = request.window_size // 2
        start_date = target_date - timedelta(days=half_window)
        end_date = target_date + timedelta(days=half_window)

        dates_to_predict = [
            start_date + timedelta(days=i)
            for i in range((end_date - start_date).days + 1)
        ]
        
        # Générer les prédictions (passer le model_state explicitement)
        predictions_data = generate_predictions(
            model_state=model_state,
            session_id=session_id,
            entity_id=request.id,
            dates_to_predict=dates_to_predict
        )
        
        # Convertir au format de réponse
        predicted_days = [
            PredictedDay(
                date=pred["date"],
                weekday=pred["weekday"],
                start_time=pred["start_time"],
                end_time=pred["end_time"],
                historical=pred["historical"]
            )
            for pred in predictions_data
        ]
        
        # Log de sécurité
        create_security_log(
            ip_address=client_ip,
            event_type=SecurityEventType.PREDICTION_MADE,
            session_id=session_id,
            event_data=f"entity_id={request.id}, date={request.target_date}",
            severity=LogSeverity.INFO
        )

        return PredictionResponse(predictions=predicted_days)
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorMessages.INVALID_DATE_FORMAT.format(DATE_FORMAT)
        )
    
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except IDNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction: {str(e)}")