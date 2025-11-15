# src/work_time_prediction/models/session_info_response.py

from pydantic import BaseModel

class SessionInfoResponse(BaseModel):
    """Informations sur une session."""
    session_id: str
    ip_address: str
    created_at: str
    last_accessed: str
    expires_at: str
    is_model_trained: bool
    entity_count: int
    data_row_count: int
