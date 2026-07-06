"""
Module de gestion de la configuration du projet.
"""

from pathlib import Path
import yaml


def load_config(config_path: str = "configs/default.yaml") -> dict:
    """Charge le fichier de configuration YAML."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config