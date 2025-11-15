# src/temporal_event_predictor/api/train_models.py
# Route d'entraînement du modèle avec gestion de session

from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Form, Request
import io

from temporal_event_predictor.core.database import load_data_from_csv, save_data_to_db, create_security_log
from temporal_event_predictor.core.train_models import train_models
from temporal_event_predictor.core.required_columns import RequiredColumnsMapping
from temporal_event_predictor.core.exceptions import InvalidCsvFormatError, NoDataFoundError
from temporal_event_predictor.core.session_manager import session_manager
from temporal_event_predictor.core.quota_manager import quota_manager
from temporal_event_predictor.core.utils.logging_config import get_logger
from temporal_event_predictor.core.constants import (
    DEFAULT_COLUMN_NAMES, SecurityEventType, LogSeverity, 
    ErrorMessages, SuccessMessages
)


logger = get_logger()
router = APIRouter()


@router.post("/train_models/")
async def train_model(
    request: Request,
    file: UploadFile = File(..., description="Fichier CSV contenant les données d'entraînement"),
    session_id: str = Header(..., alias="X-Session-ID", description="ID de session"),
    id_column: str = Form(DEFAULT_COLUMN_NAMES["id"], description="Nom de la colonne ID"),
    date_column: str = Form(DEFAULT_COLUMN_NAMES["date"], description="Nom de la colonne Date"),
    start_time_column: str = Form(DEFAULT_COLUMN_NAMES["start_time"], description="Nom de la colonne temps de début"),
    end_time_column: str = Form(DEFAULT_COLUMN_NAMES["end_time"], description="Nom de la colonne temps de fin")
):
    """
    Upload un CSV, entraîne le modèle et sauvegarde dans la session.
    Le mapping des colonnes est utilisé uniquement pour transformer le CSV.
    
    Args:
        Request: Requête HTTP
        file: Fichier CSV contenant les données d'entraînement
        session_id: ID de session (header X-Session-ID)
        id_column: Nom de la colonne ID dans le CSV
        date_column: Nom de la colonne Date dans le CSV
        start_time_column: Nom de la colonne temps de début dans le CSV
        end_time_column: Nom de la colonne temps de fin dans le CSV
    
    Returns:
        dict: Résultat de l'entraînement avec statistiques
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Vérifier le quota d'entraînement spécifique
    if not quota_manager.check_rate_limit(client_ip, 'train'):
        logger.warning(f"Quota d'entraînement dépassé pour {client_ip}")
        raise HTTPException(status_code=429, detail="Quota d'entraînement dépassé")
    
    # Vérifier la taille du fichier
    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    
    if file_size_mb > quota_manager.quotas_config['max_file_size_mb']:
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux (max: {quota_manager.quotas_config['max_file_size_mb']} MB)")
    
    # Vérifier le quota de stockage (estimation)
    if not quota_manager.check_storage_quota(client_ip, file_size_mb * 3):  # Estimation: CSV * 3 pour modèles
        raise HTTPException(status_code=507, detail="Quota de stockage dépassé")
    
    # Valider la session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=ErrorMessages.SESSION_INVALID)

    # Valider la session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=ErrorMessages.SESSION_INVALID)
    
    # Vérifier le type de fichier
    if file.filename and not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont acceptés")
    
    try:
        # Lire le contenu du fichier
        csv_data = io.StringIO(contents.decode('utf-8'))
        
        # Créer le mapping de colonnes (utilisé uniquement pour la transformation)
        columns_mapping = RequiredColumnsMapping(
            id_column, date_column, start_time_column, end_time_column
        )
        
        # Charger et transformer les données (CSV -> colonnes standardisées)
        df = load_data_from_csv(csv_data, columns_mapping)
        
        if df.empty:
            raise InvalidCsvFormatError("Le fichier CSV ne contient aucune donnée valide après nettoyage")
        
        # Sauvegarder dans la base de données de la session
        save_data_to_db(df, session_id)
        
        # Entraîner les modèles et obtenir le nouvel état
        model_state = train_models(session_id)
        
        # Sauvegarder le modèle dans la session
        session_manager.save_model(session_id, model_state)
        
        # Log de succès
        create_security_log(
            ip_address=session["ip_address"],
            event_type=SecurityEventType.MODEL_TRAINED,
            session_id=session_id,
            event_data=f"entities={model_state.entity_count}, data_points={model_state.data_row_count}",
            severity=LogSeverity.INFO
        )
        
        return {
            "message": SuccessMessages.MODEL_TRAINED,
            "session_id": session_id,
            "data_points": model_state.data_row_count,
            "entities": model_state.entity_count,
            "trained_at": model_state.trained_at
        }
    
    except InvalidCsvFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except NoDataFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'entraînement: {str(e)}")
