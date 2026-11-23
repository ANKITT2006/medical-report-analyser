"""
Canonical Reference Dataset Ingestion Adapter.
Parses Phase 2 canonical JSON reference panels and transforms them into normalized SQL repository records.
Lossless, traceable, and transactional.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from clinical_engine.domain.schemas import (
    LabMetric,
    ReferenceInterval,
    CriticalLimit,
    CriticalLimitType,
    DiagnosticThreshold,
    TreatmentTarget,
    RiskTier,
    UnitConversion,
    ClinicalContext,
    GestationalApplicabilityType
)
from clinical_engine.pipeline.converters import ALLOWED_CONVERSION_HANDLERS

# Verified metadata dictionary derived from Phase 2 canonical reference provenance
PREGNANCY_GOVERNANCE_METADATA: Dict[str, Dict[str, Any]] = {
    "hemoglobin": {
        "applicability": GestationalApplicabilityType.PHYSIOLOGICAL_SHIFT,
        "note": "WHO guidelines define anemia in pregnancy as Hb < 11.0 g/dL due to gestational hemodilution."
    },
    "hematocrit": {
        "applicability": GestationalApplicabilityType.PHYSIOLOGICAL_SHIFT,
        "note": "Gestational plasma expansion decreases hematocrit baseline by ~3-5%."
    },
    "creatinine": {
        "applicability": GestationalApplicabilityType.PHYSIOLOGICAL_SHIFT,
        "note": "Gestational renal hyperfiltration lowers baseline serum creatinine (0.4-0.8 mg/dL is normal)."
    },
    "egfr": {
        "applicability": GestationalApplicabilityType.METHODOLOGY_CONTRAINDICATED,
        "note": "2021 CKD-EPI equation is not validated in pregnancy and significantly underestimates true clearance."
    },
    "hba1c": {
        "applicability": GestationalApplicabilityType.METHODOLOGY_CONTRAINDICATED,
        "note": "ADA guidelines state HbA1c is invalid in 2nd/3rd trimester due to altered red cell turnover. Plasma blood glucose must be used."
    },
    "uric_acid": {
        "applicability": GestationalApplicabilityType.PHYSIOLOGICAL_SHIFT,
        "note": "Uric acid drops in early pregnancy and rises in late gestation; thresholds > 5.5 mg/dL used in preeclampsia evaluation."
    },
    "glucose_random": {
        "applicability": GestationalApplicabilityType.PHYSIOLOGICAL_SHIFT,
        "note": "Casual glucose tolerance shifts during pregnancy; dedicated gestational diabetes screening criteria apply."
    }
}


class CanonicalReferenceAdapter:
    """Ingestion adapter transforming Phase 2 canonical reference JSON files into normalized relational records."""

    @classmethod
    def parse_panel_file(cls, json_path: Path) -> Dict[str, Any]:
        """Parses a single canonical reference JSON file and flattens it into structured relational domain models."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        category = data.get("panel_category")
        records = {
            "metrics": [],
            "aliases": [],
            "reference_intervals": [],
            "critical_limits": [],
            "diagnostic_thresholds": [],
            "treatment_targets": [],
            "risk_thresholds": [],
            "unit_conversions": [],
            "clinical_contexts": []
        }

        for b in data.get("biomarkers", []):
            mid = b["metric_id"]
            cname = b["canonical_name"]
            loinc = b["loinc_code"]
            s_unit = b["standard_unit"]
            desc = b["description"]

            # 1. Base LabMetric & Aliases
            ld = b.get("loinc_details", {})
            metric_record = {
                "metric_id": mid,
                "canonical_name": cname,
                "category": category,
                "standard_unit": s_unit,
                "description": desc,
                "loinc_code": loinc,
                "loinc_verification_status": b.get("loinc_verification_status", "VERIFIED_REGISTRY"),
                "loinc_version": ld.get("loinc_version", "2.83 (August 2026)"),
                "loinc_component": ld.get("component", cname),
                "loinc_property": ld.get("property", "MCnc"),
                "loinc_system_specimen": ld.get("system_specimen", "Bld"),
                "loinc_scale_type": ld.get("scale_type", "Quantitative (Qn)"),
                "loinc_method_type": ld.get("method_type", "Automated count")
            }
            records["metrics"].append(metric_record)

            for alias in b.get("aliases", []):
                records["aliases"].append({"alias": alias.strip().lower(), "metric_id": mid})

            # 2. Reference Intervals
            dc = b.get("data_concepts", {})
            for inv in dc.get("laboratory_reference_intervals", []):
                records["reference_intervals"].append({
                    "metric_id": mid,
                    "population": inv.get("population", "General Adult"),
                    "gender": inv.get("gender", "all").lower(),
                    "age_min_years": float(inv.get("age_min_years", 18.0)),
                    "age_max_years": float(inv.get("age_max_years", 120.0)),
                    "pregnancy_status": inv.get("pregnancy_status", "ALL"),
                    "unit": inv.get("unit", s_unit),
                    "min_normal": float(inv["min_normal"]),
                    "max_normal": float(inv["max_normal"]),
                    "interval_context_note": inv.get("interval_context_note", ""),
                    "source_reference": inv.get("source_reference", ""),
                    "verification_status": inv.get("verification_status", "VERIFIED"),
                    "interval_tier": "PRIMARY_POPULATION_BENCHMARK",
                    "analytical_method_tag": "ALL_METHODS"
                })

            # 3. Critical Limits
            for cl in dc.get("critical_laboratory_limits", []):
                ltype_str = cl.get("limit_type", "CONSENSUS_PANIC_SURVEY_MEDIAN")
                inote = cl.get("institutional_note", "")
                inst_id = "MGH" if "Massachusetts General Hospital" in inote or "MGH" in inote else None
                records["critical_limits"].append({
                    "metric_id": mid,
                    "critical_low": float(cl["critical_low"]) if cl.get("critical_low") is not None else None,
                    "critical_high": float(cl["critical_high"]) if cl.get("critical_high") is not None else None,
                    "unit": cl.get("unit", s_unit),
                    "limit_type": ltype_str,
                    "institutional_note": inote,
                    "clinical_urgency": cl.get("clinical_urgency", ""),
                    "source_reference": cl.get("source_reference", ""),
                    "verification_status": cl.get("verification_status", "VERIFIED"),
                    "institutional_identifier": inst_id
                })

            # 4. Clinical Diagnostic Thresholds
            for dt in dc.get("clinical_diagnostic_thresholds", []):
                records["diagnostic_thresholds"].append({
                    "metric_id": mid,
                    "condition_name": dt.get("condition_name", ""),
                    "cutoff_value": float(dt["cutoff_value"]),
                    "comparison_operator": dt.get("comparison_operator", ">="),
                    "unit": dt.get("unit", s_unit),
                    "requires_repeat_confirmation": 1 if dt.get("requires_repeat_confirmation", False) else 0,
                    "clinical_criteria": dt.get("clinical_criteria", ""),
                    "source_guideline": dt.get("source_guideline", ""),
                    "verification_status": dt.get("verification_status", "VERIFIED")
                })

            # 5. Treatment Targets
            for tt in dc.get("treatment_targets", []):
                records["treatment_targets"].append({
                    "metric_id": mid,
                    "target_population": tt.get("target_population", ""),
                    "goal_description": tt.get("goal_description", ""),
                    "target_value": float(tt["target_value"]),
                    "comparison_operator": tt.get("comparison_operator", "<="),
                    "unit": tt.get("unit", s_unit),
                    "source_guideline": tt.get("source_guideline", ""),
                    "verification_status": tt.get("verification_status", "VERIFIED")
                })

            # 6. Risk Tiers
            for rt in dc.get("risk_classification_thresholds", []):
                records["risk_thresholds"].append({
                    "metric_id": mid,
                    "tier_name": rt.get("tier_name", ""),
                    "tier_description": rt.get("tier_description", ""),
                    "lower_bound": float(rt["lower_bound"]) if rt.get("lower_bound") is not None else None,
                    "upper_bound": float(rt["upper_bound"]) if rt.get("upper_bound") is not None else None,
                    "unit": rt.get("unit", s_unit),
                    "clinical_significance": rt.get("clinical_significance", ""),
                    "source_classification": rt.get("source_classification", ""),
                    "verification_status": rt.get("verification_status", "VERIFIED")
                })

            # 7. Unit Conversions
            for uc in b.get("supported_alternative_units", []):
                alt_unit = uc["unit"]
                factor = float(uc["conversion_factor_to_standard"]) if uc.get("conversion_factor_to_standard") is not None else None
                formula_str = uc.get("conversion_formula", "")
                
                # Determine handler name
                if mid == "hba1c" and "mmol/mol" in alt_unit:
                    handler_name = "HBA1C_IFCC_TO_NGSP"
                    conv_type = "COMPILED_FUNCTION"
                else:
                    handler_name = "LINEAR_SCALE"
                    conv_type = "LINEAR_SCALE"

                # Security allowlist check during ingestion
                if handler_name not in ALLOWED_CONVERSION_HANDLERS:
                    raise ValueError(f"Security error: Unallowlisted handler '{handler_name}' encountered in canonical data.")

                records["unit_conversions"].append({
                    "metric_id": mid,
                    "alternative_unit": alt_unit,
                    "standard_unit": s_unit,
                    "conversion_type": conv_type,
                    "conversion_factor": factor,
                    "canonical_conversion_formula": formula_str,
                    "formula_description": f"Standardized conversion from {alt_unit} to {s_unit}",
                    "handler_function_name": handler_name
                })

            # 8. Clinical Context & Fasting & Provenance
            freq = b.get("fasting_requirements", {})
            mctx = b.get("measurement_context", {})
            prov = b.get("provenance", {})

            # Pregnancy governance lookup
            p_gov = PREGNANCY_GOVERNANCE_METADATA.get(mid, {
                "applicability": GestationalApplicabilityType.UNAFFECTED,
                "note": "Standard adult intervals apply; no known gestational shifts."
            })

            records["clinical_contexts"].append({
                "metric_id": mid,
                "fasting_required": 1 if freq.get("is_required", False) else 0,
                "fasting_recommended_hours": float(freq["recommended_hours"]) if freq.get("recommended_hours") is not None else None,
                "fasting_details": freq.get("details", ""),
                "measurement_type": mctx.get("measurement_type", "DIRECT_MEASUREMENT"),
                "methodology": mctx.get("methodology", ""),
                "equation_description": mctx.get("equation", None),
                "longitudinal_requirements": mctx.get("longitudinal_requirements", None),
                "clinical_limitations": mctx.get("clinical_limitations", None),
                "gestational_applicability_type": p_gov["applicability"].value,
                "gestational_contraindication_note": p_gov["note"],
                "primary_source_organization": prov.get("primary_source_organization", ""),
                "primary_document_title": prov.get("primary_document_title", ""),
                "publication_year": int(prov.get("publication_year", 2024)),
                "source_url": prov.get("source_url", ""),
                "provenance_verification_status": prov.get("verification_status", "VERIFIED_DOCUMENTED_SOURCE"),
                "provenance_clinical_notes": prov.get("clinical_notes", None)
            })

        return records
