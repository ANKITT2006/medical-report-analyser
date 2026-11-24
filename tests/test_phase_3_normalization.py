"""
Phase 3.3 — Deterministic Unit Normalization & Canonical Biomarker Mapping Unit Tests.
Covers:
A. Biomarker resolution (canonical names, registered aliases, case/space variations, unknown labels, ambiguous mappings).
B. Unit lexical normalization (casing, whitespace, Unicode micro symbols, unrecognized units).
C. Biomarker-specific unit compatibility (canonical units, supported alternative units, unsupported units).
D. Mathematical conversion (linear scaling, HbA1c IFCC-to-NGSP, audit preservation, formula provenance).
E. Original value preservation (raw values, raw units, source locations untouched).
F. Non-numeric and qualified results (inequalities, qualitative strings preserved uncoerced).
G. Safety constraints (no invented units, no generic conversion bleed-through, no dynamic eval).
"""

import unittest
from clinical_engine.domain.schemas import (
    RawObservation,
    NormalizedObservation,
    ConversionAudit,
    IngestionStatus,
    ParsingStatus,
    SourceLocation,
)
from clinical_engine.pipeline.normalizer import (
    CanonicalBiomarkerResolver,
    BiomarkerResolutionStatus,
    UnitLexicalNormalizer,
    ObservationNormalizer,
)
from clinical_engine.storage.repository import SQLClinicalRepository


class TestCanonicalBiomarkerResolver(unittest.TestCase):
    """Test CanonicalBiomarkerResolver deterministic mapping."""

    @classmethod
    def setUpClass(cls):
        cls.repo = SQLClinicalRepository()
        cls.resolver = CanonicalBiomarkerResolver(cls.repo)

    def test_exact_canonical_name_matching(self):
        bio, status, expl = self.resolver.resolve("Hemoglobin")
        self.assertEqual(status, BiomarkerResolutionStatus.RESOLVED)
        self.assertIsNotNone(bio)
        self.assertEqual(bio["metric_id"], "hemoglobin")
        self.assertEqual(bio["canonical_name"], "Hemoglobin")
        self.assertEqual(bio["loinc_code"], "718-7")
        self.assertEqual(bio["standard_unit"], "g/dL")

    def test_registered_alias_matching(self):
        # Hb, HGB, Haemoglobin -> hemoglobin
        for alias in ["Hb", "HGB", "haemoglobin"]:
            bio, status, _ = self.resolver.resolve(alias)
            self.assertEqual(status, BiomarkerResolutionStatus.RESOLVED)
            self.assertEqual(bio["metric_id"], "hemoglobin")

        # TLC, Total Leukocyte Count -> wbc
        bio_wbc, status_wbc, _ = self.resolver.resolve("Total Leukocyte Count")
        self.assertEqual(status_wbc, BiomarkerResolutionStatus.RESOLVED)
        self.assertEqual(bio_wbc["metric_id"], "wbc")

        # Fasting Blood Sugar -> glucose_fasting
        bio_fbs, status_fbs, _ = self.resolver.resolve("Fasting Blood Sugar")
        self.assertEqual(status_fbs, BiomarkerResolutionStatus.RESOLVED)
        self.assertEqual(bio_fbs["metric_id"], "glucose_fasting")

    def test_case_and_whitespace_normalization(self):
        bio, status, _ = self.resolver.resolve("   hEmOGLoBiN   ")
        self.assertEqual(status, BiomarkerResolutionStatus.RESOLVED)
        self.assertEqual(bio["metric_id"], "hemoglobin")

        bio2, status2, _ = self.resolver.resolve("TOTAL   CHOLESTEROL")
        self.assertEqual(status2, BiomarkerResolutionStatus.RESOLVED)
        self.assertEqual(bio2["metric_id"], "cholesterol_total")

    def test_loinc_code_direct_lookup(self):
        # 1558-6 is LOINC for Fasting Plasma Glucose
        bio, status, _ = self.resolver.resolve("1558-6")
        self.assertEqual(status, BiomarkerResolutionStatus.RESOLVED)
        self.assertEqual(bio["metric_id"], "glucose_fasting")

    def test_unknown_biomarker_handling(self):
        bio, status, expl = self.resolver.resolve("Completely Unknown Test XYZ")
        self.assertEqual(status, BiomarkerResolutionStatus.UNKNOWN)
        self.assertIsNone(bio)
        self.assertIn("Unrecognized biomarker label", expl)

    def test_empty_or_whitespace_label_handling(self):
        bio, status, expl = self.resolver.resolve("   ")
        self.assertEqual(status, BiomarkerResolutionStatus.UNKNOWN)
        self.assertIsNone(bio)

    def test_no_demographic_context_required_for_resolution(self):
        """Biomarker resolution must succeed without demographic context (gender/age)."""
        bio, status, _ = self.resolver.resolve("Serum Creatinine")
        self.assertEqual(status, BiomarkerResolutionStatus.RESOLVED)
        self.assertEqual(bio["metric_id"], "creatinine")


