#!/usr/bin/env python3
"""
MediPulse AI — Phase 2 Canonical Dataset & Schema Validator

Upgraded validator conforming to Phase 2 specifications:
1. Validates JSON schemas against Draft 2020-12 meta-schema using jsonschema.Draft202012Validator.
2. Validates all canonical reference JSON files against reference_data.schema.json.
3. Checks for test fixtures conforming to medical_report.schema.json (reporting pending status if none exist).
4. Performs comprehensive structural and clinical data integrity checks:
   - 20 canonical biomarker IDs across CBC, Lipid Profile, Diabetes Profile, and KFT.
   - Unique LOINC mappings and registry verification.
   - Distinct classification of reference intervals, diagnostic criteria, and critical limits.
   - Institutional notes and limit types for critical limits.
   - Interval context notes for all demographic reference intervals.
   - Verification of non-empty, valid URLs in provenance.
   - Unresolved citations documentation and consistency between metadata and reference files.
5. All paths are resolved relative to the validator script's root directory.
6. Returns exit code 0 if all required checks pass; exit code 1 if any failure occurs.
"""

import sys
import json
import urllib.parse
from pathlib import Path

# Attempt to import jsonschema and Draft202012Validator
try:
    import jsonschema
    from jsonschema import Draft202012Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    # If running under a python environment without jsonschema installed globally,
    # attempt fallback search in known standard user-site paths on Windows
    candidate_paths = [
        Path.home() / "AppData/Local/Programs/Python/Python313/Lib/site-packages",
        Path.home() / "AppData/Roaming/Python/Python313/site-packages",
        Path.home() / "AppData/Roaming/Python/Python314/site-packages",
    ]
    for cp in candidate_paths:
        if cp.exists() and str(cp) not in sys.path:
            sys.path.insert(0, str(cp))
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        JSONSCHEMA_AVAILABLE = True
    except ImportError:
        JSONSCHEMA_AVAILABLE = False


def get_project_root() -> Path:
    """Resolve project root directory relative to the script file."""
    # This script resides in <project_root>/scripts/validate_phase_2.py
    return Path(__file__).resolve().parent.parent


def validate_schema_meta(schema_path: Path, errors: list):
    """Validate a JSON schema file against Draft 2020-12 meta-schema."""
    if not schema_path.exists():
        errors.append(f"[SCHEMA ERROR] File not found: {schema_path}")
        return None

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
    except Exception as e:
        errors.append(f"[SCHEMA ERROR] Failed to parse JSON in {schema_path}: {e}")
        return None

    # Structural meta checks
    if "$schema" not in schema_data:
        errors.append(f"[SCHEMA ERROR] Missing '$schema' declaration in {schema_path}")
    elif "2020-12" not in schema_data["$schema"]:
        errors.append(f"[SCHEMA ERROR] '$schema' in {schema_path} does not declare Draft 2020-12: {schema_data['$schema']}")

    if "$id" not in schema_data:
        errors.append(f"[SCHEMA ERROR] Missing '$id' identifier in {schema_path}")

    # Official jsonschema meta-schema check
    if JSONSCHEMA_AVAILABLE:
        try:
            Draft202012Validator.check_schema(schema_data)
            print(f"[META-SCHEMA VALID] {schema_path.name} is a valid Draft 2020-12 schema.")
        except jsonschema.exceptions.SchemaError as se:
            errors.append(f"[META-SCHEMA ERROR] {schema_path.name} violates Draft 2020-12 meta-schema: {se.message}")
    else:
        errors.append(f"[DEPENDENCY ERROR] 'jsonschema' library is not installed or available.")

    return schema_data


def validate_instance_against_schema(instance_data: dict, schema_data: dict, instance_name: str, errors: list):
    """Validate JSON instance against compiled Draft 2020-12 schema."""
    if not JSONSCHEMA_AVAILABLE or schema_data is None:
        errors.append(f"[INSTANCE VALIDATION SKIPPED] Cannot validate {instance_name} without jsonschema.")
        return False

    validator = Draft202012Validator(schema_data)
    instance_errors = list(validator.iter_errors(instance_data))

    if instance_errors:
        for err in instance_errors:
            path_str = " -> ".join([str(p) for p in err.path]) if err.path else "root"
            errors.append(f"[INSTANCE ERROR] {instance_name} at '{path_str}': {err.message}")
        return False
    else:
        print(f"[INSTANCE VALID] {instance_name} successfully conforms to schema.")
        return True


