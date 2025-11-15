# src/temporal_event_predictor/core/database.py
# Gestion de la base de données avec SQLAlchemy

import pandas as pd
import io
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session as SQLSession
from sqlalchemy.exc import OperationalError

from temporal_event_predictor.models.database import Base, Session, IPQuota, SecurityLog, ScheduleData
from temporal_event_predictor.core.constants import (
    SESSIONS_DB_PATH, SCHEDULE_TABLE_NAME, DF_COLS, DFCols,
    CSV_SEPARATORS, DATE_FORMATS, DATE_FORMAT, ErrorMessages
)
from temporal_event_predictor.core.utils.time_converter import time_to_minutes
from temporal_event_predictor.core.exceptions import InvalidCsvFormatError
from temporal_event_predictor.core.required_columns import RequiredColumnsMapping


# ============================================================================
# GESTION DES ENGINES ET SESSIONS
# ============================================================================

def get_main_engine():
    """Retourne l'engine pour la base de données principale (sessions.db)."""
    # Créer le répertoire si nécessaire
    SESSIONS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f'sqlite:///{SESSIONS_DB_PATH}', echo=False)


def get_session_data_engine(session_id: str):
    """Retourne l'engine pour la base de données d'une session spécifique."""
    from temporal_event_predictor.core.utils.folder_manager import get_session_data_db_path
    db_path = get_session_data_db_path(session_id)
    return create_engine(f'sqlite:///{db_path}', echo=False)


def get_db_session(engine) -> SQLSession:
    """Crée et retourne une session SQLAlchemy."""
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_main_database():
    """Initialise la base de données principale avec toutes les tables."""
    engine = get_main_engine()
    
    # Créer toutes les tables avec SQLAlchemy
    Base.metadata.create_all(engine)
    
    # Créer les index supplémentaires non définis dans les modèles
    _create_additional_indexes(engine)
    
    # Créer les vues SQL
    _create_views(engine)


def init_session_database(session_id: str):
    """Initialise la base de données pour une session spécifique."""
    engine = get_session_data_engine(session_id)
    
    # Créer le répertoire si nécessaire
    from temporal_event_predictor.core.utils.folder_manager import get_session_dir
    get_session_dir(session_id).mkdir(parents=True, exist_ok=True)
    
    # Créer la table schedule_data avec SQLAlchemy
    Base.metadata.create_all(engine, tables=[ScheduleData.__table__])
    
    # Créer les index pour schedule_data
    _create_session_data_indexes(engine)


def _create_session_data_indexes(engine):
    """
    Crée les index pour la table schedule_data dans une base de session.
    
    Args:
        engine: SQLAlchemy engine pour la base de données de session
    """
    from sqlalchemy import text
    
    indexes_sql = [
        # Index sur la colonne id pour rechercher par entité
        "CREATE INDEX IF NOT EXISTS idx_schedule_data_id ON schedule_data(id)",
        
        # Index sur la colonne date pour rechercher par date
        "CREATE INDEX IF NOT EXISTS idx_schedule_data_date ON schedule_data(date)",
        
        # Index composite pour les requêtes fréquentes (entité + date)
        "CREATE INDEX IF NOT EXISTS idx_schedule_data_id_date ON schedule_data(id, date)",
    ]
    
    with engine.begin() as conn:
        for sql in indexes_sql:
            try:
                conn.execute(text(sql))
            except Exception:
                # Index existe déjà, continuer
                pass


def _create_additional_indexes(engine):
    """Crée les index supplémentaires avec SQLAlchemy."""
    from sqlalchemy import text
    
    indexes_sql = [
        # Index composites non définis dans les modèles
        "CREATE INDEX IF NOT EXISTS idx_sessions_ip_expires ON sessions(ip_address, expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_security_logs_ip_date ON security_logs(ip_address, created_at DESC)",
    ]
    
    with engine.begin() as conn:
        for sql in indexes_sql:
            try:
                conn.execute(text(sql))
            except Exception as e:
                # Index existe déjà ou erreur mineure, continuer
                pass


