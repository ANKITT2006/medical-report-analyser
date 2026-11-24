"""
Phase 3.2 — Multi-Strategy Text & Tabular Extractors Unit Tests
Testing DelimitedTextStrategy, ColumnarTableStrategy, CSVTableStrategy, MultilinePairStrategy,
and CompositeReportExtractor with comprehensive boundary, edge case, and safety checks.
"""

import unittest
from clinical_engine.domain.schemas import (
    DocumentFormat,
    RawObservation,
    ExtractionDiagnostic,
    ExtractionResult,
    ExtractionStatus,
    ParsingStatus,
    SourceLocation,
)
from clinical_engine.pipeline.parser import (
    ClinicalReportParser,
    DelimitedTextStrategy,
    ColumnarTableStrategy,
    CSVTableStrategy,
    MultilinePairStrategy,
    CompositeReportExtractor,
    ParsedObservation,
)


class TestDelimitedTextStrategy(unittest.TestCase):
    """Test DelimitedTextStrategy across colon, equals, hyphen delimiters, numbers, and units."""

    def setUp(self):
        self.strategy = DelimitedTextStrategy()

    def test_standard_colon_delimited(self):
        text = "Hemoglobin: 13.5 g/dL\nWBC: 7500 /uL"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 2)
        
        self.assertEqual(obs[0].raw_label, "Hemoglobin")
        self.assertEqual(obs[0].raw_value_text, "13.5")
        self.assertEqual(obs[0].detected_value, 13.5)
        self.assertEqual(obs[0].raw_unit, "g/dL")
        self.assertEqual(obs[0].source_location.line_number, 1)
        self.assertEqual(obs[0].extraction_method, "DELIMITED_TEXT")
        self.assertEqual(obs[0].parsing_status, ParsingStatus.PARSED)

        self.assertEqual(obs[1].raw_label, "WBC")
        self.assertEqual(obs[1].raw_value_text, "7500")
        self.assertEqual(obs[1].detected_value, 7500.0)
        self.assertEqual(obs[1].raw_unit, "/uL")
        self.assertEqual(obs[1].source_location.line_number, 2)

    def test_equals_and_hyphen_delimiters(self):
        text = "Creatinine = 1.1 mg/dL\nPlatelets - 250000 cells/uL"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 2)

        self.assertEqual(obs[0].raw_label, "Creatinine")
        self.assertEqual(obs[0].detected_value, 1.1)
        self.assertEqual(obs[0].raw_unit, "mg/dL")

        self.assertEqual(obs[1].raw_label, "Platelets")
        self.assertEqual(obs[1].detected_value, 250000.0)
        self.assertEqual(obs[1].raw_unit, "cells/uL")

    def test_numbers_with_commas_and_decimals(self):
        text = "Total Count: 12,500.50 cells/mcL"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_value_text, "12,500.50")
        self.assertEqual(obs[0].detected_value, 12500.5)

    def test_missing_unit_preserves_none(self):
        text = "Anion Gap: 12"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Anion Gap")
        self.assertEqual(obs[0].detected_value, 12.0)
        self.assertIsNone(obs[0].raw_unit)

    def test_inequality_qualified_value_marked_non_numeric(self):
        text = "Troponin: <0.01 ng/mL\nCRP: >10.0 mg/L"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 2)
        
        self.assertEqual(obs[0].raw_label, "Troponin")
        self.assertEqual(obs[0].raw_value_text, "<0.01")
        self.assertIsNone(obs[0].detected_value)
        self.assertEqual(obs[0].raw_unit, "ng/mL")
        self.assertEqual(obs[0].parsing_status, ParsingStatus.NON_NUMERIC_RESULT)

        self.assertEqual(obs[1].raw_label, "CRP")
        self.assertEqual(obs[1].raw_value_text, ">10.0")
        self.assertIsNone(obs[1].detected_value)
        self.assertEqual(obs[1].parsing_status, ParsingStatus.NON_NUMERIC_RESULT)

    def test_qualitative_text_marked_non_numeric(self):
        text = "Ketones: Trace Positive"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Ketones")
        self.assertEqual(obs[0].raw_value_text, "Trace Positive")
        self.assertIsNone(obs[0].detected_value)
        self.assertEqual(obs[0].parsing_status, ParsingStatus.NON_NUMERIC_RESULT)

    def test_reference_range_guarded_and_ignored(self):
        text = "Hemoglobin: 14.2 g/dL (Ref: 12.0 - 16.0)\nGlucose: 95 mg/dL 70-99"
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].detected_value, 14.2)
        self.assertEqual(obs[0].raw_unit, "g/dL")
        self.assertEqual(obs[1].detected_value, 95.0)
        self.assertEqual(obs[1].raw_unit, "mg/dL")


