# src/temporal_event_predictor/core/exceptions.py
# Exceptions personnalisées pour l'application

class ModelNotTrainedError(Exception):
    """Exception levée lorsque le modèle n'est pas encore entraîné."""
    def __init__(self, message="Le modèle d'apprentissage automatique n'est pas encore entraîné."):
        self.message = message
        super().__init__(self.message)

class IDNotFoundError(Exception):
    """Exception levée lorsque l'ID de l'employé est inconnu."""
    def __init__(self, employee_id: str):
        self.message = f"L'employé avec l'ID '{employee_id}' est introuvable dans les données historiques."
        super().__init__(self.message)

class InvalidCsvFormatError(Exception):
    """Exception levée lorsque le fichier CSV est invalide ou vide."""
    def __init__(self, message="Le fichier CSV est vide ou son format est incorrect."):
        self.message = message
        super().__init__(self.message)

class NoDataFoundError(Exception):
    """Exception levée lorsque le jeu de données est vide."""
    def __init__(self, message="Aucune donnée dans la base de données."):
        self.message = message
        super().__init__(self.message)
