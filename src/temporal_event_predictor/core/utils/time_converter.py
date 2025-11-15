# src/temporal_event_predictor/core/utils/time_converter.py

import pandas as pd
from datetime import datetime

def time_to_minutes(time_str: str) -> float:
    """Convertit 'HH:MM' en minutes flottantes depuis minuit."""
    try:
        if pd.isna(time_str) or not isinstance(time_str, str) or len(time_str) != 5:
            return 0.0
        H, M = map(int, time_str.split(':'))
        return float(H * 60 + M)
    except Exception:
        return 0.0

def minutes_to_time(minutes: float) -> str:
    """Convertit les minutes flottantes en 'HH:MM'."""
    if minutes <= 0:
        return "00:00"
    total_minutes = int(round(minutes))
    H = total_minutes // 60
    M = total_minutes % 60
    return f"{H:02d}:{M:02d}"

def get_date_features(date: datetime) -> dict:
    """Extrait les caractéristiques Day_of_Week et Day_of_Year d'un objet datetime."""
    return {
        'Day_of_Week': date.weekday(),  # Lundi=0, Dimanche=6
        'Day_of_Year': date.timetuple().tm_yday
    }
