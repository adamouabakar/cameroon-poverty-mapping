"""Generate site/index.html + limitations pages (relative assets, vendored Leaflet)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.partner_web import EXIT_IO


class HtmlError(Exception):
    def __init__(self, message: str, code: int = EXIT_IO):
        super().__init__(message)
        self.code = code


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Cartographie exploratoire — {country} DHS {dhs_year}</title>
  <link rel="stylesheet" href="vendor/leaflet/leaflet.css"/>
  <style>
    :root {{ --banner-bg: #1a1a1a; --banner-fg: #f5f5f5; --map-bg: #e8eef2; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, Segoe UI, sans-serif; color: #111; background: #fafafa; }}
    #banner {{
      position: sticky; top: 0; z-index: 1000;
      background: var(--banner-bg); color: var(--banner-fg);
      padding: 0.65rem 1rem; font-size: 0.9rem; line-height: 1.35;
    }}
    #banner .en {{ opacity: 0.85; font-size: 0.8rem; margin-top: 0.25rem; }}
    header h1 {{ font-size: 1.15rem; margin: 0.75rem 1rem 0.25rem; }}
    header .sub {{ margin: 0 1rem 0.5rem; color: #444; font-size: 0.9rem; }}
    #map {{ height: min(62vh, 520px); width: 100%; background: var(--map-bg); border-top: 1px solid #ccc; border-bottom: 1px solid #ccc; }}
    .controls {{
      display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem;
      padding: 0.75rem 1rem; align-items: center; background: #fff;
    }}
    .controls label {{ font-size: 0.9rem; cursor: pointer; }}
    .legends {{ display: flex; flex-wrap: wrap; gap: 1rem; padding: 0.5rem 1rem 1rem; }}
    .legend {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 0.5rem 0.75rem; min-width: 160px; font-size: 0.8rem; }}
    .legend strong {{ display: block; margin-bottom: 0.25rem; }}
    .swatch {{ height: 10px; border-radius: 2px; margin: 0.35rem 0; }}
    .swatch-wealth {{ background: linear-gradient(90deg, #ffffcc, #fd8d3c, #800026); }}
    .swatch-priority {{ background: linear-gradient(90deg, #f2f0f7, #9e9ac8, #3f007d); }}
    .swatch-uncertainty {{ background: linear-gradient(90deg, #f7fbff, #6baed6, #08306b); }}
    footer {{ padding: 1rem; font-size: 0.8rem; color: #333; border-top: 1px solid #ddd; background: #f0f0f0; }}
    footer a {{ color: #0645ad; }}
    @media print {{
      #banner {{ position: static; }}
      .controls {{ display: none; }}
    }}
    @media (max-width: 640px) {{
      #map {{ height: 50vh; }}
      .controls {{ position: sticky; bottom: 0; z-index: 900; box-shadow: 0 -2px 8px rgba(0,0,0,.08); }}
    }}
  </style>
</head>
<body>
  <div id="banner" role="note">
    <div>{banner_fr}</div>
    <div class="en">{banner_en} · <a href="limitations_en.html" style="color:#9cf">EN limitations</a></div>
  </div>
  <header>
    <h1>Estimations exploratoires — {country} DHS {dhs_year}</h1>
    <p class="sub">R² OOF {r2} · Spearman {spearman} · n={n_clusters} · CV {cv} · unités wealth: {wealth_units}</p>
  </header>
  <div id="map" aria-label="Carte nationale"></div>
  <div class="controls">
    <label><input type="radio" name="layer" value="wealth" checked/> {label_wealth}</label>
    <label><input type="radio" name="layer" value="priority"/> {label_priority}</label>
    <label><input type="radio" name="layer" value="uncertainty"/> {label_uncertainty}</label>
  </div>
  <div class="legends">
    <div class="legend"><strong>Richesse (active)</strong><div class="swatch swatch-wealth"></div>bas → élevé (estimation)</div>
    <div class="legend"><strong>Incertitude (toujours visible)</strong><div class="swatch swatch-uncertainty"></div>croiser avant lecture</div>
    <div class="legend"><strong>Priorisation</strong><div class="swatch swatch-priority"></div>non opérationnel</div>
  </div>
  <footer>
    <p><strong>Contact :</strong> <a href="mailto:{email}">{email}</a> — délai de réponse non garanti.</p>
    <p>{anti_targeting}</p>
    <p>
      <a href="limitations.html">Limitations (FR)</a> ·
      <a href="limitations_en.html">Limitations (EN)</a> ·
      Sources : DHS, GEE/open data · MIT ·
      <span id="offline-note">Fond basemap optionnel si réseau ; couches d'estimation packagées en local.</span>
    </p>
  </footer>
  <script src="vendor/leaflet/leaflet.js"></script>
  <script>
    const BOUNDS = {bounds_json};
    const corner1 = L.latLng(BOUNDS.south, BOUNDS.west);
    const corner2 = L.latLng(BOUNDS.north, BOUNDS.east);
    const bounds = L.latLngBounds(corner1, corner2);
    const map = L.map('map', {{
      maxZoom: 11,
      minZoom: 5,
      zoomControl: true,
      attributionControl: true
    }});
    map.fitBounds(bounds);
    // Optional OSM only when online — never required offline
    if (navigator.onLine) {{
      try {{
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          maxZoom: 11,
          attribution: '&copy; OpenStreetMap',
          opacity: 0.45
        }}).addTo(map);
      }} catch (e) {{ /* ignore */ }}
    }} else {{
      document.getElementById('offline-note').textContent =
        'Mode hors-ligne : pas de fond OSM ; overlays estimation disponibles.';
    }}
    const layers = {{
      wealth: L.imageOverlay('assets/wealth.png', bounds, {{ opacity: 0.85 }}),
      priority: L.imageOverlay('assets/priority.png', bounds, {{ opacity: 0.85 }}),
      uncertainty: L.imageOverlay('assets/uncertainty.png', bounds, {{ opacity: 0.85 }})
    }};
    let current = layers.wealth;
    current.addTo(map);
    document.querySelectorAll('input[name=layer]').forEach((el) => {{
      el.addEventListener('change', () => {{
        if (!el.checked) return;
        map.removeLayer(current);
        current = layers[el.value];
        current.addTo(map);
      }});
    }});
  </script>
</body>
</html>
"""