def _create_views(engine):
    """Crée les vues SQL avec SQLAlchemy."""
    from sqlalchemy import text
    
    views_sql = [
        # Vue des sessions actives
        """
        CREATE VIEW IF NOT EXISTS active_sessions AS
        SELECT 
            session_id,
            ip_address,
            created_at,
            last_accessed,
            expires_at,
            session_metadata
        FROM sessions
        WHERE expires_at > datetime('now')
        ORDER BY last_accessed DESC
        """,
        
        # Vue des sessions expirées
        """
        CREATE VIEW IF NOT EXISTS expired_sessions AS
        SELECT 
            session_id,
            ip_address,
            created_at,
            last_accessed,
            expires_at
        FROM sessions
        WHERE expires_at <= datetime('now')
        ORDER BY expires_at DESC
        """,
        
        # Vue des statistiques par IP
        """
        CREATE VIEW IF NOT EXISTS ip_statistics AS
        SELECT 
            s.ip_address,
            COUNT(s.session_id) as total_sessions,
            COUNT(CASE WHEN s.expires_at > datetime('now') THEN 1 END) as active_sessions,
            COUNT(CASE WHEN s.expires_at <= datetime('now') THEN 1 END) as expired_sessions,
            MIN(s.created_at) as first_session_date,
            MAX(s.last_accessed) as last_activity_date
        FROM sessions s
        GROUP BY s.ip_address
        """,
    ]
    
    with engine.begin() as conn:
        for sql in views_sql:
            try:
                conn.execute(text(sql))
            except Exception as e:
                # Vue existe déjà ou erreur mineure, continuer
                pass


# ============================================================================
# OPÉRATIONS CSV
# ============================================================================

def load_data_from_csv(
    csv_data: io.StringIO, 
    required_columns: RequiredColumnsMapping
) -> pd.DataFrame:
    """
    Charge le CSV et effectue le prétraitement initial.
    
    Args:
        csv_data: Contenu du CSV
        required_columns: Mapping des colonnes CSV vers colonnes standardisées
    
    Returns:
        DataFrame avec colonnes standardisées
    
    Raises:
        InvalidCsvFormatError: Si le CSV est invalide ou incomplet
    """
    try:
        # Tentative de lecture avec différents séparateurs
        df = None
        for separator in CSV_SEPARATORS:
            try:
                csv_data.seek(0)
                df = pd.read_csv(csv_data, sep=separator)
                if len(df.columns) >= len(DF_COLS):
                    break
            except Exception:
                continue
        
        if df is None or df.empty:
            raise InvalidCsvFormatError(ErrorMessages.CSV_INVALID)
        
        # Nettoyer les noms de colonnes
        df.columns = [col.strip().replace(' ', '_') for col in df.columns]
        
        # Obtenir les colonnes requises après nettoyage
        required_columns_clean = required_columns.clean()
        
        # Vérification des colonnes requises
        required_fields = vars(required_columns_clean).values()
        missing_cols = [col for col in required_fields if col not in df.columns]
        
        if missing_cols:
            raise InvalidCsvFormatError(
                ErrorMessages.MISSING_COLUMNS.format(', '.join(missing_cols))
            )
        
        # Conversion vers colonnes standardisées
        df[DFCols.ID] = df[required_columns_clean.id].astype(str)
        df[DFCols.START_TIME_BY_MINUTES] = df[required_columns_clean.start_time].apply(time_to_minutes)
        df[DFCols.END_TIME_BY_MINUTES] = df[required_columns_clean.end_time].apply(time_to_minutes)
        
        # Parser les dates avec plusieurs formats
        date_column = df[required_columns_clean.date]
        df[DFCols.DATE] = None
        
        for date_format in DATE_FORMATS:
            try:
                df[DFCols.DATE] = pd.to_datetime(date_column, format=date_format, errors='coerce')
                # Si on a des dates valides, on garde ce format
                if df[DFCols.DATE].notna().any():
                    break
            except Exception:
                continue
        
        # Vérifier qu'on a réussi à parser des dates
        if df[DFCols.DATE].isna().all():
            raise InvalidCsvFormatError(
                f"Impossible de parser les dates. Formats supportés : {', '.join(DATE_FORMATS)}"
            )
        
        # Nettoyage et filtrage
        df.dropna(subset=[DFCols.DATE, DFCols.ID], inplace=True)
        df = df[
            (df[DFCols.START_TIME_BY_MINUTES] > 0) & 
            (df[DFCols.END_TIME_BY_MINUTES] > 0)
        ]
        df = df[df[DFCols.END_TIME_BY_MINUTES] > df[DFCols.START_TIME_BY_MINUTES]]
        
        if df.empty:
            raise InvalidCsvFormatError(
                "Aucune donnée valide après nettoyage. Vérifiez le format des dates et heures."
            )
        
        return df[DF_COLS]
    
    except InvalidCsvFormatError:
        raise
    except Exception as e:
        raise InvalidCsvFormatError(f"Échec du chargement du CSV : {e}")


