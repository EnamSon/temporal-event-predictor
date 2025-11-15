from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from work_time_prediction.api import router
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from work_time_prediction.core.session_manager import session_manager
from work_time_prediction.core.constants import CLEANUP_CONFIG
from work_time_prediction.core.utils.logging_config import get_logger

logger = get_logger()

# Scheduler pour le nettoyage automatique des sessions expirées
scheduler = AsyncIOScheduler()


def cleanup_expired_sessions_job():
    """Tâche planifiée pour nettoyer les sessions expirées."""
    try:
        count = session_manager.cleanup_expired_sessions()
        logger.info(f"Nettoyage automatique: {count} sessions expirées supprimées")
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des sessions: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le cycle de vie de l'application."""
    # Démarrage
    logger.info("=" * 70)
    logger.info("Démarrage de l'application Work Time Prediction")
    logger.info("=" * 70)
    
    # Afficher le token admin
    from work_time_prediction.core.security.admin_auth import admin_auth
    admin_token = admin_auth.get_token()
    
    logger.info("🔐 Configuration Admin")
    if admin_auth.is_dev_mode():
        logger.warning("⚠️  Mode: DÉVELOPPEMENT (token éphémère)")
        logger.warning(f"Token admin: {admin_token}")
        logger.warning("⚠️  Ce token change à chaque redémarrage !")
        logger.warning("Pour la production: export ADMIN_TOKEN='your-secure-token'")
    else:
        logger.info("✅ Mode: PRODUCTION (token depuis variable d'environnement)")
        logger.info(f"Token admin: {admin_token}")
    
    logger.info(f"Usage: Header 'X-Admin-Token: {admin_token}'")
    logger.info("Endpoints protégés: /cleanup, /cache-info, /cache-clear")
    
    # Démarrage du scheduler
    cleanup_interval_hours = CLEANUP_CONFIG.get("cleanup_interval_hours", 1)
    scheduler.add_job(
        cleanup_expired_sessions_job,
        'interval',
        hours=cleanup_interval_hours,
        id='cleanup_sessions'
    )
    scheduler.start()
    logger.info(f"✓ Scheduler démarré: nettoyage toutes les {cleanup_interval_hours}h")
    
    logger.info("=" * 70)
    logger.info("✓ Application démarrée avec succès")
    logger.info("=" * 70)
    
    yield
    
    # Arrêt
    logger.info("Arrêt de l'application...")
    scheduler.shutdown()
    logger.info("✓ Scheduler arrêté")
    logger.info("✓ Application arrêtée proprement")


# Initialisation de l'application FastAPI
app = FastAPI(
    title="Work Time Prediction API",
    description="API de prédiction des intervalles horaires de travail avec système de sessions."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # A restreindre en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de quotas
from work_time_prediction.api.middleware.quota_middleware import QuotaMiddleware
app.add_middleware(QuotaMiddleware)

logger.info("Middlewares ajoutés: CORS, Quotas")


# Inclusion du routeur principal contenant les endpoints
app.include_router(router, prefix="/api")
logger.info("Routes enregistrées: session, train_models, predict")

@app.get("/api/")
async def root():
    """Endpoint de vérification de l'état de l'API."""
    return {
        "status": "operational",
        "version": "0.1.0",
        "message": "Work Time Prediction API with Session Management",
        "endpoints": {
            "session": {
                "create": "POST /api/session/create",
                "info": "GET /api/session/info",
                "delete": "DELETE /api/session/delete"
            },
            "training": {
                "train": "POST /api/train_models/"
            },
            "prediction": {
                "predict": "POST /api/predict/"
            }
        }
    }


@app.get("/api/health")
async def health_check():
    """Endpoint de santé pour monitoring."""
    is_healthy = scheduler.running
    
    if is_healthy:
        logger.debug("Health check: OK")
    else:
        logger.warning("Health check: Scheduler non actif")
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "scheduler_running": is_healthy
    }


def run():
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    logger.info("Lancement du serveur uvicorn...")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    run()

