#!/usr/bin/env python
"""Générateur rapport décisionnel HTML (Jalon 4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    v4 = json.loads((PROJECT_ROOT / "outputs/reports/model_v4_results.json").read_text())
    ins = json.loads((PROJECT_ROOT / "outputs/reports/ins_external_validation.json").read_text())
    m = v4["metrics_v4_oof"]
    im = ins["metrics"]

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"/><title>Rapport décisionnel</title>
<style>body{{font-family:system-ui;max-width:800px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:0.5rem}}</style></head>
<body>
<h1>Rapport décisionnel — Cameroun Poverty Mapping</h1>
<p><em>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</em></p>
<h2>Métriques modèle v4</h2>
<table><tr><th>Métrique</th><th>Valeur</th></tr>
<tr><td>R² OOF</td><td>{m['r2']:.4f}</td></tr>
<tr><td>Spearman</td><td>{m['spearman']:.4f}</td></tr>
<tr><td>RMSE</td><td>{m['rmse']:.0f}</td></tr></table>
<h2>Validation INS</h2>
<p>Spearman wealth ↔ pauvreté : <strong>{im['spearman_wealth_vs_poverty']:.3f}</strong></p>
<h2>Recommandations</h2>
<ul>
<li>Croiser carte wealth avec incertitude avant toute décision.</li>
<li>Validation terrain sur Extrême-Nord, Nord, Douala.</li>
<li>Ne pas utiliser pour ciblage ménage/village.</li>
</ul>
<p><a href="../site/index.html">Carte interactive</a></p>
</body></html>"""

    out = PROJECT_ROOT / "outputs/reports/decision_report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"✅ Rapport : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())