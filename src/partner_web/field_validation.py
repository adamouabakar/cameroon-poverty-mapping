"""Field validation: validate site CSV, sample rasters, write discrepancy report."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import rasterio
from rasterio.transform import rowcol
from rasterio.warp import transform as rio_transform

# Allowed vocabulary (normalized lowercase)
WEALTH_BINS = frozenset({"bas", "moyen", "haut"})
UNCERTAINTY_BINS = frozenset({"bas", "moyen", "haut"})
LOCAL_ASSESSMENTS = frozenset(
    {
        "plus pauvre",
        "similaire",
        "plus aisé",
        "plus aise",  # ascii fallback
    }
)

REQUIRED_COLUMNS = (
    "site_id",
    "region",
    "lat",
    "lon",
    "predicted_wealth_bin",
    "uncertainty_bin",
    "local_assessment",
    "notes",
    "observer",
    "date",
)


class FieldValidationError(Exception):
    """Invalid field CSV or sampling failure."""


@dataclass
class SiteRow:
    site_id: str
    region: str
    lat: float | None
    lon: float | None
    predicted_wealth_bin: str
    uncertainty_bin: str
    local_assessment: str
    notes: str
    observer: str
    date: str
    # filled by sampling
    map_wealth: float | None = None
    map_uncertainty: float | None = None
    map_wealth_bin: str | None = None
    map_uncertainty_bin: str | None = None
    concordance: str | None = None  # match | partial | mismatch | unknown


def _norm(s: str) -> str:
    return " ".join(str(s or "").strip().lower().split())


def load_sites_csv(path: Path) -> list[SiteRow]:
    if not path.is_file():
        raise FieldValidationError(f"CSV missing: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise FieldValidationError("CSV has no header")
        cols = {_norm(c).replace(" ", "_") for c in reader.fieldnames}
        # allow flexible header spacing
        missing = []
        header_map = {_norm(c).replace(" ", "_"): c for c in reader.fieldnames}
        for req in REQUIRED_COLUMNS:
            if req not in header_map and req not in cols:
                missing.append(req)
        if missing:
            raise FieldValidationError(f"CSV missing columns: {missing}")

        rows: list[SiteRow] = []
        for i, raw in enumerate(reader, start=2):
            def get(key: str) -> str:
                for k, v in raw.items():
                    if _norm(k).replace(" ", "_") == key:
                        return (v or "").strip()
                return ""

            site_id = get("site_id")
            if not site_id or site_id.lower().startswith("ex"):
                # skip template example rows like ex1
                if site_id.lower().startswith("ex"):
                    continue
            if not site_id:
                raise FieldValidationError(f"line {i}: empty site_id")

            lat_s, lon_s = get("lat"), get("lon")
            lat = float(lat_s) if lat_s else None
            lon = float(lon_s) if lon_s else None
            if lat is not None and not (-90 <= lat <= 90):
                raise FieldValidationError(f"line {i}: invalid lat {lat}")
            if lon is not None and not (-180 <= lon <= 180):
                raise FieldValidationError(f"line {i}: invalid lon {lon}")

            wbin = _norm(get("predicted_wealth_bin"))
            ubin = _norm(get("uncertainty_bin"))
            local = _norm(get("local_assessment"))
            if wbin and wbin not in WEALTH_BINS:
                raise FieldValidationError(
                    f"line {i}: predicted_wealth_bin must be bas|moyen|haut, got {wbin!r}"
                )
            if ubin and ubin not in UNCERTAINTY_BINS:
                raise FieldValidationError(
                    f"line {i}: uncertainty_bin must be bas|moyen|haut, got {ubin!r}"
                )
            if local and local not in LOCAL_ASSESSMENTS:
                raise FieldValidationError(
                    f"line {i}: local_assessment must be "
                    f"'plus pauvre'|'similaire'|'plus aisé', got {local!r}"
                )

            rows.append(
                SiteRow(
                    site_id=site_id,
                    region=get("region"),
                    lat=lat,
                    lon=lon,
                    predicted_wealth_bin=wbin,
                    uncertainty_bin=ubin,
                    local_assessment=local,
                    notes=get("notes"),
                    observer=get("observer"),
                    date=get("date"),
                )
            )
    return rows


def validate_mvp_count(rows: list[SiteRow], minimum: int = 5) -> None:
    if len(rows) < minimum:
        raise FieldValidationError(
            f"MVP requires ≥{minimum} site rows (excluding ex* template rows); got {len(rows)}"
        )


def _tercile_edges(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 0.0, 1.0
    lo, hi = np.nanpercentile(finite, [33.333, 66.666])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = float(np.nanmin(finite)), float(np.nanmax(finite))
        mid = (lo + hi) / 2
        return mid, mid
    return float(lo), float(hi)


def value_to_bin(v: float, lo: float, hi: float) -> str:
    if not np.isfinite(v):
        return ""
    if v <= lo:
        return "bas"
    if v <= hi:
        return "moyen"
    return "haut"


def sample_raster_at(path: Path, coords: list[tuple[float, float]]) -> list[float | None]:
    """Sample band 1 at lon/lat points (WGS84). coords are (lon, lat)."""
    if not path.is_file():
        raise FieldValidationError(f"raster missing: {path}")
    out: list[float | None] = []
    with rasterio.open(path) as ds:
        wgs84 = "EPSG:4326"
        xs: list[float] = []
        ys: list[float] = []
        for lon, lat in coords:
            xs.append(lon)
            ys.append(lat)
        if ds.crs and str(ds.crs).upper() not in (wgs84, "EPSG:4326"):
            xs, ys = rio_transform(wgs84, ds.crs, xs, ys)
        for x, y in zip(xs, ys):
            try:
                r, c = rowcol(ds.transform, x, y)
                if r < 0 or c < 0 or r >= ds.height or c >= ds.width:
                    out.append(None)
                    continue
                val = ds.read(1, window=((r, r + 1), (c, c + 1)))[0, 0]
                if ds.nodata is not None and val == ds.nodata:
                    out.append(None)
                elif not np.isfinite(val):
                    out.append(None)
                else:
                    out.append(float(val))
            except Exception:  # noqa: BLE001
                out.append(None)
    return out


def enrich_with_rasters(
    rows: list[SiteRow],
    wealth_path: Path,
    uncertainty_path: Path,
    *,
    wealth_ref: np.ndarray | None = None,
    unc_ref: np.ndarray | None = None,
) -> list[SiteRow]:
    """Sample map values and assign tercile bins; compute concordance vs local_assessment."""
    coords = []
    for r in rows:
        if r.lat is None or r.lon is None:
            coords.append((float("nan"), float("nan")))
        else:
            coords.append((r.lon, r.lat))

    # For points without coords, skip sampling
    sample_coords = [(lon, lat) for lon, lat in coords if np.isfinite(lon) and np.isfinite(lat)]
    index_map = [
        i for i, (lon, lat) in enumerate(coords) if np.isfinite(lon) and np.isfinite(lat)
    ]

    w_vals = [None] * len(rows)
    u_vals = [None] * len(rows)
    if sample_coords:
        sampled_w = sample_raster_at(wealth_path, sample_coords)
        sampled_u = sample_raster_at(uncertainty_path, sample_coords)
        for j, i in enumerate(index_map):
            w_vals[i] = sampled_w[j]
            u_vals[i] = sampled_u[j]

    # terciles from reference arrays or from sampled finite values
    if wealth_ref is not None:
        w_lo, w_hi = _tercile_edges(np.asarray(wealth_ref, dtype=float))
    else:
        arr = np.array([v for v in w_vals if v is not None], dtype=float)
        w_lo, w_hi = _tercile_edges(arr if arr.size else np.array([0.0, 1.0]))

    if unc_ref is not None:
        u_lo, u_hi = _tercile_edges(np.asarray(unc_ref, dtype=float))
    else:
        arr = np.array([v for v in u_vals if v is not None], dtype=float)
        u_lo, u_hi = _tercile_edges(arr if arr.size else np.array([0.0, 1.0]))

    for i, r in enumerate(rows):
        r.map_wealth = w_vals[i]
        r.map_uncertainty = u_vals[i]
        if w_vals[i] is not None:
            r.map_wealth_bin = value_to_bin(w_vals[i], w_lo, w_hi)
        if u_vals[i] is not None:
            r.map_uncertainty_bin = value_to_bin(u_vals[i], u_lo, u_hi)
        r.concordance = _concordance(r)
    return rows


def _concordance(r: SiteRow) -> str:
    """Local assessment vs map wealth bin."""
    local = r.local_assessment
    mbin = r.map_wealth_bin or r.predicted_wealth_bin
    if not local or not mbin:
        return "unknown"
    # map high wealth = "plus aisé" expected if similar
    if local in ("similaire",):
        return "match" if mbin else "unknown"
    if local in ("plus pauvre",):
        # map should be bas or moyen
        if mbin == "bas":
            return "match"
        if mbin == "moyen":
            return "partial"
        return "mismatch"
    if local in ("plus aisé", "plus aise"):
        if mbin == "haut":
            return "match"
        if mbin == "moyen":
            return "partial"
        return "mismatch"
    return "unknown"


def write_reports(
    rows: list[SiteRow],
    out_md: Path,
    out_json: Path,
    *,
    partner: str,
    workshop_date: str,
    workshop_minutes: int,
    region_focus: str,
    map_url: str,
    extra_notes: str = "",
) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    n = len(rows)
    counts = {"match": 0, "partial": 0, "mismatch": 0, "unknown": 0}
    for r in rows:
        counts[r.concordance or "unknown"] = counts.get(r.concordance or "unknown", 0) + 1

    lines = [
        f"# Note d'écarts — validation terrain MVP",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d')} UTC*",
        "",
        "## Contexte",
        "",
        f"- **Partenaire :** {partner}",
        f"- **Atelier :** {workshop_date} ({workshop_minutes} min)",
        f"- **Région focus :** {region_focus or '—'}",
        f"- **Sites (CSV) :** {n}",
        f"- **Carte :** {map_url}",
        "",
        "## Rappel éthique",
        "",
        "Estimations exploratoires uniquement. **Pas** de stats INS. **Pas** de ciblage "
        "ménage/village. Croiser toujours l'incertitude. Voir `documentation/limitations.md`.",
        "",
        "## Synthèse concordance (carte vs lecture locale)",
        "",
        f"| Concordance | n |",
        f"|-------------|---|",
        f"| match | {counts.get('match', 0)} |",
        f"| partial | {counts.get('partial', 0)} |",
        f"| mismatch | {counts.get('mismatch', 0)} |",
        f"| unknown | {counts.get('unknown', 0)} |",
        "",
        "## Sites",
        "",
        "| site_id | region | local | map_wealth_bin | map_unc_bin | concordance | notes |",
        "|---------|--------|-------|----------------|-------------|-------------|-------|",
    ]
    for r in rows:
        notes = (r.notes or "").replace("|", "/")[:80]
        lines.append(
            f"| {r.site_id} | {r.region} | {r.local_assessment} | "
            f"{r.map_wealth_bin or r.predicted_wealth_bin or '—'} | "
            f"{r.map_uncertainty_bin or r.uncertainty_bin or '—'} | "
            f"{r.concordance} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Où la carte marche",
            "",
            "_À compléter après atelier : zones de bonne concordance._",
            "",
            "## Où la carte échoue",
            "",
            "_À compléter : mismatches, rural faible signal, jitter._",
            "",
            "## Lecture incertitude",
            "",
            "_À compléter : l'incertitude élevée correspond-elle aux doutes locaux ?_",
            "",
            "## Suite",
            "",
            "- Ne pas allouer de budget sur la base de cette carte seule.",
            "- Ouvrir des issues techniques si le partenaire demande UI/données (dropdown, etc.).",
            "",
        ]
    )
    if extra_notes.strip():
        lines.extend(["## Notes atelier", "", extra_notes.strip(), ""])

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "partner": partner,
        "workshop_date": workshop_date,
        "workshop_minutes": workshop_minutes,
        "region_focus": region_focus,
        "map_url": map_url,
        "n_sites": n,
        "concordance_counts": counts,
        "sites": [asdict(r) for r in rows],
        "ethics": "exploratory_only_no_targeting_no_official_ins",
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
