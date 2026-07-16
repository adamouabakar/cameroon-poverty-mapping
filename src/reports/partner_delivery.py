"""Génération packs de livraison partenaires — Phase 4."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from src.reports.partner_profile import PartnerProfile
from src.reports.pdf_report import generate_ngo_pdf_report
from src.reports.region_stats import compute_regional_summary, load_cluster_frame
from src.reports.report_config import ReportOptions
from src.reports.watchlist import evaluate_watchlist


def _brief_markdown(profile: PartnerProfile, *, lang: str) -> str:
    if lang == "en":
        return f"""# Partner delivery — {profile.display_name}

**Focus region:** {profile.focus_region}  
**Contact:** {profile.options.contact_email}  
**Generated:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## Package contents

- PDF report ({lang.upper()})
- Regional statistics CSV
- Watchlist alerts JSON
- Field validation template reference

## Ethics

Exploratory estimates only. Not official INS statistics. No household/village targeting.
"""
    return f"""# Livraison partenaire — {profile.display_name}

**Région focus :** {profile.focus_region}  
**Contact :** {profile.options.contact_email}  
**Généré :** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## Contenu du pack

- Rapport PDF ({lang.upper()})
- Statistiques régionales CSV
- Alertes watchlist JSON
- Référence protocole validation terrain

## Éthique

Estimations exploratoires uniquement. Ne remplace pas l'INS. Pas de ciblage ménage/village.
"""


def build_partner_delivery(
    project_root: Path,
    profile: PartnerProfile,
    *,
    langs: tuple[str, ...] = ("fr", "en"),
    output_dir: Path | None = None,
) -> Path:
    """
    Génère un dossier + ZIP de livraison pour un partenaire.

    Retourne le chemin du fichier .zip.
    """
    root = Path(project_root)
    out = output_dir or root / "partner_pack" / "deliveries" / profile.partner_id
    out.mkdir(parents=True, exist_ok=True)

    clusters = load_cluster_frame(root)
    region = profile.focus_region
    summary = compute_regional_summary(clusters, region=region)
    full_summary = compute_regional_summary(clusters)
    alerts = evaluate_watchlist(full_summary, profile.options.watchlist_rules, lang="fr")

    summary.to_csv(out / "regional_stats.csv", index=False)
    alerts.to_json(out / "watchlist_alerts.json", orient="records", indent=2, force_ascii=False)

    for lang in langs:
        opts = ReportOptions(
            language=lang,
            region=region,
            focus_region=profile.focus_region,
            partner_id=profile.partner_id,
            organization=profile.options.organization,
            logo_path=profile.options.logo_path,
            contact_email=profile.options.contact_email,
            sections=profile.options.sections,
            field_csv=profile.options.field_csv,
            watchlist_rules=profile.options.watchlist_rules,
        )
        pdf_path = out / f"ngo_report_{lang}.pdf"
        generate_ngo_pdf_report(root, region=region, output_path=pdf_path, options=opts)
        brief_path = out / f"brief_{lang}.md"
        brief_path.write_text(_brief_markdown(profile, lang=lang), encoding="utf-8")

    manifest = {
        "phase": 4,
        "partner_id": profile.partner_id,
        "display_name": profile.display_name,
        "focus_region": profile.focus_region,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "languages": list(langs),
        "files": sorted(p.name for p in out.iterdir() if p.is_file()),
        "config": str(profile.config_path.relative_to(root)),
    }
    (out / "delivery_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    zip_path = out.parent / f"{profile.partner_id}_delivery.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out.iterdir():
            if f.is_file():
                zf.write(f, arcname=f"{profile.partner_id}/{f.name}")

    return zip_path