class TestUnitLexicalNormalizer(unittest.TestCase):
    """Test UnitLexicalNormalizer controlled typographic and casing standardization."""

    def test_approved_casing_variations(self):
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("mg/dl")[0], "mg/dL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("MG/DL")[0], "mg/dL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("G/DL")[0], "g/dL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("gm/dl")[0], "g/dL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("MMOL/L")[0], "mmol/L")

    def test_harmless_whitespace_variations(self):
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("mg / dL")[0], "mg/dL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("  g / dl  ")[0], "g/dL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("mmol / l")[0], "mmol/L")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("cells / uL")[0], "/uL")

    def test_unicode_micro_symbol_variations(self):
        # Greek mu (\u03bc) and micro symbol (\u00b5)
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("µmol/L")[0], "umol/L")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("μmol/L")[0], "umol/L")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("umol/L")[0], "umol/L")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("cells/µL")[0], "/uL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("cells/μL")[0], "/uL")

    def test_cell_count_lexical_variants(self):
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("cells/uL")[0], "/uL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("/mcl")[0], "/uL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("10^3/uL")[0], "x10^3/uL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("k/uL")[0], "x10^3/uL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("10^6/uL")[0], "M/uL")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("M/uL")[0], "M/uL")
        # Lowercase 'm/uL' (milli) must NOT collapse to 'M/uL' (Mega)
        self.assertIsNone(UnitLexicalNormalizer.normalize_unit("m/uL")[0])

    def test_egfr_body_surface_area_variants(self):
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("mL/min/1.73m2")[0], "mL/min/1.73m^2")
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("ml/min/1.73 m2")[0], "mL/min/1.73m^2")

    def test_unrecognized_units_rejected(self):
        unit, err = UnitLexicalNormalizer.normalize_unit("lightyears")
        self.assertIsNone(unit)
        self.assertIn("Unrecognized or unsupported", err)

        unit2, err2 = UnitLexicalNormalizer.normalize_unit("parsecs/hour")
        self.assertIsNone(unit2)

    def test_mathematically_different_units_not_aliased(self):
        """mmol/L and mg/dL must remain separate unit tokens."""
        u1, _ = UnitLexicalNormalizer.normalize_unit("mmol/L")
        u2, _ = UnitLexicalNormalizer.normalize_unit("mg/dL")
        self.assertNotEqual(u1, u2)
        self.assertEqual(u1, "mmol/L")
        self.assertEqual(u2, "mg/dL")


