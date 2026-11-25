"""
Phase 3.4.1 Unit Test Suite — Binary Format Detector & Safe Document Validation.

Uses strictly in-memory technical fixtures (no synthetic patient reports).
Covers all 12 required scenarios:
1. Valid PDF signature detection.
2. Valid PNG detection and image verification.
3. Valid JPEG detection and image verification.
4. Plain-text detection (UTF-8 and UTF-16).
5. CSV and TSV-compatible text detection.
6. Empty-file rejection.
7. Oversized-file rejection (> 10 MB).
8. Unsupported binary rejection.
9. Extension/content mismatch diagnostics.
10. MIME/content mismatch diagnostics.
11. Malformed PNG/JPEG rejection.
12. PDF header detection without falsely claiming structural validation.
"""

import io
import unittest
from PIL import Image

from clinical_engine.domain.schemas import (
    DocumentFormat,
    DocumentProcessingStatus,
    InputSourceType,
    RawDocumentInput,
)
from clinical_engine.pipeline.document_detector import (
    DocumentFormatDetector,
    MAX_DOCUMENT_BYTES,
)


def _make_in_memory_image_bytes(fmt: str, size=(16, 16)) -> bytes:
    """Generates minimal valid in-memory PNG or JPEG bytes using Pillow."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(255, 255, 255))
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestPhase3DocumentDetector(unittest.TestCase):
    """Focused tests for binary-first DocumentFormatDetector."""

    def test_1_valid_pdf_signature_detection(self):
        """1. Valid PDF signature (%PDF-) detects DocumentFormat.PDF."""
        pdf_bytes = b"%PDF-1.4\n%minimal technical header\n%%EOF\n"
        doc = RawDocumentInput(
            raw_content=pdf_bytes,
            original_filename="technical_sample.pdf",
            declared_mime_type="application/pdf",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res = DocumentFormatDetector.detect(doc)
        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertEqual(res.processing_status, DocumentProcessingStatus.PENDING)
        self.assertTrue(res.is_valid_for_ingestion)
        self.assertEqual(res.metadata.get("signature"), "%PDF-")

    def test_2_valid_png_detection_and_image_verification(self):
        """2. Valid PNG bytes pass signature and Pillow Image.verify()."""
        png_bytes = _make_in_memory_image_bytes("PNG")
        doc = RawDocumentInput(
            raw_content=png_bytes,
            original_filename="scan.png",
            declared_mime_type="image/png",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res = DocumentFormatDetector.detect(doc)
        self.assertEqual(res.detected_format, DocumentFormat.IMAGE)
        self.assertEqual(res.processing_status, DocumentProcessingStatus.PENDING)
        self.assertTrue(res.is_valid_for_ingestion)
        self.assertTrue(res.is_structurally_validated)
        self.assertEqual(res.metadata.get("image_format"), "PNG")
        self.assertEqual(res.metadata.get("width"), 16)
        self.assertEqual(res.metadata.get("height"), 16)

    def test_3_valid_jpeg_detection_and_image_verification(self):
        """3. Valid JPEG bytes pass signature and Pillow Image.verify()."""
        jpg_bytes = _make_in_memory_image_bytes("JPEG")
        doc = RawDocumentInput(
            raw_content=jpg_bytes,
            original_filename="photo.jpg",
            declared_mime_type="image/jpeg",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res = DocumentFormatDetector.detect(doc)
        self.assertEqual(res.detected_format, DocumentFormat.IMAGE)
        self.assertEqual(res.processing_status, DocumentProcessingStatus.PENDING)
        self.assertTrue(res.is_valid_for_ingestion)
        self.assertTrue(res.is_structurally_validated)
        self.assertEqual(res.metadata.get("image_format"), "JPEG")

    def test_4_plain_text_detection_utf8_and_utf16(self):
        """4. Plain UTF-8 and UTF-16 text payloads detect as PLAIN_TEXT."""
        utf8_doc = RawDocumentInput(
            raw_content=b"Line one: alpha\nLine two: beta\n",
            original_filename="notes.txt",
            declared_mime_type="text/plain",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res_utf8 = DocumentFormatDetector.detect(utf8_doc)
        self.assertEqual(res_utf8.detected_format, DocumentFormat.PLAIN_TEXT)
        self.assertTrue(res_utf8.is_valid_for_ingestion)
        self.assertEqual(res_utf8.detected_encoding, "utf-8")

        utf16_bytes = "Line one: alpha\nLine two: beta\n".encode("utf-16")
        utf16_doc = RawDocumentInput(
            raw_content=utf16_bytes,
            original_filename="notes_utf16.txt",
            declared_mime_type="text/plain",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res_utf16 = DocumentFormatDetector.detect(utf16_doc)
        self.assertEqual(res_utf16.detected_format, DocumentFormat.PLAIN_TEXT)
        self.assertTrue(res_utf16.is_valid_for_ingestion)
        self.assertEqual(res_utf16.detected_encoding, "utf-16")

    def test_5_csv_and_tsv_compatible_text_detection(self):
        """5. CSV and TSV structures are detected from content, not extension."""
        csv_doc = RawDocumentInput(
            raw_content=b"col_a,col_b,col_c\nval1,val2,val3\n",
            original_filename="data.bin",  # non-csv extension ignored
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res_csv = DocumentFormatDetector.detect(csv_doc)
        self.assertEqual(res_csv.detected_format, DocumentFormat.CSV)
        self.assertTrue(res_csv.is_valid_for_ingestion)

        tsv_doc = RawDocumentInput(
            raw_content=b"col_a\tcol_b\tcol_c\nval1\tval2\tval3\n",
            original_filename="data.txt",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res_tsv = DocumentFormatDetector.detect(tsv_doc)
        self.assertEqual(res_tsv.detected_format, DocumentFormat.TSV)
        self.assertTrue(res_tsv.is_valid_for_ingestion)

    def test_6_empty_file_rejection(self):
        """6. Empty bytes, empty string, and whitespace-only payloads are rejected."""
        for empty_payload in (b"", "", b"   \n\t  ", None):
            doc = RawDocumentInput(
                raw_content=empty_payload,
                original_filename="empty.pdf",
                declared_mime_type="application/pdf",
                input_source=InputSourceType.FILE_UPLOAD,
            )
            res = DocumentFormatDetector.detect(doc)
            self.assertEqual(res.detected_format, DocumentFormat.UNSUPPORTED)
            self.assertEqual(res.processing_status, DocumentProcessingStatus.EXTRACTION_FAILED)
            self.assertFalse(res.is_valid_for_ingestion)
            codes = [d.diagnostic_code for d in res.diagnostics]
            self.assertIn("EMPTY_DOCUMENT", codes)

    def test_7_oversized_file_rejection(self):
        """7. Payloads exceeding MAX_DOCUMENT_BYTES (10 MB) are rejected."""
        oversized = b"A" * (MAX_DOCUMENT_BYTES + 1)
        doc = RawDocumentInput(
            raw_content=oversized,
            original_filename="huge.txt",
            declared_mime_type="text/plain",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res = DocumentFormatDetector.detect(doc)
        self.assertEqual(res.detected_format, DocumentFormat.UNSUPPORTED)
        self.assertEqual(res.processing_status, DocumentProcessingStatus.EXTRACTION_FAILED)
        self.assertFalse(res.is_valid_for_ingestion)
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("DOCUMENT_TOO_LARGE", codes)

    def test_8_unsupported_binary_rejection(self):
        """8. Arbitrary/unsupported binary bytes (e.g. ELF/ZIP/NUL) are never classified as text."""
        for bad_bytes in (
            b"\x7fELF\x02\x01\x01\x00\x00\x00",
            b"PK\x03\x04\x14\x00\x00\x00",
            b"\x00\xff\xfe\xfa\x81\x82\x83",
        ):
            doc = RawDocumentInput(
                raw_content=bad_bytes,
                original_filename="disguised.txt",
                declared_mime_type="text/plain",
                input_source=InputSourceType.FILE_UPLOAD,
            )
            res = DocumentFormatDetector.detect(doc)
            self.assertEqual(res.detected_format, DocumentFormat.UNSUPPORTED)
            self.assertEqual(res.processing_status, DocumentProcessingStatus.UNSUPPORTED_FORMAT)
            self.assertFalse(res.is_valid_for_ingestion)
            self.assertIsNone(res.decoded_text)
            codes = [d.diagnostic_code for d in res.diagnostics]
            self.assertIn("UNSUPPORTED_BINARY_CONTENT", codes)
            for d in res.diagnostics:
                self.assertIsNone(d.raw_content)

    def test_9_extension_content_mismatch_diagnostic(self):
        """9. PNG bytes with .pdf extension still classify as IMAGE and emit EXTENSION_CONTENT_MISMATCH."""
        png_bytes = _make_in_memory_image_bytes("PNG")
        doc = RawDocumentInput(
            raw_content=png_bytes,
            original_filename="misnamed.pdf",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res = DocumentFormatDetector.detect(doc)
        self.assertEqual(res.detected_format, DocumentFormat.IMAGE)
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("EXTENSION_CONTENT_MISMATCH", codes)

    def test_10_mime_content_mismatch_diagnostic(self):
        """10. Plain text with application/pdf MIME classifies as PLAIN_TEXT and emits MIME_CONTENT_MISMATCH."""
        doc = RawDocumentInput(
            raw_content=b"Simple technical text line\n",
            original_filename="report.txt",
            declared_mime_type="application/pdf",
            input_source=InputSourceType.FILE_UPLOAD,
        )
        res = DocumentFormatDetector.detect(doc)
        self.assertEqual(res.detected_format, DocumentFormat.PLAIN_TEXT)
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("MIME_CONTENT_MISMATCH", codes)

    def test_11_malformed_png_and_jpeg_rejection(self):
        """11. Truncated/corrupted PNG and JPEG headers fail Pillow verification safely."""
        bad_png = b"\x89PNG\r\n\x1a\nCORRUPTED_DATA"
        res_png = DocumentFormatDetector.detect(
            RawDocumentInput(
                raw_content=bad_png,
                original_filename="bad.png",
                input_source=InputSourceType.FILE_UPLOAD,
            )
        )
        self.assertEqual(res_png.detected_format, DocumentFormat.UNSUPPORTED)
        self.assertEqual(res_png.processing_status, DocumentProcessingStatus.CORRUPTED_DOCUMENT)
        self.assertFalse(res_png.is_valid_for_ingestion)
        self.assertIn("MALFORMED_IMAGE", [d.diagnostic_code for d in res_png.diagnostics])

        bad_jpg = b"\xff\xd8\xff\xe0CORRUPTED_JPEG_STREAM"
        res_jpg = DocumentFormatDetector.detect(
            RawDocumentInput(
                raw_content=bad_jpg,
                original_filename="bad.jpg",
                input_source=InputSourceType.FILE_UPLOAD,
            )
        )
        self.assertEqual(res_jpg.detected_format, DocumentFormat.UNSUPPORTED)
        self.assertEqual(res_jpg.processing_status, DocumentProcessingStatus.CORRUPTED_DOCUMENT)
        self.assertFalse(res_jpg.is_valid_for_ingestion)
        self.assertIn("MALFORMED_IMAGE", [d.diagnostic_code for d in res_jpg.diagnostics])

    def test_12_pdf_header_does_not_claim_structural_validation(self):
        """12. %PDF- signature identifies PDF candidate without claiming full structural validation."""
        pdf_candidate = b"%PDF-1.7\nGARBAGE_UNPARSED_BODY"
        res = DocumentFormatDetector.detect(
            RawDocumentInput(
                raw_content=pdf_candidate,
                original_filename="candidate.pdf",
                declared_mime_type="application/pdf",
                input_source=InputSourceType.FILE_UPLOAD,
            )
        )
        self.assertEqual(res.detected_format, DocumentFormat.PDF)
        self.assertFalse(res.is_structurally_validated)
        self.assertTrue(res.metadata.get("pdf_candidate_only"))
        self.assertFalse(res.metadata.get("structural_validation_performed"))
        codes = [d.diagnostic_code for d in res.diagnostics]
        self.assertIn("PDF_CANDIDATE_NOT_STRUCTURALLY_VALIDATED", codes)

    def test_13_decompression_bomb_warning_and_error_thresholds_rejected(self):
        """
        13. Images exceeding MAX_IMAGE_PIXELS_LIMIT (40M pixels) are rejected for both
        the warning band (40M < px <= 80M) and error band (> 80M), without allocating
        large image buffers and without mutating global warning filters.
        """
        import struct
        import warnings
        import zlib

        def _make_minimal_png_header_only(width: int, height: int) -> bytes:
            # Valid PNG signature + IHDR chunk + IEND chunk (no pixel allocation)
            ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
            ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
            iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
            iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
            return b"\x89PNG\r\n\x1a\n" + ihdr_chunk + iend_chunk

        filters_before = list(warnings.filters)

        # 50,000,000 pixels (between 1x and 2x MAX_IMAGE_PIXELS_LIMIT -> triggers DecompressionBombWarning)
        png_50m = _make_minimal_png_header_only(10000, 5000)
        res_50m = DocumentFormatDetector.detect(
            RawDocumentInput(raw_content=png_50m, original_filename="bomb50m.png", input_source=InputSourceType.FILE_UPLOAD)
        )
        self.assertEqual(res_50m.detected_format, DocumentFormat.UNSUPPORTED)
        self.assertEqual(res_50m.processing_status, DocumentProcessingStatus.EXTRACTION_FAILED)
        self.assertFalse(res_50m.is_valid_for_ingestion)
        self.assertIn("IMAGE_PIXEL_LIMIT_EXCEEDED", [d.diagnostic_code for d in res_50m.diagnostics])

        # 100,000,000 pixels (> 2x MAX_IMAGE_PIXELS_LIMIT -> triggers DecompressionBombError)
        png_100m = _make_minimal_png_header_only(10000, 10000)
        res_100m = DocumentFormatDetector.detect(
            RawDocumentInput(raw_content=png_100m, original_filename="bomb100m.png", input_source=InputSourceType.FILE_UPLOAD)
        )
        self.assertEqual(res_100m.detected_format, DocumentFormat.UNSUPPORTED)
        self.assertEqual(res_100m.processing_status, DocumentProcessingStatus.EXTRACTION_FAILED)
        self.assertFalse(res_100m.is_valid_for_ingestion)
        self.assertIn("IMAGE_PIXEL_LIMIT_EXCEEDED", [d.diagnostic_code for d in res_100m.diagnostics])

        # Global warning filters must remain unchanged
        self.assertEqual(warnings.filters, filters_before)

    def test_14_text_line_separators_and_control_character_handling(self):
        """
        14. Ordinary line separators (\\n, \\r\\n, \\t) and UTF-16 BOM are accepted,
        while invalid control characters and NUL bytes in UTF-8 are rejected.
        """
        # Multiline UTF-8 LF
        res_lf = DocumentFormatDetector.detect(
            RawDocumentInput(raw_content=b"Line A: 10\nLine B: 20\n", input_source=InputSourceType.FILE_UPLOAD)
        )
        self.assertEqual(res_lf.detected_format, DocumentFormat.PLAIN_TEXT)
        self.assertTrue(res_lf.is_valid_for_ingestion)

        # CRLF text
        res_crlf = DocumentFormatDetector.detect(
            RawDocumentInput(raw_content=b"Line A: 10\r\nLine B: 20\r\n", input_source=InputSourceType.FILE_UPLOAD)
        )
        self.assertEqual(res_crlf.detected_format, DocumentFormat.PLAIN_TEXT)
        self.assertTrue(res_crlf.is_valid_for_ingestion)

        # Valid TSV with tabs and CRLF/LF newlines
        res_tsv = DocumentFormatDetector.detect(
            RawDocumentInput(raw_content=b"col1\tcol2\r\nval1\tval2\r\n", input_source=InputSourceType.FILE_UPLOAD)
        )
        self.assertEqual(res_tsv.detected_format, DocumentFormat.TSV)
        self.assertTrue(res_tsv.is_valid_for_ingestion)

        # Invalid control characters (e.g. BEL \x07, ESC \x1b, NUL \x00) rejected
        for bad_text in (b"Line A\x07\n", b"Line A\x1b[31m\n", b"Line A\x00Line B\n"):
            res_bad = DocumentFormatDetector.detect(
                RawDocumentInput(raw_content=bad_text, input_source=InputSourceType.FILE_UPLOAD)
            )
            self.assertEqual(res_bad.detected_format, DocumentFormat.UNSUPPORTED)
            self.assertEqual(res_bad.processing_status, DocumentProcessingStatus.UNSUPPORTED_FORMAT)
            self.assertFalse(res_bad.is_valid_for_ingestion)


if __name__ == "__main__":
    unittest.main()
