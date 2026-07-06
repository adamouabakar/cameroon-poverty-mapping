"""
Chargement des grappes DHS Cameroun 2018 (GPS + ménages).

Mode fictif : génère 50 grappes pour tests et développement.
Mode réel   : lit les fichiers .dta DHS (GE + HR), agrège le wealth index
              au niveau grappe, puis applique le jitter DHS avant exposition.

Les coordonnées réelles ne sont jamais retournées sans jitter.
"""

from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from src.data.jitter import simulate_dhs_jitter

# Noms de fichiers attendus (Cameroun 2018, enquête 7)
_GPS_DTA_PATTERN = re.compile(r"^CMGE.*\.dta$", re.IGNORECASE)
_GPS_SHP_PATTERN = re.compile(r"^CMGE.*\.shp$", re.IGNORECASE)
_HR_PATTERN = re.compile(r"^CMHR.*\.dta$", re.IGNORECASE)

# Correspondances colonnes DHS standard → schéma pipeline
_CLUSTER_COLS = ("DHSCLUST", "hv001", "cluster", "cluster_id")
_LAT_COLS = ("LATNUM", "LAT", "latitude", "lat")
_LON_COLS = ("LONGNUM", "LONG", "longitude", "lon")
_URBAN_COLS = ("URBAN_RURA", "URBAN_RURAL", "URBAN", "urban_rural")
_REGION_COLS = ("DHSREGNA", "DHSREGCO", "hv024", "region", "REGION")

_WEALTH_COLS = ("hv271", "wealth_index", "wealth_index_score")
_HR_CLUSTER_COLS = ("hv001", "DHSCLUST", "cluster_id")
_HR_REGION_COLS = ("hv024", "region")