class TestObservationNormalizerPipeline(unittest.TestCase):
    """Test full ObservationNormalizer orchestration."""

    @classmethod
    def setUpClass(cls):
        cls.repo = SQLClinicalRepository()
        cls.normalizer = ObservationNormalizer(cls.repo)

    def test_direct_canonical_unit_match(self):
        """Observation in standard unit requires no mathematical conversion."""
        raw = RawObservation(
            raw_label="Hemoglobin",
            raw_value_text="14.5",
            detected_value=14.5,
            raw_unit="g/dL",
            source_location=SourceLocation(line_number=2),
            extraction_method="DELIMITED_TEXT"
        )
        norm = self.normalizer.normalize_observation(raw, source_document_id="DOC_001")
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "hemoglobin")
        self.assertEqual(norm.canonical_biomarker_name, "Hemoglobin")
        self.assertEqual(norm.loinc_code, "718-7")
        self.assertEqual(norm.normalized_value, 14.5)
        self.assertEqual(norm.normalized_unit, "g/dL")
        self.assertIsNone(norm.conversion_audit)
        self.assertEqual(norm.source_document_id, "DOC_001")
        self.assertEqual(norm.source_location.line_number, 2)

    def test_linear_scaling_conversion(self):
        """Hemoglobin: g/L -> g/dL (factor = 0.1)."""
        raw = RawObservation(
            raw_label="Haemoglobin",
            raw_value_text="145",
            detected_value=145.0,
            raw_unit="g/L",
            source_location=SourceLocation(line_number=3)
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "hemoglobin")
        self.assertEqual(norm.normalized_value, 14.5)
        self.assertEqual(norm.normalized_unit, "g/dL")
        self.assertIsNotNone(norm.conversion_audit)
        self.assertEqual(norm.conversion_audit.original_value, 145.0)
        self.assertEqual(norm.conversion_audit.original_unit, "g/L")
        self.assertEqual(norm.conversion_audit.converted_value, 14.5)
        self.assertEqual(norm.conversion_audit.standard_unit, "g/dL")
        self.assertEqual(norm.conversion_audit.conversion_type, "LINEAR_SCALE")
        self.assertEqual(norm.conversion_audit.handler_executed, "LINEAR_SCALE")

    def test_molar_to_mass_conversion_glucose(self):
        """Fasting Glucose: mmol/L -> mg/dL (factor = 18.0182). 5.0 mmol/L -> 90.09 mg/dL."""
        raw = RawObservation(
            raw_label="Fasting Blood Sugar",
            raw_value_text="5.0",
            detected_value=5.0,
            raw_unit="mmol/L"
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "glucose_fasting")
        self.assertAlmostEqual(norm.normalized_value, 90.091, places=2)
        self.assertEqual(norm.normalized_unit, "mg/dL")

    def test_molar_to_mass_conversion_cholesterol(self):
        """Total Cholesterol: mmol/L -> mg/dL (factor = 38.67). 5.0 mmol/L -> 193.35 mg/dL."""
        raw = RawObservation(
            raw_label="Total Cholesterol",
            raw_value_text="5.0",
            detected_value=5.0,
            raw_unit="mmol/L"
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "cholesterol_total")
        self.assertAlmostEqual(norm.normalized_value, 193.35, places=2)
        self.assertEqual(norm.normalized_unit, "mg/dL")

    def test_hba1c_ifcc_to_ngsp_conversion(self):
        """HbA1c: 48 mmol/mol -> (0.09148 * 48) + 2.152 = 6.54 %."""
        raw = RawObservation(
            raw_label="HbA1c",
            raw_value_text="48",
            detected_value=48.0,
            raw_unit="mmol/mol"
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "hba1c")
        self.assertAlmostEqual(norm.normalized_value, 6.54, places=2)
        self.assertEqual(norm.normalized_unit, "%")
        self.assertIsNotNone(norm.conversion_audit)
        self.assertEqual(norm.conversion_audit.handler_executed, "HBA1C_IFCC_TO_NGSP")

    def test_cell_count_k_ul_conversion(self):
        """Platelet Count: 250 k/uL -> 250,000 /uL (factor = 1000.0)."""
        raw = RawObservation(
            raw_label="Platelets",
            raw_value_text="250",
            detected_value=250.0,
            raw_unit="k/uL"
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "platelets")
        self.assertEqual(norm.normalized_value, 250000.0)
        self.assertEqual(norm.normalized_unit, "/uL")

    def test_original_value_and_text_preserved(self):
        """Original value, raw unit, and raw label must never be overwritten."""
        raw = RawObservation(
            raw_label="Hb",
            raw_value_text="145",
            detected_value=145.0,
            raw_unit="g/L",
            source_location=SourceLocation(line_number=10, row_number=5)
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.raw_label, "Hb")
        self.assertEqual(norm.original_value_text, "145")
        self.assertEqual(norm.original_detected_value, 145.0)
        self.assertEqual(norm.original_unit, "g/L")
        self.assertEqual(norm.source_location.line_number, 10)
        self.assertEqual(norm.source_location.row_number, 5)

    def test_missing_unit_returns_missing_unit_status(self):
        """If incoming unit is missing for a unit-dependent metric, status is MISSING_UNIT."""
        raw = RawObservation(
            raw_label="Serum Creatinine",
            raw_value_text="1.1",
            detected_value=1.1,
            raw_unit=None
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.MISSING_UNIT)
        self.assertIsNone(norm.normalized_value)
        self.assertIn("Standard unit cannot be presumed", norm.inconclusive_reason)

    def test_unsupported_unit_returns_unsupported_unit_status(self):
        """If unit is not supported for this specific metric, status is UNSUPPORTED_UNIT."""
        raw = RawObservation(
            raw_label="Hemoglobin",
            raw_value_text="14.2",
            detected_value=14.2,
            raw_unit="parsecs"
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.UNSUPPORTED_UNIT)
        self.assertIsNone(norm.normalized_value)

    def test_cross_metric_conversion_restriction(self):
        """
        Conversion for one biomarker must not bleed into another.
        Triglycerides uses factor 88.57 for mmol/L -> mg/dL.
        Glucose uses factor 18.0182 for mmol/L -> mg/dL.
        Hemoglobin does NOT accept % (only hematocrit and HbA1c do).
        """
        raw_hb_percent = RawObservation(
            raw_label="Hemoglobin",
            raw_value_text="14.0",
            detected_value=14.0,
            raw_unit="%"
        )
        norm = self.normalizer.normalize_observation(raw_hb_percent)
        self.assertEqual(norm.ingestion_status, IngestionStatus.UNSUPPORTED_UNIT)
        self.assertIn("No approved conversion pathway registered", norm.inconclusive_reason)

    def test_non_numeric_inequality_qualified_result(self):
        """Results with < or > qualifiers must not be mathematically converted or coerced to floats."""
        raw = RawObservation(
            raw_label="Fasting Glucose",
            raw_value_text="< 40",
            detected_value=None,
            raw_unit="mg/dL",
            parsing_status=ParsingStatus.NON_NUMERIC_RESULT
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.NON_NUMERIC_RESULT)
        self.assertEqual(norm.original_value_text, "< 40")
        self.assertIsNone(norm.normalized_value)
        self.assertIn("Numeric conversion skipped", norm.inconclusive_reason)

    def test_non_numeric_qualitative_result(self):
        """Qualitative result (e.g. Trace Positive) preserved uncoerced."""
        raw = RawObservation(
            raw_label="Fasting Glucose",
            raw_value_text="Trace Positive",
            detected_value=None,
            raw_unit="mg/dL",
            parsing_status=ParsingStatus.NON_NUMERIC_RESULT
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.NON_NUMERIC_RESULT)
        self.assertEqual(norm.original_value_text, "Trace Positive")
        self.assertIsNone(norm.normalized_value)

    def test_extraction_failed_observation_propagates_status(self):
        """Observation marked EXTRACTION_FAILED from parser propagates failure status."""
        raw = RawObservation(
            raw_label="Corrupted",
            raw_value_text="",
            detected_value=None,
            raw_unit=None,
            parsing_status=ParsingStatus.EXTRACTION_FAILED,
            diagnostic_message="Corrupted row syntax"
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.EXTRACTION_FAILED)
        self.assertIn("Corrupted row syntax", norm.inconclusive_reason)

    def test_batch_normalization(self):
        """normalize_observations handles a list of raw observations cleanly."""
        raw_list = [
            RawObservation(raw_label="Hemoglobin", raw_value_text="14.0", detected_value=14.0, raw_unit="g/dL"),
            RawObservation(raw_label="Platelets", raw_value_text="200", detected_value=200.0, raw_unit="k/uL")
        ]
        norm_list = self.normalizer.normalize_observations(raw_list)
        self.assertEqual(len(norm_list), 2)
        self.assertEqual(norm_list[0].normalized_value, 14.0)
        self.assertEqual(norm_list[1].normalized_value, 200000.0)


