"""Partner pack: brief, deep-dives, offline zip, WhatsApp strip."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Any

from src.partner_web import EXIT_IO
from src.partner_web.render import array_to_png


class PackError(Exception):
    def __init__(self, message: str, code: int = EXIT_IO):
        super().__init__(message)
        self.code = code


def write_brief(pack_dir: Path, claims: dict[str, Any], metrics: dict[str, Any]) -> Path:
    pack_dir.mkdir(parents=True, exist_ok=True)
    path = pack_dir / "brief_fr.md"
    body = f"""# Brief partenaire — {claims['country']} (DHS {claims['dhs_year']})

## En une phrase

Estimations **exploratoires** de bien-être relatif à ~1 km, calibrées sur l'indice de richesse des grappes DHS, croisées avec des données satellitaires ouvertes. **Ce n'est pas** une statistique officielle de l'INS.

## Performance modèle (OOF, CV spatiale)

| Métrique | Valeur |
|----------|--------|
| R² OOF | {metrics.get('r2')} |
| Spearman OOF | {metrics.get('spearman')} |
| RMSE | {metrics.get('rmse')} |
| Grappes | {metrics.get('n_clusters')} |
| CV | {metrics.get('cv_strategy')} |
| Unités wealth | {claims.get('wealth_units')} |

## Comment lire la carte

1. Commencer par la couche **richesse** (vue large).
2. Croiser **toujours** l'incertitude (légende toujours visible sur le site).
3. La couche **priorisation** est un indice composite exploratoire (pauvreté estimée + accessibilité OSM) — **non opérationnel**, pas un classement de villages.
4. Ne pas interpréter au niveau ménage / village (jitter GPS DHS).

## Ce que nous demandons en atelier

- Feedback : zones où la carte contredit le savoir local.
- Discussion sur l'incertitude et les limites.
- Si pertinent : validation terrain selon `field_validation_protocol.md` (pas de collecte non autorisée).

## Contact

{claims['contact_email']} — délai de réponse non garanti.

## Interdits d'usage

{claims['anti_targeting_fr']}
"""
    path.write_text(body, encoding="utf-8")
    return path


def write_deep_dives(
    pack_dir: Path,
    stack_pngs: dict[str, Path],
    claims: dict[str, Any],
    regions: tuple[str, str] = ("Littoral", "Extrême-Nord"),
) -> list[Path]:
    """Copy national PNGs as deep-dive illustrations + short guided notes (V1 national crops)."""
    out: list[Path] = []
    for region in regions:
        slug = _slug(region)
        md = pack_dir / f"deep_dive_{slug}.md"
        # Use wealth PNG as illustration (full national; region text guides reading)
        for key in ("wealth", "uncertainty"):
            src = stack_pngs.get(key)
            if src and src.is_file():
                dst = pack_dir / f"deep_dive_{slug}_{key}.png"
                shutil.copy2(src, dst)
                out.append(dst)
                _watermark_note(dst)
        md.write_text(
            f"""# Deep-dive — {region}

## Lecture guidée

1. Ouvrir la carte nationale (`site/index.html` ou zip offline).
2. Localiser approximativement la région **{region}** (vue large uniquement).
3. Comparer richesse et incertitude : zones floues = ne pas sur-interpréter.
4. Priorisation = scénario exploratoire, pas un ordre d'intervention.

## Limites

{claims['banner_fr']}

## Fichiers

- `deep_dive_{slug}_wealth.png`
- `deep_dive_{slug}_uncertainty.png`
""",
            encoding="utf-8",
        )
        out.append(md)
    return out


def write_email_template(pack_dir: Path, claims: dict[str, Any]) -> Path:
    path = pack_dir / "email_prise_de_contact_fr.md"
    path.write_text(
        f"""# Email type — prise de contact

**Objet :** Cartes exploratoires de bien-être ({claims['country']}, DHS {claims['dhs_year']}) — feedback 45 min

Bonjour,

Je développe un pipeline open-source qui estime un proxy de richesse à ~1 km pour le {claims['country']},
avec cartes d'incertitude et garde-fous éthiques (pas de ciblage ménage/village).

Je souhaite partager une carte web + un brief FR et recueillir votre lecture locale (45 minutes).

Lien carte : [à compléter après déploiement Pages]
Contact : {claims['contact_email']}

Cordialement,
""",
        encoding="utf-8",
    )
    return path


def write_csv_template(pack_dir: Path) -> Path:
    path = pack_dir / "field_validation_template.csv"
    path.write_text(
        "site_id,region,lat,lon,predicted_wealth_bin,uncertainty_bin,local_assessment,notes,observer,date\n"
        "ex1,Littoral,,,moyen,moyen,similaire,,,\n",
        encoding="utf-8",
    )
    return path


def copy_field_protocol(project_root: Path, pack_dir: Path) -> Path | None:
    src = project_root / "documentation" / "field_validation_protocol.md"
    if not src.is_file():
        return None
    dst = pack_dir / "field_validation_protocol.md"
    shutil.copy2(src, dst)
    return dst


def write_whatsapp_strip(pack_dir: Path, stack_arrays: dict[str, Any], claims: dict[str, Any]) -> list[Path]:
    """Square-ish PNGs + caption for WhatsApp (watermark text in caption file)."""
    wa = pack_dir / "whatsapp_strip"
    wa.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    cmaps = {"wealth": "YlOrRd", "priority": "Purples", "uncertainty": "Blues"}
    for key, arr in stack_arrays.items():
        out = wa / f"{key}.png"
        array_to_png(arr, out, cmap=cmaps.get(key, "viridis"))
        paths.append(out)
    caption = wa / "caption_fr.txt"
    caption.write_text(
        f"{claims['country']} DHS {claims['dhs_year']}: estimations exploratoires (pas INS). "
        f"Pas de ciblage ménage/village. Croiser incertitude. Contact {claims['contact_email']}",
        encoding="utf-8",
    )
    paths.append(caption)
    return paths


def make_offline_zip(site_dir: Path, pack_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if site_dir.is_dir():
                for f in site_dir.rglob("*"):
                    if f.is_file():
                        zf.write(f, arcname=str(Path("site") / f.relative_to(site_dir)))
            if pack_dir.is_dir():
                for f in pack_dir.rglob("*"):
                    if f.is_file() and f.suffix != ".zip":
                        zf.write(f, arcname=str(Path("partner_pack") / f.relative_to(pack_dir)))
    except OSError as exc:
        raise PackError(f"zip failed: {exc}") from exc
    return zip_path


def _slug(name: str) -> str:
    return (
        name.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace(" ", "_")
        .replace("-", "_")
    )


def _watermark_note(png_path: Path) -> None:
    """Sidecar note — visual watermark is the filename + pack brief (print CSS on web)."""
    note = png_path.with_suffix(".png.txt")
    note.write_text("Estimation exploratoire — pas un ciblage\n", encoding="utf-8")
