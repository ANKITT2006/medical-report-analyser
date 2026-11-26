"""
Phase 3.4.2 Unit Test Suite — PDF Text Extraction & Page-Level Source Tracking.

Uses strictly in-memory technical PDF fixtures (generic non-medical labels/values)
and controlled mocks for encrypted/scanned/page-failure edge cases.
Covers all 14 required test scenarios:
1. Single-page PDF extraction.
2. Multi-page extraction with correct page numbers.
3. Layout-preserving text extraction.
4. Generic table extraction.
5. Routing through Phase 3.2 parser.
6. Duplicate prevention between text and table extraction.
7. Blank PDF handling.
8. Image-only/scanned-page OCR-required diagnostic.
9. Encrypted PDF handling.
10. Corrupted PDF handling.
11. Page-limit enforcement (> 50 pages).
12. Partial extraction when one page fails.
13. Source-location preservation.
14. No fabricated observations or inferred units.
"""

import unittest
from typing import List
from unittest.mock import MagicMock, patch

from pdfminer.pdfdocument import PDFPasswordIncorrect

from clinical_engine.domain.schemas import (
    DocumentFormat,
    ExtractionStatus,
    InputSourceType,
    ParsingStatus,
    RawDocumentInput,
)
from clinical_engine.pipeline.pdf_extractor import MAX_PDF_PAGES, PDFTextExtractor


def _build_technical_pdf(page_streams: List[bytes]) -> bytes:
    """
    Constructs a valid minimal PDF in memory with one content stream per page.
    Contains strictly generic technical text/vector commands.
    """
    objects: List[bytes] = []

    # Obj 1: Catalog, Obj 2: Pages, Obj 3: Font
    num_pages = len(page_streams)
    # Page objects start at 4, content streams start at 4 + num_pages
    page_ids = [4 + i for i in range(num_pages)]
    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for i in range(num_pages):
        content_obj_id = 4 + num_pages + i
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_obj_id} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        ).encode("ascii")
        objects.append(page_dict)

    for stream_bytes in page_streams:
        stream_obj = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )
        objects.append(stream_obj)

    buf = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = [0]
    for idx, obj_body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf.extend(f"{idx} 0 obj\n".encode("ascii"))
        buf.extend(obj_body)
        buf.extend(b"\nendobj\n")

    xref_pos = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    buf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(buf)


def _pdf_text_stream(lines_with_xy: List[tuple]) -> bytes:
    """Helper to build a PDF BT/ET text stream from (x, y, text) tuples."""
    cmds = [b"BT", b"/F1 10 Tf"]
    for x, y, text in lines_with_xy:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        cmds.append(f"1 0 0 1 {x} {y} Tm ({safe}) Tj".encode("latin-1"))
    cmds.append(b"ET")
    return b"\n".join(cmds)


