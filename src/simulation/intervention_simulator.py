"""Simulateur d'intervention v0 — scénarios accessibilité / wealth."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class InterventionScenario:
    name: str
    dist_road_delta_km: float = 0.0
    dist_school_delta_km: float = 0.0
    dist_health_delta_km: float = 0.0
    wealth_shift: float = 0.0


def simulate_intervention(
    features: pd.DataFrame,
    scenario: InterventionScenario,
    *,
    priority_col: str = "accessibility_index",
) -> pd.DataFrame:
    """
    Applique un scénario simple sur les distances et estime un delta wealth proxy.
    v0 : heuristique linéaire, pas de réinférence modèle complète.
    """
    out = features.copy()
    if "dist_road_km" in out.columns:
        out["dist_road_km"] = (out["dist_road_km"] + scenario.dist_road_delta_km).clip(lower=0)
    if "dist_school_km" in out.columns:
        out["dist_school_km"] = (out["dist_school_km"] + scenario.dist_school_delta_km).clip(lower=0)
    if "dist_health_km" in out.columns:
        out["dist_health_km"] = (out["dist_health_km"] + scenario.dist_health_delta_km).clip(lower=0)

    dist_mean = out[["dist_road_km", "dist_school_km", "dist_health_km"]].mean(axis=1)
    out["simulated_wealth_delta"] = scenario.wealth_shift - dist_mean * 50.0
    out["scenario"] = scenario.name
    return out


def demo_scenarios() -> list[InterventionScenario]:
    return [
        InterventionScenario("routes_rurales", dist_road_delta_km=-2.0, wealth_shift=5000),
        InterventionScenario("ecoles_proximite", dist_school_delta_km=-1.5, wealth_shift=3000),
        InterventionScenario("sante_mobile", dist_health_delta_km=-3.0, wealth_shift=4000),
    ]