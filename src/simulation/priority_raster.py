"""
Carte raster d'indice de priorisation (Phase 2).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
import yaml

from src.simulation.prioritization import (
    combine_normalized_components,
    load_prioritization_config,
    normalize_component,
)


def _read_band(src: rasterio.DatasetReader, name: str, band_idx: dict[str, int]) -> int:
    if name not in band_idx:
        raise KeyError(f"Bande {name} absente du raster {src.name}")
    return band_idx[name]


def _band_index_map(src: rasterio.DatasetReader) -> dict[str, int]:
    band_idx: dict[str, int] = {}
    for i in range(1, src.count + 1):
        desc = src.descriptions[i - 1] if src.descriptions else None
        if desc:
            band_idx[desc] = i
    return band_idx


def _component_stats(
    wealth_path: Path,
    features_path: Path,
    criteria: dict,
    *,
    chunk_size: int = 512,
    nodata: float = -9999.0,
) -> dict[str, tuple[float, float]]:
    """Passe 1 : percentiles globaux pour chaque composant."""
    comp_cfg = criteria["components"]
    norm_cfg = criteria.get("normalization", {})
    p_low = norm_cfg.get("percentile_low", 5)
    p_high = norm_cfg.get("percentile_high", 95)

    samples: dict[str, list[np.ndarray]] = {
        "poverty": [],
        "dist_school": [],
        "dist_health": [],
        "dist_road": [],
    }

    with rasterio.open(wealth_path) as wealth_src, rasterio.open(features_path) as feat_src:
        feat_bands = _band_index_map(feat_src)
        for ji in range(0, wealth_src.height, chunk_size):
            h = min(chunk_size, wealth_src.height - ji)
            for ii in range(0, wealth_src.width, chunk_size):
                w = min(chunk_size, wealth_src.width - ii)
                window = rasterio.windows.Window(ii, ji, w, h)

                wealth = wealth_src.read(1, window=window).astype(np.float32)
                valid = np.isfinite(wealth) & (wealth != nodata)
                if valid.any():
                    samples["poverty"].append(wealth[valid])

                for key, band_key in [
                    ("dist_school", "dist_school"),
                    ("dist_health", "dist_health"),
                    ("dist_road", "dist_road"),
                ]:
                    band_name = comp_cfg[band_key]["band"]
                    scale = comp_cfg[band_key].get("scale", 1.0)
                    band_no = _read_band(feat_src, band_name, feat_bands)
                    dist = feat_src.read(band_no, window=window).astype(np.float32) * scale
                    dvalid = np.isfinite(dist) & (dist != nodata)
                    if dvalid.any():
                        samples[key].append(dist[dvalid])

    stats = {}
    for key, chunks in samples.items():
        if not chunks:
            stats[key] = (0.0, 1.0)
            continue
        vals = np.concatenate(chunks)
        stats[key] = (float(np.percentile(vals, p_low)), float(np.percentile(vals, p_high)))
    return stats


def compute_priority_raster(
    wealth_path: str | Path,
    features_path: str | Path,
    criteria_path: str | Path,
    output_path: str | Path,
    *,
    chunk_size: int = 512,
    nodata: float = -9999.0,
) -> Path:
    """
    Produit une carte 1 km d'indice de priorisation composite.
    """
    wealth_path = Path(wealth_path)
    features_path = Path(features_path)
    criteria = load_prioritization_config(criteria_path)
    weights = criteria["weights"]
    comp_cfg = criteria["components"]

    stats = _component_stats(
        wealth_path, features_path, criteria, chunk_size=chunk_size, nodata=nodata
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(wealth_path) as wealth_src, rasterio.open(features_path) as feat_src:
        feat_bands = _band_index_map(feat_src)
        profile = wealth_src.profile.copy()
        profile.update(count=1, dtype="float32", nodata=nodata)

        with rasterio.open(output_path, "w", **profile) as dst:
            for ji in range(0, wealth_src.height, chunk_size):
                h = min(chunk_size, wealth_src.height - ji)
                for ii in range(0, wealth_src.width, chunk_size):
                    w = min(chunk_size, wealth_src.width - ii)
                    window = rasterio.windows.Window(ii, ji, w, h)

                    wealth = wealth_src.read(1, window=window).astype(np.float32)
                    poverty = normalize_component(
                        wealth,
                        *stats["poverty"],
                        invert=comp_cfg["poverty"].get("invert", True),
                        nodata=nodata,
                    )

                    components = {"poverty": poverty}
                    for key, band_key in [
                        ("dist_school", "dist_school"),
                        ("dist_health", "dist_health"),
                        ("dist_road", "dist_road"),
                    ]:
                        band_name = comp_cfg[band_key]["band"]
                        scale = comp_cfg[band_key].get("scale", 1.0)
                        band_no = _read_band(feat_src, band_name, feat_bands)
                        dist = feat_src.read(band_no, window=window).astype(np.float32) * scale
                        components[key] = normalize_component(
                            dist, *stats[key], nodata=nodata
                        )

                    priority = combine_normalized_components(
                        components, weights, nodata=nodata
                    )
                    dst.write(priority, 1, window=window)

    return output_path