class TestColumnarTableStrategy(unittest.TestCase):
    """Test ColumnarTableStrategy with whitespace/fixed-width tables and headers."""

    def setUp(self):
        self.strategy = ColumnarTableStrategy()

    def test_standard_columnar_table(self):
        table = """
        Test Name        Result    Unit      Reference Range
        Hemoglobin       14.1      g/dL      12.0 - 16.0
        Hematocrit       42.5      %         37.0 - 48.0
        Platelets        230       k/uL      150 - 400
        """
        obs = self.strategy.extract(table)
        self.assertEqual(len(obs), 3)

        self.assertEqual(obs[0].raw_label, "Hemoglobin")
        self.assertEqual(obs[0].detected_value, 14.1)
        self.assertEqual(obs[0].raw_unit, "g/dL")
        self.assertEqual(obs[0].extraction_method, "COLUMNAR_TABLE")

        self.assertEqual(obs[1].raw_label, "Hematocrit")
        self.assertEqual(obs[1].detected_value, 42.5)
        self.assertEqual(obs[1].raw_unit, "%")

        self.assertEqual(obs[2].raw_label, "Platelets")
        self.assertEqual(obs[2].detected_value, 230.0)
        self.assertEqual(obs[2].raw_unit, "k/uL")

    def test_table_without_unit_column(self):
        table = """
        Biomarker        Observed Value    Status
        Sodium           140               Normal
        Potassium        4.2               Normal
        """
        obs = self.strategy.extract(table)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].raw_label, "Sodium")
        self.assertEqual(obs[0].detected_value, 140.0)
        self.assertIsNone(obs[0].raw_unit)

        self.assertEqual(obs[1].raw_label, "Potassium")
        self.assertEqual(obs[1].detected_value, 4.2)
        self.assertIsNone(obs[1].raw_unit)

    def test_ambiguous_or_duplicate_headers_rejected_with_diagnostic(self):
        table = """
        Test Name        Result    Observed Value
        Glucose          95        100
        """
        res = self.strategy.extract_result(table)
        self.assertEqual(len(res.observations), 0)
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "AMBIGUOUS_RESULT_HEADER")
        self.assertIn("multiple result columns detected", res.diagnostics[0].diagnostic_message)
        self.assertIn("Cannot safely select result column", res.diagnostics[0].diagnostic_message)
        self.assertIsNotNone(res.diagnostics[0].source_location)

    def test_reference_range_not_extracted_as_result(self):
        table = """
        Analyte     Reference Range    Result    Units
        Calcium     8.5 - 10.2         9.4       mg/dL
        """
        obs = self.strategy.extract(table)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Calcium")
        self.assertEqual(obs[0].detected_value, 9.4)
        self.assertEqual(obs[0].raw_unit, "mg/dL")