def check_url_validity(url: str) -> bool:
    """Verify that URL is non-empty, has a scheme (http/https), and a network location."""
    if not url or not isinstance(url, str):
        return False
    parsed = urllib.parse.urlparse(url.strip())
    return bool(parsed.scheme in ("http", "https") and parsed.netloc)


def main():
    print("=" * 70)
    print("  MEDIPULSE AI — PHASE 2 JSON SCHEMA & REFERENCE DATA VALIDATOR")
    print("=" * 70)

    project_root = get_project_root()
    print(f"Project Root: {project_root}\n")

    errors = []
    warnings = []

    # 1. Dependency check
    if not JSONSCHEMA_AVAILABLE:
        errors.append(
            "[DEPENDENCY ERROR] The 'jsonschema' library is required for Draft 2020-12 validation. "
            "Please ensure jsonschema is available in the Python runtime."
        )
    else:
        try:
            import importlib.metadata
            js_ver = importlib.metadata.version("jsonschema")
        except Exception:
            js_ver = getattr(jsonschema, "__version__", "unknown")
        print(f"[INFO] Using jsonschema library version: {js_ver}")

    # 2. Validate Schemas against Draft 2020-12 Meta-Schema
    print("\n--- 1. SCHEMA META-VALIDATION (Draft 2020-12) ---")
    ref_schema_path = project_root / "datasets/schema/reference_data.schema.json"
    rep_schema_path = project_root / "datasets/schema/medical_report.schema.json"

    ref_schema_data = validate_schema_meta(ref_schema_path, errors)
    rep_schema_data = validate_schema_meta(rep_schema_path, errors)

    # 3. Validate Dataset Metadata
    print("\n--- 2. DATASET METADATA VALIDATION ---")
    metadata_path = project_root / "datasets/metadata/dataset_metadata.json"
    metadata = {}
    if not metadata_path.exists():
        errors.append(f"[METADATA ERROR] Missing metadata file: {metadata_path}")
    else:
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            meta_content = metadata.get("dataset_metadata", {})
            if not meta_content:
                errors.append("[METADATA ERROR] Missing 'dataset_metadata' root key in metadata file.")
            
            # Version & governance check
            spec_ver = meta_content.get("dataset_specification_version")
            if spec_ver != "1.2.0":
                errors.append(f"[METADATA ERROR] Expected dataset_specification_version '1.2.0', got '{spec_ver}'.")
            
            # Unresolved citations check
            unresolved = meta_content.get("unresolved_citations", [])
            if not unresolved:
                errors.append("[METADATA ERROR] Missing 'unresolved_citations' documentation in metadata.")
            else:
                has_acc_aha = any("ACC/AHA" in item.get("source", "") for item in unresolved)
                if not has_acc_aha:
                    errors.append("[METADATA ERROR] Missing unresolved citation documentation for alleged 2026 ACC/AHA update.")
                else:
                    print("[METADATA VALID] Unresolved citation documentation confirmed (ACC/AHA 2026 unresolved status recorded).")

            print(f"[METADATA VALID] {metadata_path.name} conforms to specification version {spec_ver}.")
        except Exception as e:
            errors.append(f"[METADATA ERROR] Failed to load/parse metadata JSON: {e}")

    # 4. Instance Validation of Reference Data JSON Files
    print("\n--- 3. REFERENCE DATA INSTANCE & CLINICAL VALIDATION ---")
    expected_panels = {
        "CBC": ["hemoglobin", "rbc", "wbc", "platelets", "mcv", "mch", "mchc", "hematocrit"],
        "LIPID_PROFILE": ["cholesterol_total", "ldl", "hdl", "triglycerides"],
        "DIABETES_PROFILE": ["glucose_fasting", "glucose_random", "hba1c"],
        "KFT": ["creatinine", "urea", "bun", "egfr", "uric_acid"]
    }

    ref_files = [
        project_root / "datasets/reference_data/cbc_reference.json",
        project_root / "datasets/reference_data/lipid_reference.json",
        project_root / "datasets/reference_data/diabetes_reference.json",
        project_root / "datasets/reference_data/kft_reference.json"
    ]

    seen_metric_ids = set()
    seen_loinc_codes = set()
    total_metrics = 0
    total_intervals = 0
    total_diagnostic_cutoffs = 0
    total_critical_limits = 0
    total_treatment_targets = 0
    total_risk_tiers = 0

    allowed_limit_types = {
        "LABORATORY_SPECIFIC_PANIC_ALERT",
        "CLINICAL_PRACTICE_ALERT_THRESHOLD",
        "CONSENSUS_PANIC_SURVEY_MEDIAN"
    }

    for rf in ref_files:
        if not rf.exists():
            errors.append(f"[FILE ERROR] Missing required reference data file: {rf}")
            continue

        try:
            with open(rf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"[FILE ERROR] JSON parse failure in {rf.name}: {e}")
            continue

        # Schema instance validation
        validate_instance_against_schema(data, ref_schema_data, rf.name, errors)

        panel = data.get("panel_category")
        if panel not in expected_panels:
            errors.append(f"[PANEL ERROR] Unexpected panel_category '{panel}' in {rf.name}.")
            continue

        expected_ids = expected_panels[panel]
        actual_ids = [b.get("metric_id") for b in data.get("biomarkers", [])]

        if sorted(expected_ids) != sorted(actual_ids):
            errors.append(f"[PANEL ERROR] Panel {panel} metric mismatch: Expected {expected_ids}, got {actual_ids}")

        # Biomarker-level clinical checks
        for b in data.get("biomarkers", []):
            total_metrics += 1
            mid = b.get("metric_id")
            cname = b.get("canonical_name", "Unknown")

            if not mid:
                errors.append(f"[BIOMARKER ERROR] Missing 'metric_id' in {rf.name}")
                continue

            if mid in seen_metric_ids:
                errors.append(f"[DUPLICATE ERROR] Duplicate metric_id '{mid}' found in {rf.name}")
            seen_metric_ids.add(mid)

            # LOINC checks
            loinc = b.get("loinc_code")
            if not loinc:
                errors.append(f"[LOINC ERROR] Missing loinc_code for '{mid}' in {rf.name}")
            else:
                if loinc in seen_loinc_codes:
                    errors.append(f"[LOINC ERROR] Duplicate LOINC code '{loinc}' across distinct metrics ({mid})")
                seen_loinc_codes.add(loinc)

            if b.get("loinc_verification_status") != "VERIFIED_REGISTRY":
                errors.append(f"[LOINC ERROR] Metric '{mid}' loinc_verification_status is not 'VERIFIED_REGISTRY'")

            loinc_det = b.get("loinc_details", {})
            if "2.83" not in loinc_det.get("loinc_version", ""):
                errors.append(f"[LOINC ERROR] Metric '{mid}' does not declare LOINC version 2.83")

            # Data concepts separation check
            dc = b.get("data_concepts", {})
            intervals = dc.get("laboratory_reference_intervals", [])
            diag_cutoffs = dc.get("clinical_diagnostic_thresholds", [])
            crit_limits = dc.get("critical_laboratory_limits", [])
            targets = dc.get("treatment_targets", [])
            tiers = dc.get("risk_classification_thresholds", [])

            if not intervals:
                errors.append(f"[INTERVAL ERROR] Metric '{mid}' has no laboratory_reference_intervals defined.")

            total_intervals += len(intervals)
            total_diagnostic_cutoffs += len(diag_cutoffs)
            total_critical_limits += len(crit_limits)
            total_treatment_targets += len(targets)
            total_risk_tiers += len(tiers)

            # Reference Interval nuances
            for inv in intervals:
                cinote = inv.get("interval_context_note")
                if not cinote or len(cinote.strip()) < 10:
                    errors.append(f"[INTERVAL ERROR] Metric '{mid}' reference interval missing comprehensive 'interval_context_note'.")
                if inv.get("min_normal") is None or inv.get("max_normal") is None:
                    errors.append(f"[INTERVAL ERROR] Metric '{mid}' reference interval missing min_normal or max_normal.")
                if inv.get("min_normal") is not None and inv.get("max_normal") is not None:
                    if inv["min_normal"] >= inv["max_normal"]:
                        errors.append(f"[INTERVAL ERROR] Metric '{mid}' min_normal ({inv['min_normal']}) >= max_normal ({inv['max_normal']}).")

            # Critical limits institutional notes & type validation
            for cl in crit_limits:
                ltype = cl.get("limit_type")
                if ltype not in allowed_limit_types:
                    errors.append(f"[CRITICAL LIMIT ERROR] Metric '{mid}' critical limit invalid limit_type: '{ltype}'")
                inote = cl.get("institutional_note")
                if not inote or len(inote.strip()) < 15:
                    errors.append(f"[CRITICAL LIMIT ERROR] Metric '{mid}' critical limit missing comprehensive 'institutional_note'.")
                if cl.get("critical_low") is None and cl.get("critical_high") is None:
                    errors.append(f"[CRITICAL LIMIT ERROR] Metric '{mid}' critical limit has neither critical_low nor critical_high.")

            # Diagnostic thresholds check
            for dt in diag_cutoffs:
                if not dt.get("condition_name") or not dt.get("clinical_criteria"):
                    errors.append(f"[DIAGNOSTIC ERROR] Metric '{mid}' diagnostic threshold missing condition_name or clinical_criteria.")

            # Provenance & URL verification
            prov = b.get("provenance", {})
            if not prov.get("primary_source_organization"):
                errors.append(f"[PROVENANCE ERROR] Metric '{mid}' missing primary_source_organization.")
            if not prov.get("primary_document_title"):
                errors.append(f"[PROVENANCE ERROR] Metric '{mid}' missing primary_document_title.")
            if prov.get("verification_status") != "VERIFIED_DOCUMENTED_SOURCE":
                errors.append(f"[PROVENANCE ERROR] Metric '{mid}' verification_status is not 'VERIFIED_DOCUMENTED_SOURCE'.")

            url = prov.get("source_url")
            if not check_url_validity(url):
                errors.append(f"[PROVENANCE ERROR] Metric '{mid}' has empty or invalid source_url: '{url}'")

    # 5. Medical Report Schema Test Fixtures Check
    print("\n--- 4. MEDICAL REPORT TEST FIXTURES VALIDATION ---")
    fixture_dir = project_root / "tests/fixtures"
    fixture_files = list(fixture_dir.glob("*.json")) if fixture_dir.exists() else []

    if not fixture_files:
        print("[FIXTURE STATUS] Medical report test fixtures are pending (no patient fixtures exist in tests/fixtures/).")
        print("                 Per Phase 2 clinical safety guidelines: Zero synthetic patient records were generated.")
    else:
        print(f"[FIXTURE INFO] Found {len(fixture_files)} fixtures. Validating against medical_report.schema.json...")
        for ff in fixture_files:
            try:
                with open(ff, "r", encoding="utf-8") as f:
                    fix_data = json.load(f)
                validate_instance_against_schema(fix_data, rep_schema_data, ff.name, errors)
            except Exception as e:
                errors.append(f"[FIXTURE ERROR] Failed to validate fixture {ff.name}: {e}")

    # 6. Metadata and Reference JSON Consistency Check
    print("\n--- 5. CROSS-STORE METADATA CONSISTENCY ---")
    if metadata:
        meta_cats = metadata.get("dataset_metadata", {}) .get("supported_categories", [])
        cataloged_biomarkers = set()
        for cat in meta_cats:
            cat_biomarkers = cat.get("biomarker_ids", [])
            for b_id in cat_biomarkers:
                cataloged_biomarkers.add(b_id)

        if cataloged_biomarkers != seen_metric_ids:
            diff_missing = seen_metric_ids - cataloged_biomarkers
            diff_extra = cataloged_biomarkers - seen_metric_ids
            if diff_missing:
                errors.append(f"[CONSISTENCY ERROR] Biomarkers in reference JSON but missing in metadata: {diff_missing}")
            if diff_extra:
                errors.append(f"[CONSISTENCY ERROR] Biomarkers in metadata but missing in reference JSON: {diff_extra}")
        else:
            print("[CONSISTENCY VALID] Metadata biomarker catalog 100% matches reference JSON files.")

    # 7. Summary and Exit Code Resolution
    print("\n" + "=" * 70)
    print("  VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total Canonical Biomarkers Cataloged : {len(seen_metric_ids)} / 20")
    print(f"Total Unique LOINC Codes (LOINC 2.83): {len(seen_loinc_codes)} / 20")
    print(f"Total Reference Intervals Validated  : {total_intervals}")
    print(f"Total Diagnostic Cutoffs Validated   : {total_diagnostic_cutoffs}")
    print(f"Total Critical Limits Validated      : {total_critical_limits}")
    print(f"Total Treatment Targets Documented   : {total_treatment_targets}")
    print(f"Total Risk Classification Tiers      : {total_risk_tiers}")
    print(f"Total Errors Found                   : {len(errors)}")
    print(f"Total Warnings                       : {len(warnings)}")

    if errors:
        print("\n[VALIDATION FAILED] The following errors were identified:")
        for idx, err in enumerate(errors, 1):
            print(f"  {idx}. {err}")
        print("\nExiting with status code 1.")
        sys.exit(1)
    else:
        print("\n[VALIDATION SUCCESS] All Draft 2020-12 schemas, reference data instances,")
        print("                     metadata, and clinical governance constraints PASSED cleanly.")
        print("Exiting with status code 0.")
        sys.exit(0)


if __name__ == "__main__":
    main()