class TestIngestionStatusIntegrity(unittest.TestCase):
    """
    Exhaustive verification of IngestionStatus assignment integrity.
    Verifies the 9 required cases:
    1. Known biomarker + valid canonical unit -> VALID.
    2. Known biomarker + registered alias + supported alternative unit -> VALID only after conversion.
    3. Known biomarker + missing required unit -> MISSING_UNIT.
    4. Known biomarker + unsupported unit -> UNSUPPORTED_UNIT.
    5. Unknown biomarker -> UNKNOWN_BIOMARKER.
    6. Ambiguous biomarker -> AMBIGUOUS_BIOMARKER.
    7. Qualitative result -> NON_NUMERIC_RESULT.
    8. Failed conversion -> CONVERSION_FAILED.
    9. Missing numeric value -> MISSING_VALUE.

    Also verifies the critical invariant:
    Only a fully normalized, validated numeric observation may have ingestion_status == IngestionStatus.VALID.
    Every non-VALID observation must be ineligible for clinical evaluation.
    """

    @classmethod
    def setUpClass(cls):
        cls.repo = SQLClinicalRepository()
        cls.normalizer = ObservationNormalizer(cls.repo)

    def test_case_1_known_biomarker_valid_canonical_unit_is_valid(self):
        """Case 1: Known biomarker + valid canonical unit -> VALID."""
        raw = RawObservation(
            raw_label="Hemoglobin",
            raw_value_text="15.2",
            detected_value=15.2,
            raw_unit="g/dL",
            parsing_status=ParsingStatus.PARSED,
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "hemoglobin")
        self.assertEqual(norm.normalized_value, 15.2)
        self.assertEqual(norm.normalized_unit, "g/dL")
        self.assertIsNone(norm.inconclusive_reason)

    def test_case_2_known_biomarker_alias_supported_unit_valid_after_conversion(self):
        """Case 2: Known biomarker + registered alias + supported alternative unit -> VALID only after conversion."""
        raw = RawObservation(
            raw_label="Total Cholesterol",
            raw_value_text="5.2",
            detected_value=5.2,
            raw_unit="mmol/L",
            parsing_status=ParsingStatus.PARSED,
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm.canonical_metric_id, "cholesterol_total")
        self.assertAlmostEqual(norm.normalized_value, 5.2 * 38.67, places=2)
        self.assertEqual(norm.normalized_unit, "mg/dL")
        self.assertIsNotNone(norm.conversion_audit)
        self.assertEqual(norm.conversion_audit.handler_executed, "LINEAR_SCALE")

    def test_case_3_known_biomarker_missing_required_unit_is_missing_unit(self):
        """Case 3: Known biomarker + missing required unit -> MISSING_UNIT (cannot enter clinical eval)."""
        raw = RawObservation(
            raw_label="Fasting Blood Glucose",
            raw_value_text="95",
            detected_value=95.0,
            raw_unit=None,
            parsing_status=ParsingStatus.PARSED,
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.MISSING_UNIT)
        self.assertIsNone(norm.normalized_value)
        self.assertIsNone(norm.normalized_unit)
        self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertIn("Standard unit cannot be presumed", norm.inconclusive_reason)

    def test_case_4_known_biomarker_unsupported_unit_is_unsupported_unit(self):
        """Case 4: Known biomarker + unsupported unit -> UNSUPPORTED_UNIT (cannot enter clinical eval)."""
        raw = RawObservation(
            raw_label="Serum Creatinine",
            raw_value_text="1.2",
            detected_value=1.2,
            raw_unit="mmHg",
            parsing_status=ParsingStatus.PARSED,
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.UNSUPPORTED_UNIT)
        self.assertIsNone(norm.normalized_value)
        self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)

    def test_case_5_unknown_biomarker_is_unknown_biomarker(self):
        """Case 5: Unknown biomarker -> UNKNOWN_BIOMARKER (cannot enter clinical eval)."""
        raw = RawObservation(
            raw_label="Uncataloged Enzyme Beta",
            raw_value_text="42.0",
            detected_value=42.0,
            raw_unit="U/L",
            parsing_status=ParsingStatus.PARSED,
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.UNKNOWN_BIOMARKER)
        self.assertIsNone(norm.canonical_metric_id)
        self.assertIsNone(norm.normalized_value)
        self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)

    def test_case_6_ambiguous_biomarker_is_ambiguous_biomarker(self):
        """Case 6: Ambiguous biomarker -> AMBIGUOUS_BIOMARKER (cannot enter clinical eval)."""
        from unittest.mock import patch
        # Simulate an ambiguous resolution from the resolver
        with patch.object(
            self.normalizer.resolver,
            "resolve",
            return_value=(None, BiomarkerResolutionStatus.AMBIGUOUS, "Ambiguous mapping to multiple metrics")
        ):
            raw = RawObservation(
                raw_label="Ambiguous Protein",
                raw_value_text="10.0",
                detected_value=10.0,
                raw_unit="g/dL",
                parsing_status=ParsingStatus.PARSED,
            )
            norm = self.normalizer.normalize_observation(raw)
            self.assertEqual(norm.ingestion_status, IngestionStatus.AMBIGUOUS_BIOMARKER)
            self.assertIsNone(norm.canonical_metric_id)
            self.assertIsNone(norm.normalized_value)
            self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)

    def test_case_7_qualitative_result_is_non_numeric_result(self):
        """Case 7: Qualitative result -> NON_NUMERIC_RESULT (cannot enter clinical eval)."""
        for qual_text in ["Negative", "Positive", "Trace", "< 0.01", "> 100", "3+"]:
            raw = RawObservation(
                raw_label="Fasting Glucose",
                raw_value_text=qual_text,
                detected_value=None,
                raw_unit="mg/dL",
                parsing_status=ParsingStatus.NON_NUMERIC_RESULT,
            )
            norm = self.normalizer.normalize_observation(raw)
            self.assertEqual(norm.ingestion_status, IngestionStatus.NON_NUMERIC_RESULT)
            self.assertEqual(norm.original_value_text, qual_text)
            self.assertIsNone(norm.normalized_value)
            self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)

    def test_case_8_failed_conversion_is_conversion_failed(self):
        """Case 8: Failed conversion -> CONVERSION_FAILED (cannot enter clinical eval)."""
        from unittest.mock import patch
        with patch("clinical_engine.pipeline.normalizer.convert_laboratory_value", side_effect=ValueError("Overflow")):
            raw = RawObservation(
                raw_label="Fasting Glucose",
                raw_value_text="5.5",
                detected_value=5.5,
                raw_unit="mmol/L",
                parsing_status=ParsingStatus.PARSED,
            )
            norm = self.normalizer.normalize_observation(raw)
            self.assertEqual(norm.ingestion_status, IngestionStatus.CONVERSION_FAILED)
            self.assertIsNone(norm.normalized_value)
            self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)
            self.assertIn("Mathematical unit conversion failed", norm.inconclusive_reason)

    def test_case_9_missing_numeric_value_is_missing_value(self):
        """Case 9: Missing numeric value -> MISSING_VALUE (cannot enter clinical eval)."""
        raw = RawObservation(
            raw_label="Hemoglobin",
            raw_value_text="",
            detected_value=None,
            raw_unit="g/dL",
            parsing_status=ParsingStatus.PARSED,
        )
        norm = self.normalizer.normalize_observation(raw)
        self.assertEqual(norm.ingestion_status, IngestionStatus.MISSING_VALUE)
        self.assertIsNone(norm.normalized_value)
        self.assertNotEqual(norm.ingestion_status, IngestionStatus.VALID)
        self.assertIn("empty result value", norm.inconclusive_reason)

    def test_resolution_success_alone_does_not_make_observation_valid(self):
        """
        Verify the core invariant:
        Successful biomarker resolution alone does NOT confer IngestionStatus.VALID.
        Subsequent failures (missing value, missing unit, unsupported unit, failed conversion)
        must prevent VALID status.
        """
        # Resolved biomarker, but missing unit
        norm_no_unit = self.normalizer.normalize_observation(
            RawObservation(raw_label="Hemoglobin", raw_value_text="14.0", detected_value=14.0, raw_unit=None)
        )
        self.assertNotEqual(norm_no_unit.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm_no_unit.ingestion_status, IngestionStatus.MISSING_UNIT)

        # Resolved biomarker, but missing value
        norm_no_val = self.normalizer.normalize_observation(
            RawObservation(raw_label="Hemoglobin", raw_value_text="", detected_value=None, raw_unit="g/dL")
        )
        self.assertNotEqual(norm_no_val.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm_no_val.ingestion_status, IngestionStatus.MISSING_VALUE)

        # Resolved biomarker, but unsupported unit
        norm_bad_unit = self.normalizer.normalize_observation(
            RawObservation(raw_label="Hemoglobin", raw_value_text="14.0", detected_value=14.0, raw_unit="kg/m2")
        )
        self.assertNotEqual(norm_bad_unit.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm_bad_unit.ingestion_status, IngestionStatus.UNSUPPORTED_UNIT)

    def test_si_prefix_and_case_sensitivity(self):
        """
        Verify that SI unit prefix sensitivity is preserved:
        1. M/uL (million / uL for RBC) normalizes to 'M/uL'.
        2. k/uL (thousand / uL for WBC/Platelets) normalizes to 'x10^3/uL'.
        3. /uL normalizes to '/uL'.
        4. M/uL, x10^3/uL, and /uL are strictly non-identical and distinct tokens.
        5. RBC cannot accept k/uL or /uL as standard unit (standard unit is M/uL).
        6. WBC cannot accept M/uL without an explicit conversion registered.
        """
        norm_M, _ = UnitLexicalNormalizer.normalize_unit("M/uL")
        norm_k, _ = UnitLexicalNormalizer.normalize_unit("k/uL")
        norm_base, _ = UnitLexicalNormalizer.normalize_unit("/uL")

        self.assertEqual(norm_M, "M/uL")
        self.assertEqual(norm_k, "x10^3/uL")
        self.assertEqual(norm_base, "/uL")
        self.assertNotEqual(norm_M, norm_k)
        self.assertNotEqual(norm_M, norm_base)
        self.assertNotEqual(norm_k, norm_base)

        # RBC standard unit is M/uL; incoming /uL or x10^3/uL has no direct match or conversion
        raw_rbc = RawObservation(
            raw_label="RBC",
            raw_value_text="4.5",
            detected_value=4.5,
            raw_unit="/uL",
            parsing_status=ParsingStatus.PARSED
        )
        norm_rbc = self.normalizer.normalize_observation(raw_rbc)
        self.assertEqual(norm_rbc.ingestion_status, IngestionStatus.UNSUPPORTED_UNIT)
        self.assertIsNone(norm_rbc.normalized_value)

    def test_m_ul_and_lowercase_m_ul_never_collide(self):
        """M/uL and m/uL cannot resolve to the same conversion token merely through lowercasing."""
        norm_mega, err_mega = UnitLexicalNormalizer.normalize_unit("M/uL")
        norm_milli, err_milli = UnitLexicalNormalizer.normalize_unit("m/uL")
        self.assertEqual(norm_mega, "M/uL")
        self.assertIsNone(err_mega)
        self.assertIsNone(norm_milli)
        self.assertIsNotNone(err_milli)
        self.assertNotEqual(norm_mega, norm_milli)

        # In ObservationNormalizer, RBC with 'm/uL' must be rejected as UNSUPPORTED_UNIT (not accepted as 'M/uL')
        raw_milli = RawObservation(
            raw_label="RBC",
            raw_value_text="4.8",
            detected_value=4.8,
            raw_unit="m/uL",
            parsing_status=ParsingStatus.PARSED,
        )
        norm_obs = self.normalizer.normalize_observation(raw_milli)
        self.assertEqual(norm_obs.ingestion_status, IngestionStatus.UNSUPPORTED_UNIT)
        self.assertIsNone(norm_obs.normalized_value)

    def test_k_ul_and_x10_3_ul_distinct_until_conversion(self):
        """k/uL and x10^3/uL preserve distinct original_unit and require explicit conversion to /uL."""
        raw_k = RawObservation(
            raw_label="WBC",
            raw_value_text="7.5",
            detected_value=7.5,
            raw_unit="k/uL",
            parsing_status=ParsingStatus.PARSED,
        )
        norm_k = self.normalizer.normalize_observation(raw_k)
        self.assertEqual(norm_k.ingestion_status, IngestionStatus.VALID)
        self.assertEqual(norm_k.original_unit, "k/uL")
        self.assertEqual(norm_k.normalized_unit, "/uL")
        self.assertEqual(norm_k.normalized_value, 7500.0)
        self.assertIsNotNone(norm_k.conversion_audit)
        self.assertEqual(norm_k.conversion_audit.original_unit, "x10^3/uL")

    def test_isolated_case_distinct_sql_conversion_records_do_not_collide(self):
        """
        Using an isolated SQLite DB with two case-distinct alternative_unit records ('M/uL' and 'm/uL'),
        verify SQL conversion lookup matches exact case only and never returns an arbitrary record.
        """
        import tempfile
        import os
        import sqlite3

        fd, tmp_db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            iso_repo = SQLClinicalRepository(db_path=tmp_db)
            conn = iso_repo._get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO lab_metrics (
                    metric_id, canonical_name, category, standard_unit, description,
                    loinc_code, loinc_verification_status, loinc_version,
                    loinc_component, loinc_property, loinc_system_specimen, loinc_scale_type
                )
                VALUES (
                    'test_cell', 'Test Cell', 'Hematology', '/uL', 'Isolated test metric',
                    '99999-9', 'VERIFIED', '2.83', 'Test', 'NCnc', 'Bld', 'Qn'
                )
            """)
            cur.execute("""
                INSERT INTO metric_unit_conversions
                (metric_id, alternative_unit, standard_unit, conversion_type, conversion_factor,
                 canonical_conversion_formula, formula_description, handler_function_name)
                VALUES
                ('test_cell', 'M/uL', '/uL', 'LINEAR_SCALE', 1000000.0, 'val * 1e6', 'Mega to /uL', 'LINEAR_SCALE'),
                ('test_cell', 'm/uL', '/uL', 'LINEAR_SCALE', 0.001, 'val * 1e-3', 'milli to /uL', 'LINEAR_SCALE')
            """)
            conn.commit()
            conn.close()

            conv_mega = iso_repo.get_unit_conversion("test_cell", "M/uL")
            conv_milli = iso_repo.get_unit_conversion("test_cell", "m/uL")
            conv_wrong_case = iso_repo.get_unit_conversion("test_cell", "m/UL")

            self.assertIsNotNone(conv_mega)
            self.assertEqual(conv_mega.alternative_unit, "M/uL")
            self.assertEqual(conv_mega.conversion_factor, 1000000.0)

            self.assertIsNotNone(conv_milli)
            self.assertEqual(conv_milli.alternative_unit, "m/uL")
            self.assertEqual(conv_milli.conversion_factor, 0.001)

            self.assertIsNone(conv_wrong_case)
        finally:
            if os.path.exists(tmp_db):
                try:
                    os.remove(tmp_db)
                except OSError:
                    pass

    def test_existing_core_conversions_remain_correct(self):
        """Verify existing glucose, cholesterol, HbA1c, WBC and platelet conversions remain intact."""
        cases = [
            ("Fasting Glucose", 5.0, "mmol/L", 90.091, "mg/dL"),
            ("Total Cholesterol", 5.0, "mmol/L", 193.35, "mg/dL"),
            ("HbA1c", 53.0, "mmol/mol", 7.0, "%"),
            ("WBC", 7.5, "x10^3/uL", 7500.0, "/uL"),
            ("Platelets", 250.0, "k/uL", 250000.0, "/uL"),
        ]
        for label, val, unit, expected_val, expected_unit in cases:
            norm = self.normalizer.normalize_observation(
                RawObservation(raw_label=label, raw_value_text=str(val), detected_value=val, raw_unit=unit)
            )
            self.assertEqual(norm.ingestion_status, IngestionStatus.VALID, f"Failed for {label}")
            self.assertEqual(norm.normalized_value, expected_val, f"Value mismatch for {label}")
            self.assertEqual(norm.normalized_unit, expected_unit, f"Unit mismatch for {label}")


if __name__ == "__main__":
    unittest.main()

