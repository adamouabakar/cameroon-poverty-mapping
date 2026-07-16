"""Alertes régionales basées sur seuils configurables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.reports.report_config import ReportOptions, t


def evaluate_watchlist(
    summary: pd.DataFrame,
    rules: list[dict[str, Any]],
    *,
    lang: str = "fr",
) -> pd.DataFrame:
    """
    Évalue les règles sur le tableau régional (sans ligne nationale).

    Retourne colonnes : region, metric, value, threshold, alert_label
    """
    if not rules or summary.empty:
        return pd.DataFrame(columns=["region", "metric", "value", "threshold", "alert_label"])

    rows = summary[summary["region"] != "Tout le Cameroun"].copy()
    alerts: list[dict[str, Any]] = []

    for _, row in rows.iterrows():
        for rule in rules:
            metric = rule.get("metric")
            if not metric or metric not in row.index:
                continue
            value = float(row[metric])
            threshold = float(rule.get("threshold", 0))
            direction = rule.get("direction", "above")
            fired = value >= threshold if direction == "above" else value <= threshold
            if fired:
                label = rule.get(f"label_{lang}") or rule.get("label_fr", metric)
                alerts.append(
                    {
                        "region": row["region"],
                        "metric": metric,
                        "value": round(value, 1),
                        "threshold": threshold,
                        "alert_label": label,
                    }
                )

    return pd.DataFrame(alerts)


def format_alerts_text(alerts: pd.DataFrame, *, lang: str = "fr") -> list[str]:
    if alerts.empty:
        return [t("watchlist_title", lang) + " : " + ("Aucune alerte." if lang == "fr" else "No alerts.")]
    lines = [t("watchlist_title", lang) + ":"]
    for _, a in alerts.iterrows():
        lines.append(
            f"• {a['region']} — {a['alert_label']} ({a['metric']}={a['value']}, seuil={a['threshold']})"
        )
    return lines