class TestCSVTableStrategy(unittest.TestCase):
    """Test CSVTableStrategy across comma, semicolon, tab delimiters, quotes, and aliases."""

    def setUp(self):
        self.strategy = CSVTableStrategy()

    def test_standard_csv_comma(self):
        csv_text = (
            "test_name,result,unit,reference_interval\n"
            "Hemoglobin,13.8,g/dL,12.0-16.0\n"
            "White Blood Cell,6800,/uL,4000-11000\n"
        )
        obs = self.strategy.extract(csv_text)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].raw_label, "Hemoglobin")
        self.assertEqual(obs[0].detected_value, 13.8)
        self.assertEqual(obs[0].raw_unit, "g/dL")
        self.assertEqual(obs[0].source_location.line_number, 2)
        self.assertEqual(obs[0].extraction_method, "CSV_TABLE")

        self.assertEqual(obs[1].raw_label, "White Blood Cell")
        self.assertEqual(obs[1].detected_value, 6800.0)
        self.assertEqual(obs[1].raw_unit, "/uL")

    def test_semicolon_delimited_csv(self):
        csv_text = (
            "Parameter;Value;Unit\n"
            "Glucose;95;mg/dL\n"
            "BUN;18;mg/dL\n"
        )
        obs = self.strategy.extract(csv_text)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].raw_label, "Glucose")
        self.assertEqual(obs[0].detected_value, 95.0)
        self.assertEqual(obs[0].raw_unit, "mg/dL")

    def test_tsv_delimited_csv(self):
        tsv_text = (
            "Analyte\tTest Result\tUnits\n"
            "Creatinine\t1.05\tmg/dL\n"
        )
        obs = self.strategy.extract(tsv_text, delimiter="\t")
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Creatinine")
        self.assertEqual(obs[0].detected_value, 1.05)
        self.assertEqual(obs[0].raw_unit, "mg/dL")
        self.assertEqual(obs[0].extraction_method, "CSV_TABLE")

    def test_quoted_values_and_commas_in_fields(self):
        csv_text = (
            'test,result,unit\n'
            '"Thyroid Stimulating Hormone, 3rd Gen",2.45,uIU/mL\n'
            '"Total, Cholesterol",190,mg/dL\n'
        )
        obs = self.strategy.extract(csv_text)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].raw_label, "Thyroid Stimulating Hormone, 3rd Gen")
        self.assertEqual(obs[0].detected_value, 2.45)
        self.assertEqual(obs[0].raw_unit, "uIU/mL")
        self.assertEqual(obs[1].raw_label, "Total, Cholesterol")
        self.assertEqual(obs[1].detected_value, 190.0)

    def test_missing_result_column_returns_explicit_diagnostic(self):
        """CSV containing biomarker column but no valid result column must return structured diagnostic."""
        csv_text = "test,reference_range,flag\nGlucose,70-99,Normal\n"
        res = self.strategy.extract_result(csv_text)
        self.assertEqual(len(res.observations), 0)
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        diag = res.diagnostics[0]
        self.assertEqual(diag.diagnostic_code, "MISSING_RESULT_COLUMN")
        self.assertIn("missing required column", diag.diagnostic_message)
        self.assertIsNotNone(diag.source_location)
        self.assertEqual(diag.source_location.line_number, 1)
        self.assertIn("test", diag.raw_content)

    def test_missing_biomarker_header_returns_explicit_diagnostic(self):
        """CSV containing result column but missing biomarker column header."""
        csv_text = "result,unit\n95,mg/dL\n"
        res = self.strategy.extract_result(csv_text)
        self.assertEqual(len(res.observations), 0)
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "MISSING_BIOMARKER_HEADER")

    def test_duplicate_result_headers_rejected_with_diagnostic(self):
        csv_text = "test,result,observed value,unit\nGlucose,90,95,mg/dL\n"
        res = self.strategy.extract_result(csv_text)
        self.assertEqual(len(res.observations), 0)
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "AMBIGUOUS_RESULT_HEADER")
        self.assertIn("multiple result columns detected", res.diagnostics[0].diagnostic_message)
        self.assertIn("Cannot safely select result column", res.diagnostics[0].diagnostic_message)
        self.assertIsNotNone(res.diagnostics[0].source_location)

    def test_malformed_short_rows_retained_with_diagnostic(self):
        """Valid rows are preserved; malformed rows generate diagnostics without artificial observations."""
        csv_text = (
            "test,result,unit\n"
            "Glucose\n"  # only 1 column
            "Hemoglobin,14.0,g/dL\n"
        )
        res = self.strategy.extract_result(csv_text)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Hemoglobin")
        self.assertEqual(res.observations[0].detected_value, 14.0)
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "MALFORMED_CSV_ROW")
        self.assertIn("insufficient columns", res.diagnostics[0].diagnostic_message)
        self.assertEqual(res.diagnostics[0].raw_content, "Glucose")
        self.assertEqual(res.extraction_status, ExtractionStatus.PARTIAL_SUCCESS)

    def test_malformed_missing_biomarker_label(self):
        """Row with missing biomarker label yields a diagnostic, not an artificial RawObservation."""
        csv_text = (
            "test,result,unit\n"
            ",14.0,g/dL\n"
            "Glucose,95,mg/dL\n"
        )
        res = self.strategy.extract_result(csv_text)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Glucose")
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "MISSING_BIOMARKER_LABEL")
        self.assertIn("missing biomarker label", res.diagnostics[0].diagnostic_message)

    def test_malformed_missing_result_value(self):
        """Row with missing result value yields a diagnostic, not an artificial RawObservation."""
        csv_text = (
            "test,result,unit\n"
            "Albumin,,g/dL\n"
            "Glucose,95,mg/dL\n"
        )
        res = self.strategy.extract_result(csv_text)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Glucose")
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "MISSING_RESULT_VALUE")
        self.assertIn("empty result value", res.diagnostics[0].diagnostic_message)