class TestPhase3PDFExtractor(unittest.TestCase):
    """Focused tests for Step 3.4.2 PDFTextExtractor."""

    def test_1_single_page_pdf_extraction(self):
        """1. Single-page digital PDF extracts delimited observations cleanly."""
        stream = _pdf_text_stream([
            (72, 720, "Metric Alpha: 42.5 units/L"),
            (72, 700, "Metric Beta: 18.0 mg/dL"),
        ])
        pdf_bytes = _build_technical_pdf([stream])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="single.pdf")

        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 2)
        self.assertEqual(res.observations[0].raw_label, "Metric Alpha")
        self.assertEqual(res.observations[0].detected_value, 42.5)
        self.assertEqual(res.observations[0].raw_unit, "units/L")
        self.assertIsNone(res.observations[0].extraction_confidence)

    def test_2_multi_page_extraction_with_page_numbers(self):
        """2. Multi-page PDF preserves 1-based page_number per observation."""
        p1 = _pdf_text_stream([(72, 720, "Metric Alpha: 10.0 mg/dL")])
        p2 = _pdf_text_stream([(72, 720, "Metric Beta: 25.0 mmol/L")])
        pdf_bytes = _build_technical_pdf([p1, p2])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="multi.pdf")

        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 2)
        self.assertEqual(res.observations[0].source_location.page_number, 1)
        self.assertEqual(res.observations[1].source_location.page_number, 2)

    def test_3_layout_preserving_text_extraction(self):
        """3. Layout-preserving text extraction parses multi-columnar aligned PDF lines."""
        stream = _pdf_text_stream([
            (72, 720, "Test Name"), (260, 720, "Result"), (380, 720, "Units"),
            (72, 700, "Metric Gamma"), (260, 700, "99.5"), (380, 700, "mg/dL"),
        ])
        pdf_bytes = _build_technical_pdf([stream])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="layout.pdf")

        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Metric Gamma")
        self.assertEqual(res.observations[0].detected_value, 99.5)
        self.assertEqual(res.observations[0].raw_unit, "mg/dL")

    def test_4_generic_table_extraction(self):
        """4. Grid-lined PDF table is extracted via pdfplumber extract_tables() -> TSV strategy."""
        # Draw a 2x3 bordered grid table + text inside cells
        grid = (
            b"0.5 w\n"
            b"70 730 m 400 730 l S\n"
            b"70 710 m 400 710 l S\n"
            b"70 690 m 400 690 l S\n"
            b"70 730 m 70 690 l S\n"
            b"200 730 m 200 690 l S\n"
            b"300 730 m 300 690 l S\n"
            b"400 730 m 400 690 l S\n"
        )
        text = _pdf_text_stream([
            (80, 716, "Test Name"), (210, 716, "Result"), (310, 716, "Unit"),
            (80, 696, "Sample Metric"), (210, 696, "12.3"), (310, 696, "g/dL"),
        ])
        pdf_bytes = _build_technical_pdf([grid + b"\n" + text])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="table.pdf")

        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 1)
        obs = res.observations[0]
        self.assertEqual(obs.raw_label, "Sample Metric")
        self.assertEqual(obs.detected_value, 12.3)
        self.assertEqual(obs.raw_unit, "g/dL")
        self.assertEqual(obs.extraction_method, "CSV_TABLE")
        self.assertEqual(obs.source_location.page_number, 1)

    def test_5_routing_through_phase_3_2_parser(self):
        """5. Page text routes through Phase 3.2 CompositeReportExtractor (respects metadata guards)."""
        stream = _pdf_text_stream([
            (72, 720, "Patient ID: 12345"),
            (72, 700, "Collection Date: 2026-01-15"),
            (72, 680, "Metric Delta: 7.4 %"),
        ])
        pdf_bytes = _build_technical_pdf([stream])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes)

        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Metric Delta")

    def test_6_duplicate_prevention_between_text_and_table_extraction(self):
        """6. Same observation found by both table and layout text on one page is emitted once."""
        # Grid table also appears in page.extract_text(layout=True)
        grid = (
            b"0.5 w\n"
            b"70 730 m 400 730 l S\n"
            b"70 710 m 400 710 l S\n"
            b"70 690 m 400 690 l S\n"
            b"70 730 m 70 690 l S\n"
            b"200 730 m 200 690 l S\n"
            b"300 730 m 300 690 l S\n"
            b"400 730 m 400 690 l S\n"
        )
        text = _pdf_text_stream([
            (80, 716, "Test Name"), (210, 716, "Result"), (310, 716, "Unit"),
            (80, 696, "Metric Unique"), (210, 696, "55.0"), (310, 696, "mg/dL"),
        ])
        pdf_bytes = _build_technical_pdf([grid + b"\n" + text])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes)

        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Metric Unique")

    def test_7_blank_pdf_handling(self):
        """7. Blank digital PDF without images returns SUCCESS_EMPTY with PDF_NO_EXTRACTABLE_TEXT."""
        pdf_bytes = _build_technical_pdf([b""])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="blank.pdf")

        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS_EMPTY)
        self.assertEqual(len(res.observations), 0)
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("PDF_NO_EXTRACTABLE_TEXT", codes)

    def test_8_image_only_scanned_page_ocr_required_diagnostic(self):
        """8. Page with embedded image(s) and little/no text emits SCANNED_PAGE_OCR_REQUIRED (not SUCCESS_EMPTY)."""
        pdf_bytes = _build_technical_pdf([b""])
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = []
        mock_page.extract_text.return_value = "   "
        mock_page.images = [{"x0": 0, "y0": 0, "width": 500, "height": 700}]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = False

        with patch("clinical_engine.pipeline.pdf_extractor.pdfplumber.open", return_value=mock_pdf):
            res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="scanned.pdf")

        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(len(res.observations), 0)
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("SCANNED_PAGE_OCR_REQUIRED", codes)
        self.assertEqual(res.diagnostics[0].source_location.page_number, 1)

    def test_9_encrypted_pdf_handling(self):
        """9. Password-protected/encrypted PDF fails safely with ENCRYPTED_PDF diagnostic."""
        pdf_bytes = _build_technical_pdf([b""])
        with patch(
            "clinical_engine.pipeline.pdf_extractor.pdfplumber.open",
            side_effect=PDFPasswordIncorrect("Incorrect password"),
        ):
            res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="locked.pdf")

        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(len(res.observations), 0)
        self.assertIn("ENCRYPTED_PDF", [d.diagnostic_code for d in res.diagnostics])

    def test_10_corrupted_pdf_handling(self):
        """10. Corrupted PDF body fails safely with CORRUPTED_PDF and exposes no raw bytes."""
        corrupted_pdf = b"%PDF-1.4\nGARBAGE_CORRUPTED_XREF_AND_TRAILER"
        res = PDFTextExtractor.extract_from_bytes(corrupted_pdf, original_filename="corrupt.pdf")

        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(len(res.observations), 0)
        self.assertIn("CORRUPTED_PDF", [d.diagnostic_code for d in res.diagnostics])
        for d in res.diagnostics:
            self.assertIsNone(d.raw_content)

    def test_11_page_limit_enforcement(self):
        """11. PDFs exceeding MAX_PDF_PAGES (50) are rejected safely without silent truncation."""
        pdf_51_pages = _build_technical_pdf([b""] * (MAX_PDF_PAGES + 1))
        res = PDFTextExtractor.extract_from_bytes(pdf_51_pages, original_filename="too_many_pages.pdf")

        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.extraction_status, ExtractionStatus.FAILED)
        self.assertEqual(len(res.observations), 0)
        self.assertIn("PDF_PAGE_LIMIT_EXCEEDED", [d.diagnostic_code for d in res.diagnostics])

    def test_12_partial_extraction_when_one_page_fails(self):
        """12. Failure on one page yields PARTIAL_SUCCESS while preserving valid observations from other pages."""
        pdf_bytes = _build_technical_pdf([b""])

        good_page = MagicMock()
        good_page.extract_tables.return_value = []
        good_page.extract_text.return_value = "Metric Omega: 15.0 mg/dL"
        good_page.images = []

        bad_page = MagicMock()
        bad_page.extract_tables.side_effect = RuntimeError("Page stream decode error")

        mock_pdf = MagicMock()
        mock_pdf.pages = [good_page, bad_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = False

        with patch("clinical_engine.pipeline.pdf_extractor.pdfplumber.open", return_value=mock_pdf):
            res = PDFTextExtractor.extract_from_bytes(pdf_bytes, original_filename="partial.pdf")

        self.assertEqual(res.extraction_status, ExtractionStatus.PARTIAL_SUCCESS)
        self.assertEqual(len(res.observations), 1)
        self.assertEqual(res.observations[0].raw_label, "Metric Omega")
        self.assertEqual(res.observations[0].source_location.page_number, 1)
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("PDF_PAGE_EXTRACTION_FAILED", codes)
        fail_diag = [d for d in res.diagnostics if d.diagnostic_code == "PDF_PAGE_EXTRACTION_FAILED"][0]
        self.assertEqual(fail_diag.source_location.page_number, 2)

    def test_13_source_location_preservation(self):
        """13. Multi-line page preserves both 1-based page_number and line_number."""
        stream = _pdf_text_stream([
            (72, 740, "Header Line"),
            (72, 720, "Metric One: 10.0 mg/dL"),
            (72, 700, "Metric Two: 20.0 mg/dL"),
        ])
        pdf_bytes = _build_technical_pdf([stream])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes)

        self.assertEqual(len(res.observations), 2)
        for obs in res.observations:
            self.assertIsNotNone(obs.source_location)
            self.assertEqual(obs.source_location.page_number, 1)
            self.assertIsNotNone(obs.source_location.line_number)
            self.assertGreaterEqual(obs.source_location.line_number, 1)

    def test_14_no_fabricated_observations_or_inferred_units(self):
        """14. Missing unit remains None and qualitative text is never coerced to float."""
        stream = _pdf_text_stream([
            (72, 720, "Metric Unitless: 42"),
            (72, 700, "Metric Qual: Negative"),
        ])
        pdf_bytes = _build_technical_pdf([stream])
        res = PDFTextExtractor.extract_from_bytes(pdf_bytes)

        self.assertEqual(res.extraction_status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(res.observations), 2)
        self.assertIsNone(res.observations[0].raw_unit)
        self.assertEqual(res.observations[0].detected_value, 42.0)
        self.assertEqual(res.observations[1].parsing_status, ParsingStatus.NON_NUMERIC_RESULT)
        self.assertIsNone(res.observations[1].detected_value)
        self.assertIsNone(res.observations[1].raw_unit)


if __name__ == "__main__":
    unittest.main()
