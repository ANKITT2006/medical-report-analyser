"""
Clinical Dataset Seeding & Ingestion CLI Script.
Validates clinical data schema formats and populates the database layer.
Supports both Phase 2 canonical reference panels and legacy protocol definitions.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clinical_engine.storage.repository import SQLClinicalRepository

def seed_database(db_path: str = "data/clinical_knowledge.db") -> dict:
    project_root = Path(__file__).resolve().parent.parent
    panels = [
        project_root / "datasets/reference_data/cbc_reference.json",
        project_root / "datasets/reference_data/lipid_reference.json",
        project_root / "datasets/reference_data/diabetes_reference.json",
        project_root / "datasets/reference_data/kft_reference.json"
    ]

    print(f"[*] Ingesting Phase 2 canonical reference panels into database: {db_path}")
    repo = SQLClinicalRepository(db_path=db_path)
    counts = repo.ingest_canonical_reference_panels(panels)

    print("  [+] Canonical ingestion summary:")
    for entity, count in counts.items():
        print(f"      - {entity}: {count} records")

    # Seed legacy clinical protocols & mappings
    legacy_file = project_root / "data/canonical_clinical_dataset.json"
    if legacy_file.exists():
        print(f"[*] Ingesting clinical protocols from: {legacy_file}")
        with open(legacy_file, "r", encoding="utf-8") as f:
            p_data = json.load(f)
        protocols_count = repo.bulk_load_dataset({"protocols": p_data.get("protocols", []), "mappings": p_data.get("mappings", [])})
        print(f"  [+] Ingested {protocols_count} protocol & mapping records.")

    return counts

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed clinical knowledge database.")
    parser.add_argument("--db", default="data/clinical_knowledge.db", help="Path to SQLite database")
    args = parser.parse_args()

    try:
        res = seed_database(args.db)
        print(f"[SUCCESS] Clinical knowledge base initialized successfully.")
    except Exception as err:
        print(f"[ERROR] Failed to seed clinical database: {err}", file=sys.stderr)
        sys.exit(1)