class TestMultilinePairStrategy(unittest.TestCase):
    """Test MultilinePairStrategy for alternating label and value rows."""

    def setUp(self):
        self.strategy = MultilinePairStrategy()

    def test_valid_alternating_pairs(self):
        text = (
            "Total Cholesterol\n"
            "210 mg/dL\n"
            "Triglycerides\n"
            "150 mg/dL\n"
        )
        obs = self.strategy.extract(text)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].raw_label, "Total Cholesterol")
        self.assertEqual(obs[0].detected_value, 210.0)
        self.assertEqual(obs[0].raw_unit, "mg/dL")
        self.assertEqual(obs[0].source_location.line_number, 1)
        self.assertEqual(obs[0].extraction_method, "MULTILINE_PAIR")

        self.assertEqual(obs[1].raw_label, "Triglycerides")
        self.assertEqual(obs[1].detected_value, 150.0)
        self.assertEqual(obs[1].raw_unit, "mg/dL")

    def test_ambiguous_successive_numbers_rejected(self):
        text = (
            "Blood Glucose\n"
            "95 mg/dL\n"
            "110 mg/dL\n"
        )
        res = self.strategy.extract_result(text)
        self.assertEqual(len(res.observations), 0)
        self.assertEqual(len(res.diagnostics), 1)
        self.assertEqual(res.diagnostics[0].diagnostic_code, "AMBIGUOUS_MULTILINE_ASSOCIATION")


