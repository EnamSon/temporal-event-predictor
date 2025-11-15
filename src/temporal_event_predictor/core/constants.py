# src/temporal_event_predictor/core/constants.py
# Constantes centralisées de l'application

from pathlib import Path

# ============================================================================
# COLONNES DU DATAFRAME
# ============================================================================

class DFCols:
    """Noms des colonnes standardisées du DataFrame."""
    ID = "id"
    ID_ENCODED = "id_encoded"
    DATE = "date"
    START_TIME_BY_MINUTES = "start_time_by_minutes"
    END_TIME_BY_MINUTES = "end_time_by_minutes"
    DAY_OF_YEAR = "day_of_year"
    DAY_OF_WEEK = "day_of_week"
    WEEK_OF_MONTH = "week_of_month"
    WEEK_OF_YEAR = "week_of_year"
    MONTH = "month"

# Colonnes du DataFrame après prétraitement
DF_COLS = [DFCols.ID, DFCols.DATE, DFCols.START_TIME_BY_MINUTES, DFCols.END_TIME_BY_MINUTES]

# ============================================================================
# APPLICATION
# ============================================================================

APP_NAME = "temporal_event_predictor"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "API de prédiction des horaires de travail avec système de sessions"

# ============================================================================
# CHEMINS DE BASE
# ============================================================================

# Répertoire home de l'utilisateur
HOME_DIR = Path.home()

# Répertoire racine de l'application dans $HOME
APP_ROOT_DIR = HOME_DIR / APP_NAME

# Répertoires principaux
DATA_DIR = APP_ROOT_DIR / "data"
LOGS_DIR = APP_ROOT_DIR / "logs"
CONFIG_DIR = APP_ROOT_DIR / "config"

# ============================================================================
# CHEMINS DES SESSIONS (unifié avec models)
# ============================================================================

# Sessions (contient les modèles ML)
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DB_PATH = SESSIONS_DIR / "sessions.db"

# Quotas par IP
QUOTAS_DIR = DATA_DIR / "quotas"
QUOTAS_DB_PATH = QUOTAS_DIR / "quotas.db"

# ============================================================================
# NOMS DE FICHIERS PAR SESSION
# ============================================================================

# Structure: sessions/{session_id}/
SESSION_METADATA_FILE = "metadata.json"
SESSION_MODEL_ARRIVAL_FILE = "model_arrival.pkl"
SESSION_MODEL_DEPARTURE_FILE = "model_departure.pkl"
SESSION_ENCODER_FILE = "encoder.pkl"
SESSION_DATA_DB_FILE = "data.db"

# Alias pour compatibilité avec ancien code
MODEL_METADATA_FILE = SESSION_METADATA_FILE
MODEL_ARRIVAL_FILE = SESSION_MODEL_ARRIVAL_FILE
MODEL_DEPARTURE_FILE = SESSION_MODEL_DEPARTURE_FILE
MODEL_ENCODER_FILE = SESSION_ENCODER_FILE
MODEL_DATA_DB_FILE = SESSION_DATA_DB_FILE

# ============================================================================
# CHEMINS DE LOGS
# ============================================================================

APP_LOG_FILE = LOGS_DIR / "app.log"
SECURITY_LOG_FILE = LOGS_DIR / "security.log"
QUOTAS_LOG_FILE = LOGS_DIR / "quotas.log"

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_FILE = CONFIG_DIR / "config.yaml"
ENV_FILE = APP_ROOT_DIR / ".env"

# ============================================================================
# NOMS DES TABLES SQL
# ============================================================================

# Table des sessions
SESSIONS_TABLE_NAME = "sessions"

# Table des quotas IP
IP_QUOTAS_TABLE_NAME = "ip_quotas"

# Table des logs de sécurité
SECURITY_LOGS_TABLE_NAME = "security_logs"

# Table des données d'horaires (dans data.db de chaque session)
SCHEDULE_TABLE_NAME = "schedule_data"

# ============================================================================
# NOMS DES VUES SQL
# ============================================================================

VIEW_ACTIVE_SESSIONS = "active_sessions"
VIEW_EXPIRED_SESSIONS = "expired_sessions"
VIEW_IP_STATISTICS = "ip_statistics"
VIEW_RECENT_SECURITY_EVENTS = "recent_security_events"
VIEW_SUSPICIOUS_IPS = "suspicious_ips"
VIEW_SYSTEM_STATISTICS = "system_statistics"

# ============================================================================
# TYPES D'ÉVÉNEMENTS DE SÉCURITÉ
# ============================================================================

class SecurityEventType:
    """Types d'événements de sécurité."""
    SESSION_CREATED = "session_created"
    SESSION_DELETED = "session_deleted"
    SESSION_ACCESSED = "session_accessed"
    MODEL_TRAINED = "model_trained"
    PREDICTION_MADE = "prediction_made"
    IP_CHANGED = "ip_changed"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_REQUEST = "invalid_request"
    RATE_LIMIT_HIT = "rate_limit_hit"
    BANNED = "banned"
    UNBANNED = "unbanned"

# ============================================================================
# NIVEAUX DE SÉVÉRITÉ DES LOGS
# ============================================================================