# ============================================================================
# OPÉRATIONS SUR LES DONNÉES D'ENTRAÎNEMENT
# ============================================================================

def save_data_to_db(df: pd.DataFrame, session_id: str):
    """
    Sauvegarde le DataFrame dans la base de données de la session.
    
    Args:
        df: DataFrame avec colonnes standardisées
        session_id: ID de la session
    """
    engine = get_session_data_engine(session_id)
    
    # Convertir les dates en string pour SQLite
    df_copy = df.copy()
    df_copy[DFCols.DATE] = df_copy[DFCols.DATE].dt.strftime(DATE_FORMAT)
    
    # Sauvegarder avec pandas (plus simple pour bulk insert)
    df_copy.to_sql(
        SCHEDULE_TABLE_NAME, 
        engine, 
        if_exists='replace', 
        index=False
    )


def get_all_data(session_id: str) -> pd.DataFrame:
    """
    Récupère toutes les données d'une session avec features temporelles.
    
    Args:
        session_id: ID de la session
    
    Returns:
        DataFrame avec colonnes enrichies (features temporelles)
    """
    engine = get_session_data_engine(session_id)
    
    try:
        # Lire depuis la base de données
        query = f"SELECT * FROM {SCHEDULE_TABLE_NAME}"
        df = pd.read_sql_query(query, engine)
        
        if df.empty:
            return pd.DataFrame()
        
        # Convertir la colonne date
        df[DFCols.DATE] = pd.to_datetime(df[DFCols.DATE], format=DATE_FORMAT)
        
        # Ajouter les features temporelles
        df[DFCols.DAY_OF_YEAR] = df[DFCols.DATE].dt.dayofyear
        df[DFCols.DAY_OF_WEEK] = df[DFCols.DATE].dt.dayofweek
        df[DFCols.WEEK_OF_YEAR] = df[DFCols.DATE].dt.isocalendar().week
        df[DFCols.MONTH] = df[DFCols.DATE].dt.month
        
        # Calculer week_of_month
        from temporal_event_predictor.core.utils.temporal_features import get_week_of_month
        df[DFCols.WEEK_OF_MONTH] = df[DFCols.DATE].apply(get_week_of_month)
        
        return df
    
    except (OperationalError, Exception):
        # La table n'existe pas encore ou erreur
        return pd.DataFrame()


def get_entity_history(session_id: str, entity_id: str) -> pd.DataFrame:
    """
    Récupère l'historique d'une entité spécifique.
    
    Args:
        session_id: ID de la session
        entity_id: ID de l'entité
    
    Returns:
        DataFrame filtré pour cet entité
    """
    df = get_all_data(session_id)
    if df.empty:
        return df
    
    return df[df[DFCols.ID] == entity_id]


# ============================================================================
# OPÉRATIONS SUR LES SESSIONS (SQLAlchemy ORM)
# ============================================================================

