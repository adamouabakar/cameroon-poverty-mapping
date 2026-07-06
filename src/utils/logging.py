"""
Module de journalisation des expériences et runs.
"""

import json
from datetime import datetime
from pathlib import Path


def log_experiment(config: dict, metrics: dict, output_dir: str = "logs"):
    """Enregistre les paramètres et métriques d'une exécution."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    log_data = {
        "timestamp": timestamp,
        "config": config,
        "metrics": metrics
    }
    
    filepath = Path(output_dir) / f"run_{timestamp}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4, ensure_ascii=False)