def ensure_leaflet_vendor(vendor_dir: Path, leaflet_src: Path) -> None:
    """Copy vendored Leaflet into site/vendor/leaflet from leaflet_src directory."""
    vendor_dir.mkdir(parents=True, exist_ok=True)
    targets = ("leaflet.js", "leaflet.css")
    src = leaflet_src
    if not src.is_dir():
        raise HtmlError(f"Leaflet vendor missing; expected directory {src}")
    for name in targets:
        s = src / name
        if not s.is_file():
            raise HtmlError(f"missing Leaflet file: {s}")
        shutil.copy2(s, vendor_dir / name)
    img_src = src / "images"
    if img_src.is_dir():
        img_dst = vendor_dir / "images"
        if img_dst.exists():
            shutil.rmtree(img_dst)
        shutil.copytree(img_src, img_dst)


def write_site_html(
    site_dir: Path,
    claims: dict[str, Any],
    metrics: dict[str, Any],
    bounds: dict[str, float],
    *,
    leaflet_src: Path,
) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    try:
        ensure_leaflet_vendor(site_dir / "vendor" / "leaflet", leaflet_src=leaflet_src)
    except HtmlError:
        raise
    except OSError as exc:
        raise HtmlError(f"vendor copy failed: {exc}") from exc

    labels = claims["layer_labels"]
    html = INDEX_TEMPLATE.format(
        country=claims["country"],
        dhs_year=claims["dhs_year"],
        banner_fr=claims["banner_fr"].replace("\n", " ").strip(),
        banner_en=claims["banner_en_one_liner"].replace("\n", " ").strip(),
        r2=_fmt(metrics.get("r2")),
        spearman=_fmt(metrics.get("spearman")),
        n_clusters=metrics.get("n_clusters", "?"),
        cv=metrics.get("cv_strategy", "?"),
        wealth_units=claims.get("wealth_units", "?"),
        label_wealth=labels["wealth"],
        label_priority=labels["priority"],
        label_uncertainty=labels["uncertainty"],
        email=claims["contact_email"],
        anti_targeting=str(claims["anti_targeting_fr"]).replace("\n", " ").strip(),
        bounds_json=json.dumps(bounds),
    )
    (site_dir / "index.html").write_text(html, encoding="utf-8")

    lim_fr = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/><title>Limitations</title>
    <style>body{{font-family:system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}</style></head>
    <body><h1>Limitations</h1>
    <p>{claims["banner_fr"]}</p>
    <p>{claims["anti_targeting_fr"]}</p>
    <p>Jitter GPS DHS (2 km urbain / 5 km rural). Proxy richesse ≠ pauvreté monétaire officielle.
    Données d'enquête {claims["dhs_year"]}. Voir documentation/limitations.md dans le dépôt.</p>
    <p><a href="index.html">← Carte</a></p></body></html>"""
    lim_en = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>Limitations</title>
    <style>body{{font-family:system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}</style></head>
    <body><h1>Limitations</h1>
    <p>{claims["banner_en_one_liner"]}</p>
    <p>DHS GPS jitter (2 km urban / 5 km rural). Wealth index is a proxy, not official poverty.
    Survey year {claims["dhs_year"]}. See documentation/limitations.md in the repository.</p>
    <p><a href="index.html">← Map</a></p></body></html>"""
    (site_dir / "limitations.html").write_text(lim_fr, encoding="utf-8")
    (site_dir / "limitations_en.html").write_text(lim_en, encoding="utf-8")


def _fmt(v: Any) -> str:
    try:
        return f"{float(v):.3f}"
    except (TypeError, ValueError):
        return str(v)
