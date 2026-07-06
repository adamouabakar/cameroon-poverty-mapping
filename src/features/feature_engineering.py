"""
Module de feature engineering (création de nouvelles variables).
"""

import pandas as pd
import numpy as np


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée de nouvelles features à partir des existantes.
    Exemple : ratios, transformations logarithmiques, etc.
    """
    df = df.copy()
    # Exemple
    # if 'night_lights' in df.columns:
    #     df['log_night_lights'] = np.log1p(df['night_lights'])
    return df