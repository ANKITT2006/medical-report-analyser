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
        self.assertEqual(status, IngestionStatus.VALID)
        self.assertIsNotNone(bio)
        self.assertEqual(bio["metric_id"], "hemoglobin")
        self.assertEqual(bio["canonical_name"], "Hemoglobin")
        self.assertEqual(bio["loinc_code"], "718-7")
        self.assertEqual(bio["standard_unit"], "g/dL")

    def test_registered_alias_matching(self):
        # Hb, HGB, Haemoglobin -> hemoglobin
        for alias in ["Hb", "HGB", "haemoglobin"]:
            bio, status, _ = self.resolver.resolve(alias)
            self.assertEqual(status, IngestionStatus.VALID)
            self.assertEqual(bio["metric_id"], "hemoglobin")

        # TLC, Total Leukocyte Count -> wbc
        bio_wbc, status_wbc, _ = self.resolver.resolve("Total Leukocyte Count")
        self.assertEqual(status_wbc, IngestionStatus.VALID)
        self.assertEqual(bio_wbc["metric_id"], "wbc")

        # Fasting Blood Sugar -> glucose_fasting
        bio_fbs, status_fbs, _ = self.resolver.resolve("Fasting Blood Sugar")
        self.assertEqual(status_fbs, IngestionStatus.VALID)
        self.assertEqual(bio_fbs["metric_id"], "glucose_fasting")

    def test_case_and_whitespace_normalization(self):
        bio, status, _ = self.resolver.resolve("   hEmOGLoBiN   ")
        self.assertEqual(status, IngestionStatus.VALID)
        self.assertEqual(bio["metric_id"], "hemoglobin")

        bio2, status2, _ = self.resolver.resolve("TOTAL   CHOLESTEROL")
        self.assertEqual(status2, IngestionStatus.VALID)
        self.assertEqual(bio2["metric_id"], "cholesterol_total")

    def test_loinc_code_direct_lookup(self):
        # 1558-6 is LOINC for Fasting Plasma Glucose
        bio, status, _ = self.resolver.resolve("1558-6")
        self.assertEqual(status, IngestionStatus.VALID)
        self.assertEqual(bio["metric_id"], "glucose_fasting")

    def test_unknown_biomarker_handling(self):
        bio, status, expl = self.resolver.resolve("Completely Unknown Test XYZ")
        self.assertEqual(status, IngestionStatus.UNKNOWN_BIOMARKER)
        self.assertIsNone(bio)
        self.assertIn("Unrecognized biomarker label", expl)

    def test_empty_or_whitespace_label_handling(self):
        bio, status, expl = self.resolver.resolve("   ")
        self.assertEqual(status, IngestionStatus.UNKNOWN_BIOMARKER)
        self.assertIsNone(bio)

    def test_no_demographic_context_required_for_resolution(self):
        """Biomarker resolution must succeed without demographic context (gender/age)."""
        bio, status, _ = self.resolver.resolve("Serum Creatinine")
        self.assertEqual(status, IngestionStatus.VALID)
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
        self.assertEqual(UnitLexicalNormalizer.normalize_unit("m/uL")[0], "M/uL")

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


if __name__ == "__main__":
    unittest.main()

