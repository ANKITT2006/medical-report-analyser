"""
Deterministic Unit Normalization & Canonical Biomarker Mapping Pipeline.
Phase 3.3 Implementation:
1. CanonicalBiomarkerResolver: maps RawObservation.raw_label -> canonical biomarker.
2. UnitLexicalNormalizer: controlled lexical normalization of typographic/casing/unicode unit variations.
3. ObservationNormalizer: orchestrates biomarker resolution, unit compatibility, mathematical conversion,
   and constructs strongly typed NormalizedObservation records preserving full audit provenance.
"""

import re
import unicodedata
from typing import Optional, List, Dict, Tuple, Any

from clinical_engine.domain.schemas import (
    RawObservation,
    NormalizedObservation,
    ConversionAudit,
    IngestionStatus,
    ParsingStatus,
)
from clinical_engine.pipeline.converters import (
    convert_laboratory_value,
    ALLOWED_CONVERSION_HANDLERS,
)
from clinical_engine.storage.repository import ClinicalRepository, SQLClinicalRepository


# =============================================================================
# 1. CANONICAL BIOMARKER RESOLVER
# =============================================================================

class CanonicalBiomarkerResolver:
    """
    Deterministic resolver that maps a raw biomarker label to its canonical entity.
    Queries the authoritative SQL repository (lab_metrics and metric_aliases).
    
    Rules:
    - Normalizes case and whitespace.
    - Strips leading/trailing punctuation/bullets.
    - Exactly one match -> returns canonical tuple.
    - Zero matches -> UNKNOWN_BIOMARKER.
    - Multiple distinct matches -> AMBIGUOUS_BIOMARKER.
    - Never uses fuzzy LLM matching or manufactures canonical IDs.
    - Does NOT require demographic context (gender/age) merely to identify a biomarker.
    """

    def __init__(self, repository: Optional[ClinicalRepository] = None):
        self.repository = repository or SQLClinicalRepository()

    def resolve(self, raw_label: str) -> Tuple[Optional[Dict[str, Any]], IngestionStatus, Optional[str]]:
        """
        Resolves raw_label into:
        (canonical_metric_dict, ingestion_status, explanation)
        canonical_metric_dict contains: metric_id, canonical_name, loinc_code, standard_unit, category.
        """
        if not raw_label or not raw_label.strip():
            return None, IngestionStatus.UNKNOWN_BIOMARKER, "Empty or missing biomarker label."

        cleaned = raw_label.strip()
        # Clean leading bullets, dashes, or numbered lists (e.g. "1. Hemoglobin" or "- Glucose")
        # Ensure we do not strip LOINC codes like "1558-6"
        if not re.match(r"^\d+-\d+$", cleaned):
            cleaned = re.sub(r"^[\*\-\•\s]+", "", cleaned)
            cleaned = re.sub(r"^\d+\.\s*", "", cleaned).strip()
        # Clean trailing colons, asterisks
        cleaned = re.sub(r"[\*:]+$", "", cleaned).strip()
        # Collapse multiple internal spaces
        normalized_query = re.sub(r"\s+", " ", cleaned).lower()

        if not normalized_query:
            return None, IngestionStatus.UNKNOWN_BIOMARKER, "Biomarker label contains no searchable characters."

        # Query database directly using connection
        conn = getattr(self.repository, "_get_connection")()
        try:
            cursor = conn.cursor()

            # 1. Check exact match on metric_id, canonical_name, or LOINC code
            cursor.execute("""
                SELECT metric_id, canonical_name, standard_unit, loinc_code, category
                FROM lab_metrics
                WHERE LOWER(metric_id) = ? OR LOWER(canonical_name) = ? OR LOWER(loinc_code) = ?
            """, (normalized_query, normalized_query, normalized_query))
            direct_matches = [dict(r) for r in cursor.fetchall()]

            # 2. Check match in metric_aliases
            cursor.execute("""
                SELECT m.metric_id, m.canonical_name, m.standard_unit, m.loinc_code, m.category
                FROM metric_aliases a
                JOIN lab_metrics m ON a.metric_id = m.metric_id
                WHERE LOWER(a.alias) = ?
            """, (normalized_query,))
            alias_matches = [dict(r) for r in cursor.fetchall()]

            # Combine matches deduplicated by metric_id
            combined: Dict[str, Dict[str, Any]] = {}
            for m in direct_matches + alias_matches:
                combined[m["metric_id"]] = m

            matched_list = list(combined.values())

            if len(matched_list) == 1:
                return matched_list[0], IngestionStatus.VALID, None

            if len(matched_list) > 1:
                candidate_ids = [m["metric_id"] for m in matched_list]
                return (
                    None,
                    IngestionStatus.AMBIGUOUS_BIOMARKER,
                    f"Ambiguous biomarker label '{raw_label}': maps to multiple canonical metrics ({', '.join(candidate_ids)})."
                )

            # Zero matches
            return None, IngestionStatus.UNKNOWN_BIOMARKER, f"Unrecognized biomarker label: '{raw_label}'."

        finally:
            conn.close()


