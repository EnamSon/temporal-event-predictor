# src/temporal_event_predictor/api/session.py
# Routes API pour la gestion des sessions

from fastapi import APIRouter, HTTPException, Request, Header, Depends

from temporal_event_predictor.core.session_manager import session_manager
from temporal_event_predictor.core.constants import SuccessMessages, ErrorMessages
from temporal_event_predictor.models.session_create_response import SessionCreateResponse
from temporal_event_predictor.models.session_info_response import SessionInfoResponse
from temporal_event_predictor.core.security.admin_auth import verify_admin_token
router = APIRouter(prefix="/session")


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(request: Request) -> SessionCreateResponse:
    """
    Crée une nouvelle session pour l'utilisateur.
    
    Returns:
        SessionCreateResponse: ID de session et message de confirmation
    """
    # Récupérer l'IP du client
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        session_id = session_manager.create_session(
            ip_address=client_ip,
            metadata={"user_agent": request.headers.get("user-agent", "unknown")}
        )
        
        return SessionCreateResponse(
            session_id=session_id,
            message=SuccessMessages.SESSION_CREATED + ". Utilisez ce session_id dans le header X-Session-ID pour vos requêtes."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la session: {str(e)}")


@router.get("/info", response_model=SessionInfoResponse)
async def get_session_info(
    request: Request,
    session_id: str = Header(..., alias="X-Session-ID"),
) -> SessionInfoResponse:
    """
    Récupère les informations d'une session.
    
    Args:
        session_id: ID de session (passé dans le header X-Session-ID)
        request: Requête HTTP (pour logging IP)
    
    Returns:
        SessionInfoResponse: Informations détaillées sur la session
    """
    client_ip = request.client.host if request.client else None
    
    session = session_manager.get_session(session_id, current_ip=client_ip)
    
    if not session:
        raise HTTPException(status_code=404, detail=ErrorMessages.SESSION_NOT_FOUND)
    
    # Charger le modèle pour vérifier l'état d'entraînement
    model_state = session_manager.load_model(session_id)
    
    is_trained = model_state is not None and model_state.is_trained
    entity_count = model_state.entity_count if model_state else 0
    data_row_count = model_state.data_row_count if model_state else 0
    
    return SessionInfoResponse(
        session_id=session["session_id"],
        ip_address=session["ip_address"],
        created_at=session["created_at"],
        last_accessed=session["last_accessed"],
        expires_at=session["expires_at"],
        is_model_trained=is_trained,
        entity_count=entity_count,
        data_row_count=data_row_count
    )


@router.delete("/delete")
async def delete_session(session_id: str = Header(..., alias="X-Session-ID")):
    """
    Supprime une session et toutes ses données associées.
    
    Args:
        session_id: ID de session (passé dans le header X-Session-ID)
    
    Returns:
        dict: Message de confirmation
    """
    deleted = session_manager.delete_session(session_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=ErrorMessages.SESSION_NOT_FOUND)
    
    return {"message": SuccessMessages.SESSION_DELETED}


@router.post("/cleanup", dependencies=[Depends(verify_admin_token)])
async def cleanup_expired():
    """
    Nettoie toutes les sessions expirées (endpoint admin).
    Nécessite un token admin dans le header X-Admin-Token.
    
    Returns:
        dict: Nombre de sessions supprimées
    """
    try:
        count = session_manager.cleanup_expired_sessions()
        return {
            "message": SuccessMessages.CLEANUP_COMPLETED,
            "deleted_count": count
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {str(e)}")


@router.get("/cache-info", dependencies=[Depends(verify_admin_token)])
async def get_cache_info():
    """
    Récupère les informations sur le cache de modèles en mémoire.
    Nécessite un token admin dans le header X-Admin-Token.
    
    Returns:
        dict: Informations du cache
    """
    return session_manager.get_cache_info()


@router.post("/cache-clear", dependencies=[Depends(verify_admin_token)])
async def clear_cache():
    """
    Vide le cache de modèles en mémoire (endpoint admin).
    Force le rechargement depuis le disque au prochain accès.
    Nécessite un token admin dans le header X-Admin-Token.
    
    Returns:
        dict: Message de confirmation
    """
    session_manager.clear_cache()
    return {"message": "Cache de modèles vidé avec succès"}