class LogSeverity:
    """Niveaux de sévérité des logs."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# ============================================================================
# FEATURES ML (Colonnes utilisées pour l'entraînement)
# ============================================================================

FEATURES = [
    DFCols.ID_ENCODED,
    DFCols.DAY_OF_WEEK,
    DFCols.WEEK_OF_MONTH,
    DFCols.WEEK_OF_YEAR,
    DFCols.MONTH,
    DFCols.DAY_OF_YEAR
]

# ============================================================================
# PARAMÈTRES DES MODÈLES ML
# ============================================================================

# RandomForestRegressor
ML_N_ESTIMATORS = 100
ML_RANDOM_STATE = 42
ML_N_JOBS = -1
ML_MAX_DEPTH = 10

# Seuil de confiance pour les prédictions (en minutes)
# Si l'erreur estimée dépasse ce seuil, on retourne NA au lieu d'une prédiction douteuse
PREDICTION_CONFIDENCE_THRESHOLD_MINUTES = 180  # 3 heures

# ============================================================================
# QUOTAS PAR DÉFAUT
# ============================================================================

DEFAULT_QUOTAS = {
    # Limites par IP
    "models_per_ip": 10,
    "max_file_size_mb": 50,
    "max_entities_per_model": 10000,
    "max_data_points": 100000,
    "max_storage_per_ip_mb": 500,

    # Rate limiting
    "requests_per_minute": 60,
    "train_per_hour": 5,
    "predictions_per_day": 1000,

    # Bannissement
    "ban_after_violations": 10,
    "ban_duration_hours": 24,
}

# ============================================================================
# SÉCURITÉ
# ============================================================================

# Taille des tokens de session (en bytes avant hex encoding)
SESSION_TOKEN_BYTES = 32  # 64 caractères hex

# Expiration des sessions
JWT_EXPIRATION_DAYS = 365  # 1 an

# Taille minimale de la clé secrète (si JWT utilisé)
MIN_JWT_SECRET_LENGTH = 32

# ============================================================================
# NETTOYAGE ET MAINTENANCE
# ============================================================================

CLEANUP_CONFIG = {
    "inactive_session_days": 365,      # Supprimer sessions inactives après 365 jours
    "log_retention_days": 30,         # Garder les logs 30 jours
    "cleanup_interval_hours": 24,      # Lancer cleanup toutes les 24 heures
    "max_security_logs": 100000,       # Nombre max de logs avant auto-nettoyage
}

# ============================================================================
# FORMATS DE DATE/HEURE
# ============================================================================

# Formats de date supportés (ordre de priorité)
DATE_FORMATS = [
    "%Y-%m-%d",      # ISO format: 2025-01-15
    "%d/%m/%Y",      # Format européen: 15/01/2025
]

# Format par défaut pour l'affichage
DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# ============================================================================
# JOURS DE LA SEMAINE
# ============================================================================

WEEKDAY_NAMES = {
    0: "mon",  # Lundi
    1: "tue",  # Mardi
    2: "wed",  # Mercredi
    3: "thu",  # Jeudi
    4: "fri",  # Vendredi
    5: "sat",  # Samedi
    6: "sun",  # Dimanche
}

# Valeur spéciale pour indiquer une absence de données
NA_VALUE = "NA"

# Nombre maximum de modèles en cache mémoire (LRU)
MAX_MODELS_IN_CACHE = 50

# Durée de vie du cache en secondes
CACHE_TTL_SECONDS = 3600  # 1 heure

# ============================================================================
# SÉPARATEURS CSV
# ============================================================================

CSV_SEPARATORS = [',', ';', '\t']  # Séparateurs à tester dans l'ordre

# ============================================================================
# NOMS DE COLONNES CSV PAR DÉFAUT (Génériques)
# ============================================================================

DEFAULT_COLUMN_NAMES = {
    "id": "ID",
    "date": "Date",
    "start_time": "Start Time",
    "end_time": "End Time",
}

# ============================================================================
# MESSAGES D'ERREUR STANDARDISÉS
# ============================================================================

class ErrorMessages:
    """Messages d'erreur standardisés."""
    SESSION_INVALID = "Session invalide ou expirée"
    SESSION_NOT_FOUND = "Session non trouvée"
    MODEL_NOT_TRAINED = "Le modèle n'est pas encore entraîné"
    ID_NOT_FOUND = "ID introuvable dans les données historiques"
    CSV_INVALID = "Le fichier CSV est invalide ou vide"
    NO_DATA = "Aucune donnée disponible"
    QUOTA_EXCEEDED = "Quota dépassé"
    IP_BANNED = "Adresse IP bannie"
    FILE_TOO_LARGE = "Fichier trop volumineux"
    INVALID_DATE_FORMAT = "Format de date invalide. Utilisez {}"
    MISSING_COLUMNS = "Colonnes manquantes dans le CSV: {}"

# ============================================================================
# MESSAGES DE SUCCÈS STANDARDISÉS
# ============================================================================

class SuccessMessages:
    """Messages de succès standardisés."""
    SESSION_CREATED = "Session créée avec succès"
    SESSION_DELETED = "Session supprimée avec succès"
    MODEL_TRAINED = "Modèle entraîné avec succès"
    PREDICTION_GENERATED = "Prédiction générée avec succès"
    CLEANUP_COMPLETED = "Nettoyage effectué avec succès"
    DB_OPTIMIZED = "Base de données optimisée avec succès"

# ============================================================================
# CODES HTTP
# ============================================================================

class HTTPStatus:
    """Codes de statut HTTP standardisés."""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401