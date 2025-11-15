# src/work_time_prediction/api/__init__.py
# Router principal de l'API

from fastapi import APIRouter

from temporal_event_predictor.api.train_models import router as train_router
from temporal_event_predictor.api.session import router as session_router
from temporal_event_predictor.api.predict import router as predict_router

# Création du routeur principal
router = APIRouter()

# Inclusion des sous-routeurs
router.include_router(train_router, tags=["Model Training"])
router.include_router(predict_router, tags=["Predictions"])
router.include_router(session_router, tags=["Sessions"])

__all__ = ["router"]
