# src/temporal_event_predictor/models/database.py
# Modèles SQLAlchemy pour l'application

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from temporal_event_predictor.core.constants import DFCols
Base = declarative_base()


class Session(Base):
    """Modèle de session utilisateur."""
    
    __tablename__ = 'sessions'
    
    session_id = Column(String, primary_key=True)
    ip_address = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    session_metadata = Column(Text, default='{}')
    
    # Relations
    security_logs = relationship("SecurityLog", back_populates="session", cascade="all, delete-orphan")
    
    # Index composites
    __table_args__ = (
        Index('idx_sessions_ip_expires', 'ip_address', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<Session(session_id={self.session_id}, ip={self.ip_address})>"
    
    @property
    def is_expired(self) -> bool:
        """Vérifie si la session est expirée."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Vérifie si la session est active."""
        return not self.is_expired


class IPQuota(Base):
    """Modèle des quotas par IP."""
    
    __tablename__ = 'ip_quotas'
    
    ip_address = Column(String, primary_key=True)
    models_count = Column(Integer, default=0)
    storage_used_mb = Column(Float, default=0.0)
    requests_count = Column(Integer, default=0)
    train_count = Column(Integer, default=0)
    predictions_count = Column(Integer, default=0)
    violations_count = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False, index=True)
    banned_until = Column(DateTime, nullable=True, index=True)
    last_reset = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<IPQuota(ip={self.ip_address}, models={self.models_count}, banned={self.is_banned})>"
    
    @property
    def is_currently_banned(self) -> bool:
        """Vérifie si l'IP est actuellement bannie."""
        if not self.is_banned:
            return False
        if self.banned_until is None:
            return True
        return datetime.utcnow() < self.banned_until


class SecurityLog(Base):
    """Modèle des logs de sécurité."""
    
    __tablename__ = 'security_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('sessions.session_id', ondelete='CASCADE'), index=True)
    ip_address = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(Text, nullable=True)
    severity = Column(String, default='INFO', index=True)  # INFO, WARNING, ERROR, CRITICAL
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relations
    session = relationship("Session", back_populates="security_logs")
    
    # Index composites
    __table_args__ = (
        Index('idx_security_logs_ip_date', 'ip_address', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SecurityLog(id={self.id}, type={self.event_type}, severity={self.severity})>"


class ScheduleData(Base):
    """Modèle des données d'horaire (dans data.db de chaque session)."""
    
    __tablename__ = 'schedule_data'
    
    id = Column(DFCols.ID, String, primary_key=True)
    date = Column(DFCols.DATE, String, primary_key=True)
    start_time_by_minutes = Column(DFCols.START_TIME_BY_MINUTES, Integer, nullable=False)
    end_time_by_minutes = Column(DFCols.END_TIME_BY_MINUTES, Integer, nullable=False)
    
    __table_args__ = (
        Index('idx_schedule_data_id', DFCols.ID),
        Index('idx_schedule_data_date', DFCols.DATE),
    )
    
    def __repr__(self):
        return f"<ScheduleData(entity={self.id}, date={self.date})>"