# =============================================================================
# 2. UNIT LEXICAL NORMALIZER
# =============================================================================

class UnitLexicalNormalizer:
    """
    Controlled lexical normalizer for laboratory units.
    Standardizes harmless typographic, casing, and Unicode symbol variations
    (e.g., 'µmol/L' vs 'umol/L', 'mg / dL' vs 'mg/dL', 'cells/uL' vs '/uL')
    into approved canonical unit tokens.
    
    CRITICAL:
    - Does NOT treat mathematically different units as lexical aliases (e.g. mmol/L vs mg/dL).
    - Unrecognized units return None (caller flags UNSUPPORTED_UNIT).
    - Ambiguous aliases return None with explicit ambiguity flag.
    """

    # Controlled mapping: lowercase stripped normalized form -> canonical unit string
    CONTROLLED_UNIT_MAP: Dict[str, str] = {
        # Mass per volume
        "g/dl": "g/dL",
        "gm/dl": "g/dL",
        "g / dl": "g/dL",
        "gm / dl": "g/dL",
        "grams/dl": "g/dL",

        "mg/dl": "mg/dL",
        "mg / dl": "mg/dL",
        "milligram/dl": "mg/dL",
        "milligrams/dl": "mg/dL",

        "g/l": "g/L",
        "gm/l": "g/L",
        "g / l": "g/L",

        "mg/l": "mg/L",
        "mg / l": "mg/L",

        "ug/dl": "ug/dL",
        "µg/dl": "ug/dL",
        "μg/dl": "ug/dL",
        "ug / dl": "ug/dL",
        "mcg/dl": "ug/dL",

        "ng/ml": "ng/mL",
        "ng / ml": "ng/mL",

        "pg/ml": "pg/mL",
        "pg / ml": "pg/mL",

        # Molar concentrations
        "mmol/l": "mmol/L",
        "mmol / l": "mmol/L",
        "millimol/l": "mmol/L",

        "umol/l": "umol/L",
        "µmol/l": "umol/L",
        "μmol/l": "umol/L",
        "umol / l": "umol/L",
        "µmol / l": "umol/L",
        "micromol/l": "umol/L",

        "mmol/mol": "mmol/mol",
        "mmol / mol": "mmol/mol",

        # Cell counts and volumes
        "/ul": "/uL",
        "/ ul": "/uL",
        "/mcl": "/uL",
        "/ mcl": "/uL",
        "/µl": "/uL",
        "/μl": "/uL",
        "cells/ul": "/uL",
        "cells / ul": "/uL",
        "cells/mcl": "/uL",
        "cells/µl": "/uL",
        "cells/μl": "/uL",
        "per microliter": "/uL",

        "m/ul": "M/uL",
        "m / ul": "M/uL",
        "m/mcl": "M/uL",
        "m/µl": "M/uL",
        "m/μl": "M/uL",
        "mil/ul": "M/uL",
        "million/ul": "M/uL",
        "10^6/ul": "M/uL",
        "10^6/mcl": "M/uL",
        "10^6/µl": "M/uL",
        "x10^12/l": "x10^12/L",
        "10^12/l": "x10^12/L",
        "x10*12/l": "x10^12/L",

        "k/ul": "x10^3/uL",
        "k / ul": "x10^3/uL",
        "10^3/ul": "x10^3/uL",
        "10^3/mcl": "x10^3/uL",
        "10^3/µl": "x10^3/uL",
        "x10^3/ul": "x10^3/uL",
        "x10*3/ul": "x10^3/uL",
        "thousand/ul": "x10^3/uL",

        "x10^9/l": "x10^9/L",
        "10^9/l": "x10^9/L",
        "x10*9/l": "x10^9/L",

        # Volumes & weights
        "fl": "fL",
        "femtoliter": "fL",
        "femtoliters": "fL",

        "pg": "pg",
        "picogram": "pg",
        "picograms": "pg",

        # Percentages and ratios
        "%": "%",
        "percent": "%",
        "percentage": "%",
        "l/l": "L/L",

        # Filtration rates
        "ml/min": "mL/min",
        "ml / min": "mL/min",
        "ml/min/1.73m^2": "mL/min/1.73m^2",
        "ml/min/1.73m2": "mL/min/1.73m^2",
        "ml/min/1.73 m2": "mL/min/1.73m^2",
        "ml / min / 1.73 m2": "mL/min/1.73m^2",
        "ml/min/1.73sqm": "mL/min/1.73m^2",
    }

    @classmethod
    def normalize_unit(cls, raw_unit: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalizes raw unit string.
        Returns (normalized_unit_token, error_message).
        If raw_unit is None or empty, returns (None, None).
        If unit is unrecognized, returns (None, error_message).
        """
        if raw_unit is None:
            return None, None

        cleaned = raw_unit.strip()
        if not cleaned:
            return None, None

        # Unicode NFKC normalization (turns various micro symbols like \u03bc and \u00b5 into standard forms)
        norm_text = unicodedata.normalize("NFKC", cleaned)
        # Collapse internal spaces
        norm_text = re.sub(r"\s+", " ", norm_text).strip()
        lower_key = norm_text.lower()

        # Direct map check
        if lower_key in cls.CONTROLLED_UNIT_MAP:
            return cls.CONTROLLED_UNIT_MAP[lower_key], None

        # Try removing spaces around slashes
        collapsed_slash = re.sub(r"\s*/\s*", "/", lower_key)
        if collapsed_slash in cls.CONTROLLED_UNIT_MAP:
            return cls.CONTROLLED_UNIT_MAP[collapsed_slash], None

        # Unrecognized unit
        return None, f"Unrecognized or unsupported unit representation: '{raw_unit}'."


# =============================================================================
# 3. DETERMINISTIC OBSERVATION NORMALIZER
# =============================================================================

class ObservationNormalizer:
    """
    Main orchestration service for Phase 3.3.
    Transforms RawObservation -> NormalizedObservation.
    
    Enforces:
    1. Canonical biomarker resolution (via CanonicalBiomarkerResolver).
    2. Unit lexical normalization (via UnitLexicalNormalizer).
    3. Metric-specific unit compatibility validation against database registry.
    4. Approved mathematical unit conversion (via converters.convert_laboratory_value).
    5. Complete preservation of original values, text, and source locations.
    6. Non-numeric / qualified values remain uncoerced.
    """

    def __init__(self, repository: Optional[ClinicalRepository] = None):
        self.repository = repository or SQLClinicalRepository()
        self.resolver = CanonicalBiomarkerResolver(self.repository)

    def normalize_observation(
        self,
        raw_obs: RawObservation,
        source_document_id: Optional[str] = None
    ) -> NormalizedObservation:
        """Normalizes a single RawObservation into a strongly typed NormalizedObservation."""
        validation_messages: List[str] = []

        # 1. Initialize base NormalizedObservation with verbatim original data
        normalized = NormalizedObservation(
            raw_label=raw_obs.raw_label,
            original_value_text=raw_obs.raw_value_text,
            original_detected_value=raw_obs.detected_value,
            original_unit=raw_obs.raw_unit,
            source_document_id=source_document_id,
            source_location=raw_obs.source_location,
            ingestion_status=IngestionStatus.INCONCLUSIVE,
            validation_messages=[],
            inconclusive_reason=None
        )

        # 2. Check for parser extraction failure from Phase 3.2
        if raw_obs.parsing_status == ParsingStatus.EXTRACTION_FAILED:
            normalized.ingestion_status = IngestionStatus.EXTRACTION_FAILED
            msg = raw_obs.diagnostic_message or f"Extraction failed for label '{raw_obs.raw_label}'."
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        # 3. Resolve canonical biomarker identity
        bio_dict, bio_status, bio_expl = self.resolver.resolve(raw_obs.raw_label)
        if bio_status != IngestionStatus.VALID or bio_dict is None:
            normalized.ingestion_status = bio_status
            msg = bio_expl or f"Biomarker resolution status: {bio_status.value}."
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        # Biomarker conclusively resolved!
        normalized.canonical_metric_id = bio_dict["metric_id"]
        normalized.canonical_biomarker_name = bio_dict["canonical_name"]
        normalized.loinc_code = bio_dict["loinc_code"]
        standard_unit = bio_dict["standard_unit"]

        # 4. Handle Non-Numeric or Inequality-Qualified Results
        if (
            raw_obs.parsing_status == ParsingStatus.NON_NUMERIC_RESULT
            or raw_obs.detected_value is None
        ):
            # Guard: check if raw_value_text is empty
            if not raw_obs.raw_value_text or not raw_obs.raw_value_text.strip():
                normalized.ingestion_status = IngestionStatus.MISSING_VALUE
                msg = f"Biomarker '{normalized.canonical_biomarker_name}' has empty result value."
                normalized.validation_messages.append(msg)
                normalized.inconclusive_reason = msg
                return normalized

            # Non-numeric qualitative or inequality-qualified (e.g. "< 0.01", "Trace Positive", "Negative")
            normalized.ingestion_status = IngestionStatus.NON_NUMERIC_RESULT
            msg = (
                f"Biomarker '{normalized.canonical_biomarker_name}' has non-numeric result "
                f"'{raw_obs.raw_value_text}'. Numeric conversion skipped."
            )
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        # 5. Handle Missing Unit
        if raw_obs.raw_unit is None or not raw_obs.raw_unit.strip():
            # Check if this metric is inherently unitless (e.g., standard_unit is empty or 'ratio')
            if standard_unit in ("", "ratio"):
                # Unitless metric: valid without unit
                normalized.normalized_value = raw_obs.detected_value
                normalized.normalized_unit = standard_unit
                normalized.ingestion_status = IngestionStatus.VALID
                return normalized

            # Missing unit for a metric requiring a unit: do not assume canonical unit
            normalized.ingestion_status = IngestionStatus.MISSING_UNIT
            msg = (
                f"Biomarker '{normalized.canonical_biomarker_name}' requires unit '{standard_unit}', "
                f"but incoming unit is missing. Standard unit cannot be presumed."
            )
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        # 6. Lexically normalize incoming unit
        norm_incoming_unit, unit_err = UnitLexicalNormalizer.normalize_unit(raw_obs.raw_unit)
        if norm_incoming_unit is None:
            normalized.ingestion_status = IngestionStatus.UNSUPPORTED_UNIT
            msg = unit_err or f"Unsupported or unrecognized unit: '{raw_obs.raw_unit}'."
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        # 7. Check if incoming unit is already the standard unit (case-insensitive check against canonical standard unit)
        if norm_incoming_unit.strip().lower() == standard_unit.strip().lower():
            normalized.normalized_value = raw_obs.detected_value
            normalized.normalized_unit = standard_unit  # Assign canonical standard unit casing
            normalized.ingestion_status = IngestionStatus.VALID
            return normalized

        # 8. Check Metric-Specific Unit Compatibility in Database Registry
        conn = getattr(self.repository, "_get_connection")()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT conversion_id, alternative_unit, standard_unit, conversion_type,
                       conversion_factor, canonical_conversion_formula, handler_function_name
                FROM metric_unit_conversions
                WHERE metric_id = ? AND LOWER(alternative_unit) = ?
            """, (normalized.canonical_metric_id, norm_incoming_unit.lower()))
            conv_row = cursor.fetchone()
        finally:
            conn.close()

        if not conv_row:
            # No registered conversion for this metric + unit pair
            normalized.ingestion_status = IngestionStatus.UNSUPPORTED_UNIT
            msg = (
                f"Unit '{norm_incoming_unit}' (from raw '{raw_obs.raw_unit}') is not supported "
                f"for biomarker '{normalized.canonical_biomarker_name}' (standard unit: '{standard_unit}'). "
                f"No approved conversion pathway registered."
            )
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        # 9. Execute Approved Mathematical Unit Conversion
        handler_name = conv_row["handler_function_name"]
        factor = conv_row["conversion_factor"]
        formula_str = conv_row["canonical_conversion_formula"]
        conversion_type = conv_row["conversion_type"]

        if handler_name not in ALLOWED_CONVERSION_HANDLERS:
            normalized.ingestion_status = IngestionStatus.CONVERSION_FAILED
            msg = f"Unauthorized conversion handler '{handler_name}' rejected by security allowlist."
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

        try:
            conv_result = convert_laboratory_value(
                detected_value=raw_obs.detected_value,
                incoming_unit=norm_incoming_unit,
                standard_unit=standard_unit,
                conversion_type=conversion_type,
                handler_name=handler_name,
                factor=factor,
                formula_str=formula_str
            )
            normalized.normalized_value = conv_result["converted_value"]
            normalized.normalized_unit = standard_unit

            # Populate strongly typed ConversionAudit
            audit_data = conv_result.get("audit")
            if audit_data:
                normalized.conversion_audit = ConversionAudit(**audit_data)

            normalized.ingestion_status = IngestionStatus.VALID
            return normalized

        except Exception as e:
            normalized.ingestion_status = IngestionStatus.CONVERSION_FAILED
            msg = f"Mathematical unit conversion failed for '{raw_obs.raw_label}': {str(e)}"
            normalized.validation_messages.append(msg)
            normalized.inconclusive_reason = msg
            return normalized

    def normalize_observations(
        self,
        raw_observations: List[RawObservation],
        source_document_id: Optional[str] = None
    ) -> List[NormalizedObservation]:
        """Normalizes a list of RawObservation records."""
        return [self.normalize_observation(raw_obs, source_document_id) for raw_obs in raw_observations]