class TestCompositeReportExtractorAndSafety(unittest.TestCase):
    """Test CompositeReportExtractor integration, safety invariants, and backward compatibility."""

    def setUp(self):
        self.composite = CompositeReportExtractor()
        self.parser = ClinicalReportParser()

    def test_composite_csv_dispatch(self):
        csv_text = "test,result,unit\nHemoglobin,14.5,g/dL"
        obs = self.composite.extract_observations(csv_text, DocumentFormat.CSV)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Hemoglobin")
        self.assertEqual(obs[0].detected_value, 14.5)
        self.assertEqual(obs[0].extraction_method, "CSV_TABLE")

    def test_composite_tsv_dispatch(self):
        tsv_text = "test\tresult\tunit\nHemoglobin\t14.5\tg/dL"
        obs = self.composite.extract_observations(tsv_text, DocumentFormat.TSV)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Hemoglobin")
        self.assertEqual(obs[0].extraction_method, "CSV_TABLE")

    def test_composite_plain_text_dispatch_delimited_first(self):
        text = "Hemoglobin: 14.5 g/dL\nPlatelets: 200 k/uL"
        obs = self.composite.extract_observations(text, DocumentFormat.PLAIN_TEXT)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].extraction_method, "DELIMITED_TEXT")

    def test_composite_plain_text_dispatch_fallback_to_columnar(self):
        table = (
            "Test Name        Result    Unit\n"
            "Potassium        4.5       mmol/L\n"
            "Sodium           138       mmol/L\n"
        )
        obs = self.composite.extract_observations(table, DocumentFormat.PLAIN_TEXT)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0].extraction_method, "COLUMNAR_TABLE")

    def test_plain_text_not_misclassified_as_csv(self):
        """Ordinary prose with commas should not be misclassified as CSV."""
        text = "Hemoglobin: 14.2 g/dL\nNote: Patient is stable, alert, oriented"
        obs = self.composite.extract_observations(text, DocumentFormat.PLAIN_TEXT)
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].raw_label, "Hemoglobin")
        self.assertEqual(obs[0].extraction_method, "DELIMITED_TEXT")

    def test_no_double_extraction_on_overlapping_content(self):
        """Ensure input lines are extracted exactly once by the winning strategy."""
        text = "Hemoglobin: 14.2 g/dL\nGlucose: 95 mg/dL"
        obs = self.composite.extract_observations(text)
        self.assertEqual(len(obs), 2)
        self.assertEqual([o.raw_label for o in obs], ["Hemoglobin", "Glucose"])

    def test_backward_compatibility_parse_text(self):
        """ClinicalReportParser.parse_text must still return List[ParsedObservation]."""
        text = "Hemoglobin: 14.2 g/dL\nGlucose: 95 mg/dL"
        legacy_obs = self.parser.parse_text(text)
        self.assertIsInstance(legacy_obs, list)
        self.assertEqual(len(legacy_obs), 2)
        self.assertIsInstance(legacy_obs[0], ParsedObservation)
        self.assertEqual(legacy_obs[0].raw_key, "Hemoglobin")
        self.assertEqual(legacy_obs[0].detected_value, 14.2)
        self.assertEqual(legacy_obs[0].raw_unit, "g/dL")

    def test_extract_raw_observations_method(self):
        """ClinicalReportParser.extract_raw_observations returns List[RawObservation]."""
        text = "WBC: 7200 /uL"
        raw_obs = self.parser.extract_raw_observations(text)
        self.assertEqual(len(raw_obs), 1)
        self.assertIsInstance(raw_obs[0], RawObservation)
        self.assertEqual(raw_obs[0].raw_label, "WBC")
        self.assertEqual(raw_obs[0].detected_value, 7200.0)
        self.assertEqual(raw_obs[0].raw_unit, "/uL")

    def test_extract_report_method_returns_extraction_result(self):
        """ClinicalReportParser.extract_report returns strongly typed ExtractionResult."""
        text = "test,result,unit\nGlucose,95,mg/dL"
        res = self.parser.extract_report(text, DocumentFormat.CSV)
        self.assertIsInstance(res, ExtractionResult)
        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Glucose")
        self.assertEqual(len(res.diagnostics), 0)

    def test_safety_dates_and_patient_metadata_not_extracted_as_observations(self):
        text = (
            "Patient ID: 987654321\n"
            "Date of Birth: 1985-04-12\n"
            "Collection Date: 2026-11-20\n"
            "Report Status: Final\n"
            "Glucose: 92 mg/dL\n"
        )
        raw_obs = self.parser.extract_raw_observations(text)
        self.assertEqual(len(raw_obs), 1)
        self.assertEqual(raw_obs[0].raw_label, "Glucose")
        self.assertEqual(raw_obs[0].detected_value, 92.0)

    def test_empty_document_handling(self):
        """Empty string or whitespace-only document returns SUCCESS_EMPTY status."""
        res = self.composite.extract_result("")
        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS_EMPTY)
        self.assertEqual(len(res.observations), 0)
        self.assertEqual(len(res.diagnostics), 0)

        res_ws = self.composite.extract_result("   \n\n  \t  ")
        self.assertEqual(res_ws.extraction_status, ExtractionStatus.SUCCESS_EMPTY)
        self.assertEqual(len(res_ws.observations), 0)

    def test_no_extraction_diagnostic_appears_in_observations(self):
        """Verify that no ExtractionDiagnostic object or error surrogate ever appears in observations list."""
        csv_text = (
            "test,result,unit\n"
            "Glucose\n"  # short row
            ",14.0,g/dL\n"  # missing biomarker
            "Albumin,,g/dL\n"  # missing result
            "Hemoglobin,13.5,g/dL\n"  # valid
        )
        res = self.parser.extract_report(csv_text, DocumentFormat.CSV)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Hemoglobin")
        for obs in res.observations:
            self.assertIsInstance(obs, RawObservation)
            self.assertNotEqual(obs.raw_label, "AMBIGUOUS_CSV_HEADER")
            self.assertNotEqual(obs.raw_label, "AMBIGUOUS_TABLE_HEADER")
            self.assertNotEqual(obs.raw_label, "MISSING_BIOMARKER_LABEL")
            self.assertNotEqual(obs.raw_label, "MALFORMED_CSV_ROW")
        self.assertEqual(len(res.diagnostics), 3)

    def test_partial_extraction_with_valid_short_and_missing_result_rows(self):
        """
        Verify partial extraction on a CSV containing:
        - One valid laboratory observation (Hemoglobin).
        - One malformed short row (Glucose).
        - One row with missing result (Albumin).
        Expected:
        - Valid observation preserved in observations.
        - Malformed rows represented as ExtractionDiagnostic objects.
        - No diagnostic represented as RawObservation.
        - extraction_status = PARTIAL_SUCCESS.
        - Original row content and source locations preserved.
        """
        csv_text = (
            "test,result,unit\n"
            "Hemoglobin,14.2,g/dL\n"
            "Glucose\n"
            "Albumin,,g/dL\n"
        )
        res = self.parser.extract_report(csv_text, DocumentFormat.CSV)
        self.assertEqual(res.extraction_status, ExtractionStatus.PARTIAL_SUCCESS)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Hemoglobin")
        self.assertEqual(res.observations[0].detected_value, 14.2)
        self.assertEqual(res.observations[0].raw_unit, "g/dL")

        # Diagnostics: 2 malformed rows
        self.assertEqual(len(res.diagnostics), 2)
        diag_codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("MALFORMED_CSV_ROW", diag_codes)
        self.assertIn("MISSING_RESULT_VALUE", diag_codes)

        # Confirm no diagnostic in observations
        for obs in res.observations:
            self.assertNotEqual(obs.raw_label, "MALFORMED_CSV_ROW")
            self.assertNotEqual(obs.raw_label, "MISSING_RESULT_VALUE")

        # Provenance: short row
        short_diag = next(d for d in res.diagnostics if d.diagnostic_code == "MALFORMED_CSV_ROW")
        self.assertEqual(short_diag.raw_content, "Glucose")
        self.assertEqual(short_diag.source_location.line_number, 3)

        # Provenance: missing result row
        missing_val_diag = next(d for d in res.diagnostics if d.diagnostic_code == "MISSING_RESULT_VALUE")
        self.assertEqual(missing_val_diag.raw_content, "Albumin,,g/dL")
        self.assertEqual(missing_val_diag.source_location.line_number, 4)

    def test_extraction_result_cannot_silently_assume_success(self):
        """Verify that ExtractionResult requires explicit extraction_status and rejects uninitialized defaults."""
        with self.assertRaises(ValueError):
            # Missing extraction_status
            ExtractionResult()

    def test_extraction_result_invariants_enforced(self):
        """Verify invariant enforcement: PARTIAL_SUCCESS requires obs+diags, SUCCESS cannot have ERROR diags, etc."""
        # PARTIAL_SUCCESS with no observations -> ValueError
        with self.assertRaises(ValueError):
            ExtractionResult(
                extraction_status=ExtractionStatus.PARTIAL_SUCCESS,
                observations=[],
                diagnostics=[ExtractionDiagnostic(diagnostic_code="ERR", diagnostic_message="msg", severity="ERROR")]
            )

        # PARTIAL_SUCCESS with no diagnostics -> ValueError
        with self.assertRaises(ValueError):
            ExtractionResult(
                extraction_status=ExtractionStatus.PARTIAL_SUCCESS,
                observations=[RawObservation(raw_label="Hb", raw_value_text="14")],
                diagnostics=[]
            )

        # SUCCESS with ERROR diagnostics -> ValueError
        with self.assertRaises(ValueError):
            ExtractionResult(
                extraction_status=ExtractionStatus.SUCCESS,
                observations=[RawObservation(raw_label="Hb", raw_value_text="14")],
                diagnostics=[ExtractionDiagnostic(diagnostic_code="ERR", diagnostic_message="msg", severity="ERROR")]
            )

        # SUCCESS_EMPTY with observations -> ValueError
        with self.assertRaises(ValueError):
            ExtractionResult(
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                observations=[RawObservation(raw_label="Hb", raw_value_text="14")],
                diagnostics=[]
            )

    def test_extraction_diagnostic_and_result_serialization(self):
        """Verify ExtractionDiagnostic and ExtractionResult serialize cleanly via to_dict."""
        diag = ExtractionDiagnostic(
            diagnostic_code="TEST_CODE",
            diagnostic_message="Test message",
            severity="WARNING",
            source_location=SourceLocation(line_number=5, row_number=4),
            raw_content="Raw test line",
            strategy_name="CSV_TABLE"
        )
        d_dict = diag.to_dict()
        self.assertEqual(d_dict["diagnostic_code"], "TEST_CODE")
        self.assertEqual(d_dict["severity"], "WARNING")
        self.assertEqual(d_dict["source_location"]["line_number"], 5)

        res = ExtractionResult(
            observations=[
                RawObservation(
                    raw_label="Sodium",
                    raw_value_text="140",
                    detected_value=140.0,
                    raw_unit="mmol/L",
                    source_location=SourceLocation(line_number=2),
                    extraction_method="CSV_TABLE"
                )
            ],
            diagnostics=[diag],
            extraction_status=ExtractionStatus.PARTIAL_SUCCESS,
            detected_format=DocumentFormat.CSV
        )
        r_dict = res.to_dict()
        self.assertEqual(r_dict["extraction_status"], "PARTIAL_SUCCESS")
        self.assertEqual(r_dict["detected_format"], "CSV")
        self.assertEqual(len(r_dict["observations"]), 1)
        self.assertEqual(r_dict["observations"][0]["raw_label"], "Sodium")
        self.assertEqual(len(r_dict["diagnostics"]), 1)


if __name__ == "__main__":
    unittest.main()
