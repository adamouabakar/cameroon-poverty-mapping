#!/usr/bin/env python
"""
Génère un pack de livraison partenaire (PDF, CSV, brief, ZIP).

Usage:
  python scripts/generate_partner_delivery.py --partner nord_humanitaire
  python scripts/generate_partner_delivery.py --all
  python scripts/generate_partner_delivery.py --partner generic_ngo --lang fr
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.reports.partner_delivery import build_partner_delivery
from src.reports.partner_profile import list_partner_profiles, load_partner_profile


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pack livraison partenaire Phase 4")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--partner", help="Identifiant partenaire (configs/partners/)")
    g.add_argument("--all", action="store_true", help="Générer pour tous les profils")
    p.add_argument("--lang", action="append", choices=["fr", "en"], default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    langs = tuple(args.lang) if args.lang else ("fr", "en")

    if args.all:
        profiles = list_partner_profiles(PROJECT_ROOT)
        if not profiles:
            print("Aucun profil dans configs/partners/")
            return 1
        for profile in profiles:
            zip_path = build_partner_delivery(PROJECT_ROOT, profile, langs=langs)
            print(f"✅ {profile.partner_id} → {zip_path}")
        return 0

    profile = load_partner_profile(PROJECT_ROOT, args.partner)
    zip_path = build_partner_delivery(PROJECT_ROOT, profile, langs=langs)
    print(f"✅ Livraison générée : {zip_path}")
    print(f"   Partenaire : {profile.display_name}")
    print(f"   Région focus : {profile.focus_region}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())