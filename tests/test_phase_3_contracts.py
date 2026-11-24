"""
Phase 3.1 Unit Test Suite — Ingestion Domain Contracts & Schemas.

Comprehensive testing of:
1. RawDocumentInput format safety (TEXT_INPUT defaults to PLAIN_TEXT, FILE_UPLOAD defaults to UNDETECTED).
2. Uncoupling of MIME types and extensions from document format.
3. SourceLocation coordinate validations (positive 1-based indexing, non-negative offsets, end >= start).
4. RawObservation extraction confidence validation (0.0 to 1.0, None allowed, invalid rejected).
5. NormalizedObservation preservation of verbatim raw values and strongly typed ConversionAudit.
6. Structured status enums (DocumentFormat, InputSourceType, ParsingStatus, IngestionStatus).
7. Invalid enum value rejection.
8. JSON round-trip serialization and dictionary conversion.
"""

import json
import unittest
from clinical_engine.domain.schemas import (
    InputSourceType,
    DocumentFormat,
    DocumentProcessingStatus,
    ParsingStatus,
    IngestionStatus,
    ConversionAudit,
    RawDocumentInput,
    SourceLocation,
    RawObservation,
    NormalizedObservation,
)


class TestPhase3Contracts(unittest.TestCase):
    """Verifies type safety, coordinate validation, confidence boundaries, and conversion provenance."""

    # =========================================================================
    # 1. RAW DOCUMENT INPUT & FORMAT SAFETY TESTS
    # =========================================================================

    def test_raw_document_input_text_defaults_to_plain_text(self):
        """Direct text input defaults document_format to PLAIN_TEXT."""
        doc = RawDocumentInput(raw_content="Hemoglobin: 14.2 g/dL")
        self.assertEqual(doc.raw_content, "Hemoglobin: 14.2 g/dL")
        self.assertEqual(doc.input_source, InputSourceType.TEXT_INPUT)
        self.assertEqual(doc.document_format, DocumentFormat.PLAIN_TEXT)
        self.assertIsNone(doc.original_filename)
        self.assertIsNone(doc.document_id)
        self.assertEqual(doc.file_metadata, {})

    def test_raw_document_input_file_upload_remains_undetected(self):
        """
        Clinical safety rule: An uploaded file cannot silently be treated as PLAIN_TEXT
        prior to inspection. It must remain UNDETECTED regardless of filename extension or declared MIME type.
        """
        doc = RawDocumentInput(
            raw_content=b"%PDF-1.4...",
            original_filename="lab_report_2026.pdf",
            declared_mime_type="application/pdf",
            detected_extension=".pdf",
            input_source=InputSourceType.FILE_UPLOAD,
            document_id="DOC-98234",
            file_metadata={"file_size_bytes": 10240, "sha256": "abc123hash"}
            # Notice document_format is omitted
        )
        self.assertEqual(doc.document_id, "DOC-98234")
        self.assertEqual(doc.input_source, InputSourceType.FILE_UPLOAD)
        # Format must remain UNDETECTED; filename extension and declared MIME are NOT proof of content
        self.assertEqual(doc.document_format, DocumentFormat.UNDETECTED)
        self.assertEqual(doc.file_metadata["file_size_bytes"], 10240)
        self.assertIsInstance(doc.raw_content, bytes)

    def test_raw_document_input_explicit_format_allowed(self):
        """Explicit format assignment is permitted when detection has occurred."""
        doc = RawDocumentInput(
            raw_content="col1,col2\nval1,val2",
            input_source=InputSourceType.FILE_UPLOAD,
            document_format=DocumentFormat.CSV
        )
        self.assertEqual(doc.document_format, DocumentFormat.CSV)

    # =========================================================================
    # 2. SOURCE LOCATION COORDINATE VALIDATION TESTS
    # =========================================================================

    def test_source_location_valid_coordinates(self):
        """Verify SourceLocation accepts valid 1-based coordinates and non-negative offsets."""
        loc_sparse = SourceLocation(line_number=4)
        self.assertEqual(loc_sparse.line_number, 4)
        self.assertIsNone(loc_sparse.page_number)
        self.assertIsNone(loc_sparse.char_start_offset)

        loc_full = SourceLocation(
            page_number=1,
            line_number=12,
            row_number=3,
            column_number=2,
            column_name="Result",
            char_start_offset=120,
            char_end_offset=128
        )
        self.assertEqual(loc_full.column_name, "Result")
        self.assertEqual(loc_full.row_number, 3)
        self.assertEqual(loc_full.char_end_offset, 128)

    def test_source_location_zero_or_negative_page_rejected(self):
        """SourceLocation rejects page_number < 1."""
        with self.assertRaises(ValueError):
            SourceLocation(page_number=0)
        with self.assertRaises(ValueError):
            SourceLocation(page_number=-1)

    def test_source_location_zero_or_negative_line_row_column_rejected(self):
        """SourceLocation rejects line, row, or column < 1."""
        with self.assertRaises(ValueError):
            SourceLocation(line_number=0)
        with self.assertRaises(ValueError):
            SourceLocation(row_number=-5)
        with self.assertRaises(ValueError):
            SourceLocation(column_number=0)

    def test_source_location_negative_offset_rejected(self):
        """SourceLocation rejects negative character offsets."""
        with self.assertRaises(ValueError):
            SourceLocation(char_start_offset=-1)
        with self.assertRaises(ValueError):
            SourceLocation(char_end_offset=-10)

    def test_source_location_end_preceding_start_rejected(self):
        """SourceLocation rejects char_end_offset preceding char_start_offset."""
        with self.assertRaises(ValueError):
            SourceLocation(char_start_offset=50, char_end_offset=40)

        # Equal start and end (0-length match) is valid
        loc_zero_len = SourceLocation(char_start_offset=50, char_end_offset=50)
        self.assertEqual(loc_zero_len.char_start_offset, 50)
        self.assertEqual(loc_zero_len.char_end_offset, 50)

    # =========================================================================
    # 3. RAW OBSERVATION & EXTRACTION CONFIDENCE TESTS
    # =========================================================================

    def test_raw_observation_extraction_confidence_valid_range(self):
        """Accept None, 0.0, 1.0, and values in between for extraction_confidence."""
        # None is valid when extractor does not supply confidence
        raw_none = RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=None)
        self.assertIsNone(raw_none.extraction_confidence)

        # 0.0 boundary
        raw_zero = RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=0.0)
        self.assertEqual(raw_zero.extraction_confidence, 0.0)

        # 1.0 boundary
        raw_one = RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=1.0)
        self.assertEqual(raw_one.extraction_confidence, 1.0)

        # 0.85 typical
        raw_mid = RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=0.85)
        self.assertEqual(raw_mid.extraction_confidence, 0.85)

    def test_raw_observation_extraction_confidence_out_of_bounds_rejected(self):
        """Reject extraction_confidence < 0.0 or > 1.0."""
        with self.assertRaises(ValueError):
            RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=-0.01)

        with self.assertRaises(ValueError):
            RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=1.05)

        with self.assertRaises(ValueError):
            RawObservation(raw_label="Hb", raw_value_text="14.0", extraction_confidence=99.0)

    def test_raw_observation_qualitative_result(self):
        """Verify qualitative results are preserved without fabricating floats."""
        raw_qual = RawObservation(
            raw_label="Urine Protein",
            raw_value_text="Trace Positive",
            detected_value=None,
            parsing_status=ParsingStatus.NON_NUMERIC_RESULT
        )
        self.assertIsNone(raw_qual.detected_value)
        self.assertEqual(raw_qual.raw_value_text, "Trace Positive")
        self.assertEqual(raw_qual.parsing_status, ParsingStatus.NON_NUMERIC_RESULT)

    # =========================================================================
    # 4. NORMALIZED OBSERVATION & STRONGLY TYPED CONVERSION AUDIT TESTS
    # =========================================================================

    def test_normalized_observation_strongly_typed_conversion_audit(self):
        """Verify NormalizedObservation uses strongly typed ConversionAudit model."""
        audit = ConversionAudit(
            original_value=5.0,
            original_unit="mmol/L",
            converted_value=90.09,
            standard_unit="mg/dL",
            conversion_type="LINEAR_SCALE",
            formula_used="mg/dL = mmol/L * 18.0182",
            handler_executed="LINEAR_SCALE"
        )

        norm = NormalizedObservation(
            raw_label="Blood Sugar Fasting",
            original_value_text="5.0",
            original_detected_value=5.0,
            original_unit="mmol/L",
            canonical_metric_id="glucose_fasting",
            canonical_biomarker_name="Fasting Plasma Glucose",
            loinc_code="1558-6",
            normalized_value=90.09,
            normalized_unit="mg/dL",
            source_document_id="DOC-TEST-001",
            conversion_audit=audit,
            ingestion_status=IngestionStatus.VALID,
            validation_messages=["Unit successfully converted via linear scale."]
        )

        # Check that original values are completely intact and not overwritten
        self.assertEqual(norm.raw_label, "Blood Sugar Fasting")
        self.assertEqual(norm.original_value_text, "5.0")
        self.assertEqual(norm.original_detected_value, 5.0)
        self.assertEqual(norm.original_unit, "mmol/L")

        # Check canonical mapping
        self.assertEqual(norm.canonical_metric_id, "glucose_fasting")
        self.assertEqual(norm.loinc_code, "1558-6")

        # Check strongly typed conversion audit
        self.assertIsInstance(norm.conversion_audit, ConversionAudit)
        self.assertEqual(norm.conversion_audit.handler_executed, "LINEAR_SCALE")
        self.assertEqual(norm.conversion_audit.converted_value, 90.09)
        self.assertEqual(norm.ingestion_status, IngestionStatus.VALID)

    def test_normalized_observation_default_status_is_inconclusive(self):
        """Clinical safety rule: default ingestion status must be INCONCLUSIVE until validated."""
        norm = NormalizedObservation(
            raw_label="Unknown Analyte",
            original_value_text="120",
            original_detected_value=120.0,
            original_unit="mg/dL"
        )
        self.assertEqual(norm.ingestion_status, IngestionStatus.INCONCLUSIVE)
        self.assertIsNone(norm.canonical_metric_id)
        self.assertIsNone(norm.normalized_value)
        self.assertIsNone(norm.conversion_audit)

    # =========================================================================
    # 5. STATUS ENUMS & VALIDATION REJECTION TESTS
    # =========================================================================

    def test_structured_status_enums(self):
        """Verify all mandated pipeline statuses exist and evaluate cleanly."""
        mandated_statuses = [
            IngestionStatus.VALID,
            IngestionStatus.UNKNOWN_BIOMARKER,
            IngestionStatus.AMBIGUOUS_BIOMARKER,
            IngestionStatus.MISSING_VALUE,
            IngestionStatus.MISSING_UNIT,
            IngestionStatus.NON_NUMERIC_RESULT,
            IngestionStatus.UNSUPPORTED_UNIT,
            IngestionStatus.CONVERSION_FAILED,
            IngestionStatus.EXTRACTION_FAILED,
            IngestionStatus.INCONCLUSIVE,
        ]
        self.assertEqual(len(mandated_statuses), 10)

        formats = [
            DocumentFormat.UNDETECTED,
            DocumentFormat.PLAIN_TEXT,
            DocumentFormat.CSV,
            DocumentFormat.TSV,
            DocumentFormat.PDF,
            DocumentFormat.IMAGE,
            DocumentFormat.UNSUPPORTED
        ]
        self.assertEqual(len(formats), 7)

    def test_invalid_enum_rejected(self):
        """Pydantic rejects invalid enum assignments."""
        with self.assertRaises(ValueError):
            RawDocumentInput(raw_content="test", input_source="INVALID_SOURCE")

        with self.assertRaises(ValueError):
            NormalizedObservation(
                raw_label="Hb",
                original_value_text="12",
                ingestion_status="PERFECTLY_VALID"  # Invalid enum value
            )

    # =========================================================================
    # 6. JSON SERIALIZATION & DESERIALIZATION TESTS
    # =========================================================================

    def test_pydantic_serialization_and_deserialization(self):
        """Verify round-trip JSON serialization and dictionary conversion with nested models."""
        loc = SourceLocation(page_number=1, line_number=10)
        raw = RawObservation(
            raw_label="Total Cholesterol",
            raw_value_text="190",
            detected_value=190.0,
            raw_unit="mg/dL",
            source_location=loc,
            extraction_confidence=0.95,
            parsing_status=ParsingStatus.PARSED
        )

        d = raw.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["raw_label"], "Total Cholesterol")
        self.assertEqual(d["detected_value"], 190.0)
        self.assertEqual(d["extraction_confidence"], 0.95)

        # JSON round-trip
        json_str = json.dumps(d)
        deserialized_data = json.loads(json_str)
        reconstituted = RawObservation(**deserialized_data)
        self.assertEqual(reconstituted.raw_label, "Total Cholesterol")
        self.assertEqual(reconstituted.source_location.line_number, 10)
        self.assertEqual(reconstituted.extraction_confidence, 0.95)


if __name__ == "__main__":
    unittest.main()