def _first_existing(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _normalize_urban_rural(series: pd.Series) -> pd.Series:
    """Convertit les codes DHS (U/R, 1/0, texte) vers 'urban' | 'rural'."""
    mapping = {
        "u": "urban",
        "r": "rural",
        "urban": "urban",
        "rural": "rural",
        "1": "urban",
        "1.0": "urban",
        "0": "rural",
        "0.0": "rural",
        "2": "rural",
        "2.0": "rural",
    }
    normalized = (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map(mapping)
    )
    if normalized.isna().any():
        unknown = series[normalized.isna()].unique()[:5]
        raise ValueError(
            f"Valeurs urbain/rural non reconnues : {list(unknown)}. "
            "Attendu : U/R, urban/rural, ou 1/0."
        )
    return normalized


def _resolve_dhs_dir(dhs_dir: str | Path | None) -> Path:
    if dhs_dir is None:
        return Path("data/raw/dhs")
    return Path(dhs_dir)


def _iter_dhs_files(dhs_dir: Path) -> list[Path]:
    """Liste récursivement les fichiers du répertoire DHS (sous-dossiers inclus)."""
    if not dhs_dir.exists():
        return []
    return [p for p in dhs_dir.rglob("*") if p.is_file()]


def _find_dhs_file(dhs_dir: Path, pattern: re.Pattern[str]) -> Path | None:
    matches = sorted(p for p in _iter_dhs_files(dhs_dir) if pattern.match(p.name))
    return matches[0] if matches else None


def _find_gps_file(dhs_dir: Path) -> Path | None:
    """Préfère le .dta GPS ; sinon shapefile CMGE (distribution DHS courante)."""
    dta = _find_dhs_file(dhs_dir, _GPS_DTA_PATTERN)
    if dta is not None:
        return dta
    return _find_dhs_file(dhs_dir, _GPS_SHP_PATTERN)


def has_real_dhs_files(dhs_dir: str | Path | None = None) -> bool:
    """Indique si les fichiers GPS et ménages DHS sont présents."""
    root = _resolve_dhs_dir(dhs_dir)
    return _find_gps_file(root) is not None and _find_dhs_file(root, _HR_PATTERN) is not None


def _load_fake_clusters(n_clusters: int = 50, random_state: int = 42) -> gpd.GeoDataFrame:
    """Génère des grappes fictives (développement / tests)."""
    print("⚠️  Mode fictif activé (pas de fichiers DHS réels)")
    rng = np.random.default_rng(random_state)

    data = {
        "cluster_id": range(1, n_clusters + 1),
        "wealth_index": rng.normal(loc=0, scale=1, size=n_clusters),
        "urban_rural": rng.choice(["urban", "rural"], size=n_clusters),
        "region": rng.choice(
            [
                "Adamaoua", "Centre", "Est", "Extrême-Nord",
                "Littoral", "Nord", "Nord-Ouest", "Ouest",
                "Sud", "Sud-Ouest",
            ],
            size=n_clusters,
        ),
        "latitude": rng.uniform(2, 13, size=n_clusters),
        "longitude": rng.uniform(8, 16, size=n_clusters),
    }
    df = pd.DataFrame(data)
    geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def _gps_coords_already_displaced(gps_path: Path) -> bool:
    """
    Les shapefiles CMGE distribués par DHS contiennent des coordonnées
    déjà déplacées selon la politique officielle (voir GPS_Displacement_README).
    """
    return gps_path.suffix.lower() == ".shp"


def _load_gps_clusters(gps_path: Path) -> pd.DataFrame:
    """Charge et normalise le fichier GPS (.dta ou shapefile CMGE)."""
    if gps_path.suffix.lower() == ".shp":
        gps = gpd.read_file(gps_path)
        if not isinstance(gps, pd.DataFrame):
            gps = pd.DataFrame(gps.drop(columns="geometry", errors="ignore"))
    else:
        gps = pd.read_stata(gps_path)

    cluster_col = _first_existing(gps, _CLUSTER_COLS)
    lat_col = _first_existing(gps, _LAT_COLS)
    lon_col = _first_existing(gps, _LON_COLS)
    urban_col = _first_existing(gps, _URBAN_COLS)
    region_col = _first_existing(gps, _REGION_COLS)

    missing = [
        name for name, col in [
            ("cluster", cluster_col),
            ("latitude", lat_col),
            ("longitude", lon_col),
            ("urban_rural", urban_col),
        ]
        if col is None
    ]
    if missing:
        raise KeyError(
            f"Colonnes GPS manquantes dans {gps_path.name} : {missing}. "
            f"Colonnes disponibles : {list(gps.columns)}"
        )

    out = pd.DataFrame({
        "cluster_id": gps[cluster_col].astype(int),
        "latitude_raw": gps[lat_col].astype(float),
        "longitude_raw": gps[lon_col].astype(float),
        "urban_rural": _normalize_urban_rural(gps[urban_col]),
    })
    if region_col is not None:
        out["region"] = gps[region_col].astype(str).str.strip()
    else:
        out["region"] = "unknown"

    # Une ligne par grappe (fichier GE peut contenir des doublons)
    out = (
        out.dropna(subset=["latitude_raw", "longitude_raw"])
        .drop_duplicates(subset=["cluster_id"], keep="first")
        .reset_index(drop=True)
    )
    return out


def _load_household_wealth(hr_path: Path) -> pd.DataFrame:
    """Agrège le wealth index (hv271) au niveau grappe."""
    hr = pd.read_stata(hr_path)

    cluster_col = _first_existing(hr, _HR_CLUSTER_COLS)
    wealth_col = _first_existing(hr, _WEALTH_COLS)
    region_col = _first_existing(hr, _HR_REGION_COLS)

    if cluster_col is None:
        raise KeyError(
            f"Colonne grappe introuvable dans {hr_path.name}. "
            f"Colonnes disponibles : {list(hr.columns)}"
        )
    if wealth_col is None:
        raise KeyError(
            f"Colonne wealth index introuvable dans {hr_path.name}. "
            "Attendu : hv271 (score factoriel DHS)."
        )

    hr = hr.dropna(subset=[wealth_col])
    hr["cluster_id"] = hr[cluster_col].astype(int)

    agg: dict[str, str] = {"wealth_index": (wealth_col, "mean")}
    if region_col is not None:
        agg["region"] = (region_col, lambda s: s.mode().iloc[0] if len(s) else "unknown")

    cluster_wealth = (
        hr.groupby("cluster_id", as_index=False)
        .agg(**agg)
    )
    return cluster_wealth


def _load_real_clusters(
    dhs_dir: Path,
    *,
    apply_jitter: bool | None,
    random_state: int | None,
) -> gpd.GeoDataFrame:
    """Charge les vraies grappes DHS, fusionne GPS + ménages, gère le jitter."""
    gps_path = _find_gps_file(dhs_dir)
    hr_path = _find_dhs_file(dhs_dir, _HR_PATTERN)

    if gps_path is None or hr_path is None:
        raise FileNotFoundError(
            f"Fichiers DHS introuvables dans {dhs_dir}. "
            "Attendu : CMGE*.shp ou CMGE*.dta (GPS) et CMHR*.dta (ménages)."
        )

    coords_displaced = _gps_coords_already_displaced(gps_path)
    if apply_jitter is None:
        apply_jitter = not coords_displaced

    print(f"📂 Chargement DHS réel : {gps_path.name} + {hr_path.name}")

    gps_df = _load_gps_clusters(gps_path)
    wealth_df = _load_household_wealth(hr_path)

    merged = gps_df.merge(wealth_df, on="cluster_id", how="inner", suffixes=("", "_hr"))

    # Priorité à la région du fichier GPS ; repli sur HR si absente
    if "region_hr" in merged.columns:
        merged["region"] = merged["region"].where(
            merged["region"].ne("unknown"),
            merged["region_hr"],
        )
        merged = merged.drop(columns=["region_hr"])

    if merged.empty:
        raise ValueError("Aucune grappe après jointure GPS ↔ ménages.")

    missing_wealth = merged["wealth_index"].isna().sum()
    if missing_wealth:
        raise ValueError(f"{missing_wealth} grappe(s) sans wealth_index après agrégation.")

    # Coordonnées réelles : utilisées uniquement en interne pour le jitter
    merged["latitude"] = merged["latitude_raw"]
    merged["longitude"] = merged["longitude_raw"]

    geometry = gpd.points_from_xy(merged["longitude_raw"], merged["latitude_raw"])
    gdf = gpd.GeoDataFrame(merged, geometry=geometry, crs="EPSG:4326")

    if apply_jitter:
        gdf = simulate_dhs_jitter(gdf, random_state=random_state)
        gdf["displacement_source"] = "simulated_dhs_policy"
        print(
            f"✓ Jitter DHS simulé sur {len(gdf)} grappes "
            f"(médiane : {gdf['jitter_distance_km'].median():.2f} km)"
        )
    elif coords_displaced:
        gdf["displacement_source"] = "dhs_official_ge"
        print(
            f"✓ Coordonnées GE officielles (déjà jitterées DHS) — "
            f"{len(gdf)} grappes, pas de double déplacement"
        )
    else:
        raise ValueError(
            "Coordonnées GPS non déplacées détectées sans apply_jitter=True. "
            "Les coordonnées brutes ne doivent pas être exposées."
        )

    # Schéma de sortie compatible pipeline (sans coordonnées brutes)
    keep_cols = [
        "cluster_id", "wealth_index", "urban_rural", "region",
        "latitude", "longitude", "displacement_source",
        "jitter_distance_km", "jitter_extended",
    ]
    keep_cols = [c for c in keep_cols if c in gdf.columns]
    return gdf[keep_cols + ["geometry"]]


def load_dhs_clusters(
    dhs_dir: str | Path | None = None,
    *,
    use_fake: bool | None = None,
    apply_jitter: bool | None = None,
    random_state: int | None = 42,
    n_fake_clusters: int = 50,
) -> gpd.GeoDataFrame:
    """
    Charge les grappes DHS Cameroun 2018.

    Parameters
    ----------
    dhs_dir : répertoire contenant CMGE*.dta et CMHR*.dta
    use_fake : True = fictif, False = réel, None = auto-détection
    apply_jitter : None = auto (GE officiel → pas de double jitter ; .dta brut → simuler)
    random_state : graine du jitter / données fictives

    Returns
    -------
    GeoDataFrame (EPSG:4326) avec :
        cluster_id, wealth_index, urban_rural, region,
        latitude, longitude, geometry
    """
    root = _resolve_dhs_dir(dhs_dir)
    real_available = has_real_dhs_files(root)

    if use_fake is None:
        use_fake = not real_available

    if use_fake:
        gdf = _load_fake_clusters(n_clusters=n_fake_clusters, random_state=random_state or 42)
        if apply_jitter:
            gdf = simulate_dhs_jitter(gdf, random_state=random_state)
        return gdf

    return _load_real_clusters(
        root,
        apply_jitter=apply_jitter,
        random_state=random_state,
    )