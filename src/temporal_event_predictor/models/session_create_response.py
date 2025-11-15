# src/work_time_prediction/models/session_create_response.py

from pydantic import BaseModel

class SessionCreateResponse(BaseModel):
    """Réponse lors de la création d'une session."""
    session_id: str
    message: str