def create_session_record(
    session_id: str,
    ip_address: str,
    expires_at,
    metadata: Optional[dict] = None
) -> Session:
    """
    Crée un enregistrement de session dans la base de données.
    
    Args:
        session_id: ID unique de la session
        ip_address: Adresse IP du client
        expires_at: Date d'expiration
        metadata: Métadonnées optionnelles
    
    Returns:
        Objet Session créé
    """
    engine = get_main_engine()
    db_session = get_db_session(engine)
    
    try:
        session_record = Session(
            session_id=session_id,
            ip_address=ip_address,
            expires_at=expires_at,
            session_metadata=str(metadata or {})
        )
        
        db_session.add(session_record)
        db_session.commit()
        db_session.refresh(session_record)
        
        return session_record
    
    finally:
        db_session.close()


def get_session_record(session_id: str) -> Optional[Session]:
    """
    Récupère un enregistrement de session.
    
    Args:
        session_id: ID de la session
    
    Returns:
        Objet Session ou None si non trouvé
    """
    engine = get_main_engine()
    db_session = get_db_session(engine)
    
    try:
        stmt = select(Session).where(Session.session_id == session_id)
        result = db_session.execute(stmt).scalar_one_or_none()
        return result
    
    finally:
        db_session.close()


def delete_session_record(session_id: str) -> bool:
    """
    Supprime un enregistrement de session.
    
    Args:
        session_id: ID de la session
    
    Returns:
        True si supprimé, False si non trouvé
    """
    engine = get_main_engine()
    db_session = get_db_session(engine)
    
    try:
        session_record = db_session.query(Session).filter(
            Session.session_id == session_id
        ).first()
        
        if session_record:
            db_session.delete(session_record)
            db_session.commit()
            return True
        
        return False
    
    finally:
        db_session.close()


def update_session_last_accessed(session_id: str):
    """
    Met à jour le timestamp de dernier accès d'une session.
    
    Args:
        session_id: ID de la session
    """
    from datetime import datetime
    
    engine = get_main_engine()
    db_session = get_db_session(engine)
    
    try:
        session_record = db_session.query(Session).filter(
            Session.session_id == session_id
        ).first()
        
        if session_record:
            session_record.last_accessed = datetime.utcnow()
            db_session.commit()
    
    finally:
        db_session.close()


# ============================================================================
# OPÉRATIONS SUR LES QUOTAS IP
# ============================================================================

def get_or_create_ip_quota(ip_address: str) -> IPQuota:
    """
    Récupère ou crée un enregistrement de quota pour une IP.
    
    Args:
        ip_address: Adresse IP
    
    Returns:
        Objet IPQuota
    """
    engine = get_main_engine()
    db_session = get_db_session(engine)
    
    try:
        quota = db_session.query(IPQuota).filter(
            IPQuota.ip_address == ip_address
        ).first()
        
        if not quota:
            quota = IPQuota(ip_address=ip_address)
            db_session.add(quota)
            db_session.commit()
            db_session.refresh(quota)
        
        return quota
    
    finally:
        db_session.close()


# ============================================================================
# LOGS DE SÉCURITÉ
# ============================================================================

def create_security_log(
    ip_address: str,
    event_type: str,
    session_id: Optional[str] = None,
    event_data: Optional[str] = None,
    severity: str = 'INFO'
):
    """
    Crée un log de sécurité.
    
    Args:
        ip_address: Adresse IP
        event_type: Type d'événement
        session_id: ID de session (optionnel)
        event_data: Données de l'événement (optionnel)
        severity: Niveau de sévérité
    """
    engine = get_main_engine()
    db_session = get_db_session(engine)
    
    try:
        log = SecurityLog(
            session_id=session_id,
            ip_address=ip_address,
            event_type=event_type,
            event_data=event_data,
            severity=severity
        )
        
        db_session.add(log)
        db_session.commit()
    
    finally:
        db_session.close()