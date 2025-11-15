# src/temporal_event_predictor/core/ml/occurrence_features.py
# Extraction des features pour prédire l'occurrence d'un événement

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from functools import lru_cache

from temporal_event_predictor.core.constants import DFCols
from temporal_event_predictor.core.utils.logging_config import get_logger

logger = get_logger()


class OccurrenceFeatureExtractor:
    """
    Extracteur de features pour prédire si un événement va se produire.
    Utilise un cache pour optimiser les calculs répétés.
    """
    
    def __init__(self):
        """Initialise l'extracteur avec un cache vide."""
        self._cache: Dict[str, Dict] = {}
    
    def compute_entity_stats(
        self, 
        entity_id: str, 
        history: pd.DataFrame
    ) -> Dict:
        """
        Calcule les statistiques globales d'une entité (cachées).
        
        Args:
            entity_id: ID de l'entité
            history: Historique complet de l'entité
        
        Returns:
            Dict avec les statistiques cachées
        """
        # Vérifier le cache
        cache_key = f"{entity_id}_{len(history)}"  # Clé avec taille pour invalider si données changent
        
        if cache_key in self._cache:
            logger.debug(f"Cache hit pour {entity_id}")
            return self._cache[cache_key]
        
        logger.debug(f"Calcul des stats pour {entity_id} ({len(history)} événements)")
        
        # Trier par date
        history_sorted = history.sort_values(DFCols.DATE)
        
        # 1. Stats par jour de la semaine
        weekday_stats = self._compute_weekday_stats(history_sorted)
        
        # 2. Gaps entre événements
        gaps = self._compute_gaps_between_events(history_sorted)
        stddev_gap = float(np.std(gaps)) if len(gaps) > 1 else 0.0
        
        # 3. Score de périodicité
        periodicity_score = self._compute_periodicity_score(gaps)
        
        # Construire le cache
        stats = {
            'weekday_stats': weekday_stats,
            'stddev_gap_between_events': stddev_gap,
            'periodicity_score': periodicity_score,
            'total_events': len(history),
            'history_span_days': (history_sorted[DFCols.DATE].max() - history_sorted[DFCols.DATE].min()).days
        }
        
        # Mettre en cache
        self._cache[cache_key] = stats
        
        return stats
    
    def extract_features(
        self,
        entity_id: str,
        target_date: datetime,
        history: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Extrait toutes les features d'occurrence pour une date donnée.
        
        Args:
            entity_id: ID de l'entité
            target_date: Date cible pour la prédiction
            history: Historique de l'entité
        
        Returns:
            Dict avec toutes les features
        """
        # Récupérer les stats cachées
        stats = self.compute_entity_stats(entity_id, history)
        
        # Features spécifiques à la date cible
        weekday = target_date.weekday()
        from temporal_event_predictor.core.utils.temporal_features import get_week_of_month
        week_of_month = get_week_of_month(target_date)
        
        # Récupérer les stats du jour de la semaine
        weekday_info = stats['weekday_stats'].get(weekday, {
            'occurrence_count': 0,
            'occurrence_rate': 0.0,
            'total_opportunities': 0
        })
        
        return {
            'weekday_occurrence_rate': weekday_info['occurrence_rate'],
            'weekday_occurrence_count': weekday_info['occurrence_count'],
            'stddev_gap_between_events': stats['stddev_gap_between_events'],
            'periodicity_score': stats['periodicity_score'],
            'week_of_month': float(week_of_month)
        }
    
    def should_predict_event(
        self,
        entity_id: str,
        target_date: datetime,
        history: pd.DataFrame,
        min_occurrence_count: int = 2,
        min_occurrence_rate: float = 0.15
    ) -> Tuple[bool, float, str]:
        """
        Détermine si on doit prédire un événement pour cette date.
        
        Args:
            entity_id: ID de l'entité
            target_date: Date cible
            history: Historique de l'entité
            min_occurrence_count: Nombre minimum d'occurrences requises
            min_occurrence_rate: Taux minimum d'occurrence requis
        
        Returns:
            Tuple (should_predict, confidence, reason)
        """
        features = self.extract_features(entity_id, target_date, history)
        
        occurrence_count = int(features['weekday_occurrence_count'])
        occurrence_rate = features['weekday_occurrence_rate']
        
        # Règle 1 : Pas assez de données
        if occurrence_count < min_occurrence_count:
            return False, 0.0, f"Échantillon insuffisant ({occurrence_count} < {min_occurrence_count})"
        
        # Règle 2 : Taux trop faible
        if occurrence_rate < min_occurrence_rate:
            return False, occurrence_rate, f"Taux trop faible ({occurrence_rate:.1%} < {min_occurrence_rate:.1%})"
        
        # Règle 3 : OK pour prédire
        return True, occurrence_rate, f"Prédiction autorisée (taux: {occurrence_rate:.1%}, n={occurrence_count})"
    
    def _compute_weekday_stats(self, history: pd.DataFrame) -> Dict[int, Dict]:
        """
        Calcule les statistiques par jour de la semaine.
        
        Args:
            history: Historique trié par date
        
        Returns:
            Dict {weekday: {occurrence_count, occurrence_rate, total_opportunities}}
        """
        if history.empty:
            return {}
        
        # Compter les occurrences par jour de la semaine
        weekday_counts = history[DFCols.DATE].dt.dayofweek.value_counts().to_dict()
        
        # Calculer le nombre total de chaque jour dans la période
        min_date = history[DFCols.DATE].min()
        max_date = history[DFCols.DATE].max()
        total_days = (max_date - min_date).days + 1
        
        weekday_stats = {}
        
        for weekday in range(7):
            # Nombre d'occurrences de ce jour
            occurrence_count = weekday_counts.get(weekday, 0)
            
            # Nombre total de ce jour dans la période
            total_opportunities = self._count_weekdays_in_range(min_date, max_date, weekday)
            
            # Taux d'occurrence
            occurrence_rate = occurrence_count / total_opportunities if total_opportunities > 0 else 0.0
            
            weekday_stats[weekday] = {
                'occurrence_count': occurrence_count,
                'occurrence_rate': occurrence_rate,
                'total_opportunities': total_opportunities
            }
        
        return weekday_stats
    
    def _count_weekdays_in_range(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        target_weekday: int
    ) -> int:
        """
        Compte le nombre d'un jour de la semaine spécifique dans une plage.
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            target_weekday: Jour cible (0=lundi, 6=dimanche)
        
        Returns:
            Nombre de ce jour dans la plage
        """
        count = 0
        current = start_date
        
        while current <= end_date:
            if current.weekday() == target_weekday:
                count += 1
            current += timedelta(days=1)
        
        return count
    
    def _compute_gaps_between_events(self, history: pd.DataFrame) -> List[int]:
        """
        Calcule les gaps (en jours) entre événements consécutifs.
        
        Args:
            history: Historique trié par date
        
        Returns:
            Liste des gaps en jours
        """
        if len(history) < 2:
            return []
        
        dates = history[DFCols.DATE].tolist()
        gaps = []
        
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i-1]).days
            if gap > 0:  # Ignorer les événements le même jour
                gaps.append(gap)
        
        return gaps
    
    def _compute_periodicity_score(self, gaps: List[int]) -> float:
        """
        Calcule un score de périodicité basé sur les gaps.
        Score élevé = événements réguliers, score faible = événements irréguliers.
        
        Args:
            gaps: Liste des gaps entre événements
        
        Returns:
            Score entre 0 (très irrégulier) et 1 (très régulier)
        """
        if len(gaps) < 3:
            return 0.0
        
        # Méthode 1 : Coefficient de variation inverse
        # Plus le CV est faible, plus c'est régulier
        mean_gap = np.mean(gaps)
        std_gap = np.std(gaps)
        
        if mean_gap == 0:
            return 0.0
        
        cv = std_gap / mean_gap  # Coefficient de variation
        
        # Transformer CV en score 0-1 (inverse et normaliser)
        # CV faible (~0) -> score élevé (~1)
        # CV élevé (>1) -> score faible (~0)
        periodicity_score = 1.0 / (1.0 + cv)
        
        return float(periodicity_score)
    
    def clear_cache(self, entity_id: Optional[str] = None):
        """
        Vide le cache (partiellement ou totalement).
        
        Args:
            entity_id: Si fourni, vide seulement le cache de cette entité
        """
        if entity_id:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(entity_id)]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug(f"Cache vidé pour {entity_id}")
        else:
            self._cache.clear()
            logger.debug("Cache complètement vidé")
    
    def get_cache_stats(self) -> Dict:
        """Retourne des statistiques sur le cache."""
        return {
            'cache_size': len(self._cache),
            'cached_entities': len(set(k.split('_')[0] for k in self._cache.keys()))
        }


# Instance globale (une par session si nécessaire)
def create_occurrence_extractor() -> OccurrenceFeatureExtractor:
    """Crée une nouvelle instance d'extracteur."""
    return OccurrenceFeatureExtractor()