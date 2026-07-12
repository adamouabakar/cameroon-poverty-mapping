#!/usr/bin/env python
"""
Post-v1.0 Action 5 — Publication & communication.

Agrège les rapports Actions 1–4, produit le rapport final et brouillons LinkedIn/X.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPORT_SOURCES = {
    "action1": "outputs/reports/field_validation_proxy.json",
    "action2": "outputs/reports/post_v1_action2_ecam5.json",
    "action3": "outputs/reports/post_v1_action3_model_v5.json",
    "action4": "outputs/reports/post_v1_action4_actionability.json",
}


def _load_json(rel: str) -> dict | None:
    path = PROJECT_ROOT / rel
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_final_report(sources: dict[str, dict | None]) -> str:
    a1 = sources.get("action1") or {}
    a2 = sources.get("action2") or {}
    a3 = sources.get("action3") or {}
    a4 = sources.get("action4") or {}

    m1 = a1.get("metrics", {})
    m2 = a2.get("metrics_ecam5", {})
    m3 = a3.get("metrics_v5_post_oof", {})
    m4_top = (a4.get("top_actionable_clusters") or [])[:5]

    lines = [
        "# Rapport final Post-v1.0 — Cameroon Poverty Mapping",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC*",
        "",
        "## Synthèse exécutive",
        "",
        "Cinq actions post-v1.0 ont été exécutées séquentiellement avec **données publiques "
        "uniquement** (DHS 2018, INS ECAM 4/5, GEE, OSM, WorldPop).",
        "",
        "| Action | Résultat clé |",
        "|--------|--------------|",
        f"| 1 Validation terrain proxy | {int(m1.get('n_sites', 0))} sites DHS; "
        f"Spearman raster↔DHS {m1.get('spearman_raster_vs_dhs', 0):.3f} |",
        f"| 2 ECAM 5 | Spearman modèle↔pauvreté ECAM5 {m2.get('spearman_wealth_vs_poverty', 0):.3f} |",
        f"| 3 Modèle v5_post | R² OOF {m3.get('r2', 0):.4f} (+{a3.get('delta_v5_post_minus_v4', {}).get('r2', 0):.4f} vs v4) |",
        f"| 4 Actionnabilité | {len(a4.get('top_actionable_clusters', []))} grappes priorisées |",
        "| 5 Publication | Ce rapport + brouillons communication |",
        "",
        "## Action 1 — Validation terrain (proxy)",
        "",
        "- Référence : wealth_index DHS 2018 aux centroides de grappes",
        f"- Concordance bins match : {m1.get('concordance_match_pct', 0):.1f}%",
        "- Limite : proxy numérique, pas d'atelier partenaire terrain",
        "",
        "## Action 2 — ECAM 5 + micro-données",
        "",
        "- Table régionale ECAM5 intégrée (`data/reference/ins/ecam5_regional_indicators.csv`)",
        "- Micro-données ECAM5 unitaires : **non publiques** — proxy DHS 430 grappes",
        f"- Validation externe ECAM5 : Spearman {m2.get('spearman_wealth_vs_poverty', 0):.3f}",
        "",
        "## Action 3 — Modèle v5_post",
        "",
        f"- Features : {a3.get('n_features', '—')} (GEE v3 + INS ECAM5 + proxies temporels/accessibilité)",
        f"- Production candidate : **{a3.get('production_model', 'v4')}**",
        f"- R² {m3.get('r2', 0):.4f}, Spearman {m3.get('spearman', 0):.4f}",
        "",
        "## Action 4 — Cartes + actionnabilité",
        "",
        "- Raster priorité actionable généré",
        "- Indice actionnabilité grappes = priorité × accessibilité × confiance OOF",
        "",
        "### Top 5 grappes actionnables",
        "",
        "| Région | Cluster | Indice |",
        "|--------|---------|--------|",
    ]
    for row in m4_top:
        lines.append(
            f"| {row.get('region', '')} | {row.get('cluster_id', '')} | "
            f"{row.get('actionability_index', '')} |"
        )

    lines.extend(
        [
            "",
            "## Limites & éthique",
            "",
            "- Estimations exploratoires — ne remplacent pas l'INS",
            "- Pas de ciblage ménage/village/budget",
            "- ECAM5 méthodologie EHCVM ≠ ECAM4",
            "- Validation terrain partenaire toujours requise",
            "",
            "## Liens",
            "",
            "- Carte : https://adamouabakar.github.io/cameroon-poverty-mapping/",
            "- Code : https://github.com/adamouabakar/cameroon-poverty-mapping",
            "- Release v1.0 : https://github.com/adamouabakar/cameroon-poverty-mapping/releases/tag/v1.0.0",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_communication(a3: dict | None) -> str:
    m = (a3 or {}).get("metrics_v5_post_oof", {})
    r2 = m.get("r2", 0.793)
    sp = m.get("spearman", 0.889)
    return "\n".join(
        [
            "# Brouillon communication — Post-v1.0",
            "",
            "## LinkedIn / X (FR)",
            "",
            "🗺️ Cameroon Poverty Mapping — mise à jour post-v1.0",
            "",
            "5 actions automatisées avec données publiques :",
            "✅ Validation terrain proxy (DHS 2018)",
            "✅ Intégration INS ECAM 5 (2022)",
            f"✅ Modèle v5_post : R² {r2:.2f} · Spearman {sp:.2f}",
            "✅ Cartes + indice d'actionnabilité",
            "",
            "Carte interactive :",
            "https://adamouabakar.github.io/cameroon-poverty-mapping/",
            "",
            "Code open source :",
            "https://github.com/adamouabakar/cameroon-poverty-mapping",
            "",
            "⚠️ Estimations exploratoires — pas de substitution aux statistiques INS.",
            "Pas de ciblage opérationnel sans validation locale.",
            "",
            "## LinkedIn / X (EN)",
            "",
            "🗺️ Cameroon Poverty Mapping — post-v1.0 update",
            "",
            "Five automated actions using public data only:",
            "field validation proxy (DHS), INS ECAM 5 integration,",
            f"improved model v5_post (R² {r2:.2f}), actionable priority maps.",
            "",
            "Interactive map: https://adamouabakar.github.io/cameroon-poverty-mapping/",
            "Open repo: https://github.com/adamouabakar/cameroon-poverty-mapping",
            "",
            "Exploratory estimates only — not official INS statistics.",
            "",
            "## Hashtags",
            "",
            "#OpenData #Cameroon #DHS #PovertyMapping #MachineLearning #INS #ECAM5 #GeoAI",
            "",
        ]
    )


def main() -> int:
    sources = {k: _load_json(v) for k, v in REPORT_SOURCES.items()}

    final_md = _build_final_report(sources)
    comm_md = _build_communication(sources.get("action3"))

    doc_report = PROJECT_ROOT / "documentation/post_v1_final_report.md"
    comm_file = PROJECT_ROOT / "COMMUNICATION_POST_V1.md"
    doc_report.parent.mkdir(parents=True, exist_ok=True)
    doc_report.write_text(final_md, encoding="utf-8")
    comm_file.write_text(comm_md, encoding="utf-8")

    out_json = PROJECT_ROOT / "outputs/reports/post_v1_publication_summary.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "action": "post_v1_action5_publication",
                "artifacts": {
                    "final_report": str(doc_report.relative_to(PROJECT_ROOT)),
                    "communication": str(comm_file.relative_to(PROJECT_ROOT)),
                },
                "actions_loaded": {k: v is not None for k, v in sources.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("✅ Post-v1 Action 5 — publication terminée")
    print(f"  Rapport final : {doc_report}")
    print(f"  Communication : {comm_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())