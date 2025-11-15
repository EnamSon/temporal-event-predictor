# src/temporal_event_predictor/core/utils/temporal_features.py

import pandas as pd
import numpy as np
from datetime import datetime

def get_week_of_month(date: pd.Timestamp | datetime) -> int:
    """
    Calcule l'indice de la semaine du mois (base 0) pour une date donnée.
    La première semaine du mois a l'indice 0.

    Args:
        date: Un objet pandas Timestamp.

    Returns:
        Un entier représentant l'indice de la semaine du mois (0, 1, 2, 3, 4, ou 5).
    """
    day_of_month = date.day
    first_day_of_month = date.replace(day=1)
    day_of_week_first = first_day_of_month.weekday()
    week_of_month = int(np.ceil((day_of_month + day_of_week_first) / 7.0))

    return week_of_month - 1