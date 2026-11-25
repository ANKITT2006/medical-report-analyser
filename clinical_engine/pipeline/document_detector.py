"""
Binary Format Detector & Safe Document Validation (Phase 3.4.1).

Deterministically identifies uploaded document formats from actual binary contents
rather than trusting filename extensions or declared MIME types.
Reuses Phase 3.1/3.2 domain contracts (RawDocumentInput, DocumentFormat,
DocumentProcessingStatus, ExtractionDiagnostic) without duplicating schemas.
"""

import io
import os
import re
import unicodedata
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, UnidentifiedImageError

from clinical_engine.domain.schemas import (
    DocumentFormat,
    DocumentProcessingStatus,
    ExtractionDiagnostic,
    InputSourceType,
    RawDocumentInput,
)

# 10 MB maximum upload size matching frontend dropzone specification
MAX_DOCUMENT_BYTES: int = 10 * 1024 * 1024

# Decompression bomb protection limit for Pillow
MAX_IMAGE_PIXELS_LIMIT: int = 40_000_000

# Magic byte signatures
PDF_SIGNATURE: bytes = b"%PDF-"
PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE: bytes = b"\xff\xd8\xff"
UTF16_LE_BOM: bytes = b"\xff\xfe"
UTF16_BE_BOM: bytes = b"\xfe\xff"
UTF8_BOM: bytes = b"\xef\xbb\xbf"

# Expected extensions and MIME types for mismatch diagnostics (advisory only, never trusted)
_FORMAT_EXPECTED_EXTENSIONS: Dict[str, Tuple[str, ...]] = {
    "PDF": (".pdf",),
    "PNG": (".png",),
    "JPEG": (".jpg", ".jpeg"),
    "CSV": (".csv",),
    "TSV": (".tsv", ".tab"),
    "PLAIN_TEXT": (".txt", ".text", ".log"),
}

_FORMAT_EXPECTED_MIMES: Dict[str, Tuple[str, ...]] = {
    "PDF": ("application/pdf",),
    "PNG": ("image/png",),
    "JPEG": ("image/jpeg", "image/jpg"),
    "CSV": ("text/csv", "application/csv", "text/plain"),
    "TSV": ("text/tab-separated-values", "text/tsv", "text/plain"),
    "PLAIN_TEXT": ("text/plain",),
}


@dataclass
class DocumentDetectionResult:
    """
    Deterministic format detection outcome for a RawDocumentInput.
    Separates format classification, structural verification state, and diagnostics.
    """
    detected_format: DocumentFormat
    processing_status: DocumentProcessingStatus
    diagnostics: List[ExtractionDiagnostic] = field(default_factory=list)
    is_valid_for_ingestion: bool = False
    is_structurally_validated: bool = False
    decoded_text: Optional[str] = None
    detected_encoding: Optional[str] = None
    byte_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentFormatDetector:
    """
    Safe binary-first document format detector.

    Rules:
    - Never trusts filename extensions or browser-declared MIME types as proof of format.
    - Enforces MAX_DOCUMENT_BYTES (10 MB) and rejects empty payloads.
    - Detects PDF candidates via %PDF- magic bytes without claiming full PDF structural validation.
    - Validates PNG and JPEG image integrity via Pillow Image.verify().
    - Detects UTF-8 / UTF-16 text and classifies CSV / TSV / PLAIN_TEXT from content structure.
    - Rejects arbitrary binary payloads safely without exposing raw bytes or patient data.
    """

    @classmethod
    def detect(
        cls,
        doc_input: RawDocumentInput,
        max_bytes: int = MAX_DOCUMENT_BYTES,
    ) -> DocumentDetectionResult:
        """Inspects RawDocumentInput content bytes/str and returns DocumentDetectionResult."""
        raw = doc_input.raw_content
        diagnostics: List[ExtractionDiagnostic] = []

        # 1. Convert input to bytes safely for uniform size and binary inspection
        if raw is None:
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="EMPTY_DOCUMENT",
                diagnostic_message="Document payload is empty (None).",
                severity="ERROR",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.UNSUPPORTED,
                processing_status=DocumentProcessingStatus.EXTRACTION_FAILED,
                diagnostics=diagnostics,
                is_valid_for_ingestion=False,
                byte_size=0,
            )

        if isinstance(raw, str):
            raw_bytes = raw.encode("utf-8", errors="strict")
            input_was_str = True
        elif isinstance(raw, (bytes, bytearray, memoryview)):
            raw_bytes = bytes(raw)
            input_was_str = False
        else:
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="UNSUPPORTED_PAYLOAD_TYPE",
                diagnostic_message=f"Unsupported raw_content type: {type(raw).__name__}.",
                severity="ERROR",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.UNSUPPORTED,
                processing_status=DocumentProcessingStatus.UNSUPPORTED_FORMAT,
                diagnostics=diagnostics,
                is_valid_for_ingestion=False,
                byte_size=0,
            )

        byte_size = len(raw_bytes)

        # 2. Empty check
        if byte_size == 0 or not raw_bytes.strip():
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="EMPTY_DOCUMENT",
                diagnostic_message="Uploaded document contains no data.",
                severity="ERROR",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.UNSUPPORTED,
                processing_status=DocumentProcessingStatus.EXTRACTION_FAILED,
                diagnostics=diagnostics,
                is_valid_for_ingestion=False,
                byte_size=byte_size,
            )

        # 3. Maximum size check (10 MB default)
        if byte_size > max_bytes:
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="DOCUMENT_TOO_LARGE",
                diagnostic_message=(
                    f"Document size ({byte_size} bytes) exceeds maximum allowed limit "
                    f"of {max_bytes} bytes."
                ),
                severity="ERROR",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.UNSUPPORTED,
                processing_status=DocumentProcessingStatus.EXTRACTION_FAILED,
                diagnostics=diagnostics,
                is_valid_for_ingestion=False,
                byte_size=byte_size,
            )

        # 4. Binary signature checks (only on bytes/file uploads, or if str literally starts with binary magic)
        # 4a. PDF signature (%PDF- within leading 1024 bytes per PDF specification)
        if PDF_SIGNATURE in raw_bytes[:1024]:
            cls._check_mismatch_diagnostics(doc_input, "PDF", diagnostics)
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="PDF_CANDIDATE_NOT_STRUCTURALLY_VALIDATED",
                diagnostic_message=(
                    "PDF signature (%PDF-) detected. Full PDF structural validation "
                    "and text extraction require a PDF parser (Step 3.4.2)."
                ),
                severity="INFO",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.PDF,
                processing_status=DocumentProcessingStatus.PENDING,
                diagnostics=diagnostics,
                is_valid_for_ingestion=True,
                is_structurally_validated=False,
                byte_size=byte_size,
                metadata={
                    "signature": "%PDF-",
                    "pdf_candidate_only": True,
                    "structural_validation_performed": False,
                },
            )

        # 4b. PNG signature
        if raw_bytes.startswith(PNG_SIGNATURE):
            return cls._validate_image_bytes(
                raw_bytes=raw_bytes,
                expected_pil_format="PNG",
                doc_input=doc_input,
                diagnostics=diagnostics,
                byte_size=byte_size,
            )

        # 4c. JPEG signature
        if raw_bytes.startswith(JPEG_SIGNATURE):
            return cls._validate_image_bytes(
                raw_bytes=raw_bytes,
                expected_pil_format="JPEG",
                doc_input=doc_input,
                diagnostics=diagnostics,
                byte_size=byte_size,
            )

        # 5. Text detection (UTF-8 / UTF-16) — never silently classify arbitrary binary as text
        decoded_text, encoding = cls._try_decode_safe_text(raw_bytes, input_was_str=input_was_str)
        if decoded_text is not None:
            text_format = cls._classify_text_format(decoded_text)
            cls._check_mismatch_diagnostics(doc_input, text_format.value, diagnostics)
            return DocumentDetectionResult(
                detected_format=text_format,
                processing_status=DocumentProcessingStatus.PENDING,
                diagnostics=diagnostics,
                is_valid_for_ingestion=True,
                is_structurally_validated=True,
                decoded_text=decoded_text,
                detected_encoding=encoding,
                byte_size=byte_size,
                metadata={"encoding": encoding},
            )

        # 6. Unsupported binary content
        diagnostics.append(ExtractionDiagnostic(
            diagnostic_code="UNSUPPORTED_BINARY_CONTENT",
            diagnostic_message=(
                "Uploaded file contains unsupported or unrecognized binary content "
                "that does not match PDF, PNG, JPEG, or valid text encodings."
            ),
            severity="ERROR",
            raw_content=None,
            strategy_name="DOCUMENT_DETECTOR",
        ))
        return DocumentDetectionResult(
            detected_format=DocumentFormat.UNSUPPORTED,
            processing_status=DocumentProcessingStatus.UNSUPPORTED_FORMAT,
            diagnostics=diagnostics,
            is_valid_for_ingestion=False,
            is_structurally_validated=False,
            byte_size=byte_size,
        )

    @classmethod
    def _validate_image_bytes(
        cls,
        raw_bytes: bytes,
        expected_pil_format: str,
        doc_input: RawDocumentInput,
        diagnostics: List[ExtractionDiagnostic],
        byte_size: int,
    ) -> DocumentDetectionResult:
        """Verifies PNG/JPEG integrity via Pillow without exposing raw bytes."""
        prev_max_pixels = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS_LIMIT
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw_bytes)) as img:
                    actual_format = (img.format or "").upper()
                    img.verify()
                # Re-open briefly to safely read dimensions after verify()
                with Image.open(io.BytesIO(raw_bytes)) as img_meta:
                    width, height = img_meta.size
                    mode = img_meta.mode

            if width * height > MAX_IMAGE_PIXELS_LIMIT:
                raise Image.DecompressionBombError(
                    f"Image dimensions ({width}x{height} = {width * height} pixels) "
                    f"exceed limit of {MAX_IMAGE_PIXELS_LIMIT} pixels."
                )

            if actual_format != expected_pil_format:
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="MALFORMED_IMAGE",
                    diagnostic_message=(
                        f"Image signature indicated {expected_pil_format}, "
                        f"but decoded format was '{actual_format}'."
                    ),
                    severity="ERROR",
                    raw_content=None,
                    strategy_name="DOCUMENT_DETECTOR",
                ))
                return DocumentDetectionResult(
                    detected_format=DocumentFormat.UNSUPPORTED,
                    processing_status=DocumentProcessingStatus.CORRUPTED_DOCUMENT,
                    diagnostics=diagnostics,
                    is_valid_for_ingestion=False,
                    is_structurally_validated=False,
                    byte_size=byte_size,
                )

            cls._check_mismatch_diagnostics(doc_input, expected_pil_format, diagnostics)
            return DocumentDetectionResult(
                detected_format=DocumentFormat.IMAGE,
                processing_status=DocumentProcessingStatus.PENDING,
                diagnostics=diagnostics,
                is_valid_for_ingestion=True,
                is_structurally_validated=True,
                byte_size=byte_size,
                metadata={
                    "image_format": actual_format,
                    "width": width,
                    "height": height,
                    "mode": mode,
                },
            )
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="IMAGE_PIXEL_LIMIT_EXCEEDED",
                diagnostic_message=(
                    f"{expected_pil_format} image exceeds maximum allowed pixel limit "
                    f"({MAX_IMAGE_PIXELS_LIMIT} pixels): {type(exc).__name__}."
                ),
                severity="ERROR",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.UNSUPPORTED,
                processing_status=DocumentProcessingStatus.EXTRACTION_FAILED,
                diagnostics=diagnostics,
                is_valid_for_ingestion=False,
                is_structurally_validated=False,
                byte_size=byte_size,
            )
        except (UnidentifiedImageError, SyntaxError, OSError, ValueError) as exc:
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="MALFORMED_IMAGE",
                diagnostic_message=f"Malformed or corrupted {expected_pil_format} image: {type(exc).__name__}.",
                severity="ERROR",
                raw_content=None,
                strategy_name="DOCUMENT_DETECTOR",
            ))
            return DocumentDetectionResult(
                detected_format=DocumentFormat.UNSUPPORTED,
                processing_status=DocumentProcessingStatus.CORRUPTED_DOCUMENT,
                diagnostics=diagnostics,
                is_valid_for_ingestion=False,
                is_structurally_validated=False,
                byte_size=byte_size,
            )
        finally:
            Image.MAX_IMAGE_PIXELS = prev_max_pixels

    @classmethod
    def _try_decode_safe_text(
        cls,
        raw_bytes: bytes,
        input_was_str: bool = False,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempts deterministic UTF-8 or UTF-16 decoding.
        Rejects binary payloads containing NUL bytes or excessive control characters.
        """
        # Check explicit UTF-16 BOMs first
        if raw_bytes.startswith(UTF16_LE_BOM) or raw_bytes.startswith(UTF16_BE_BOM):
            try:
                text = raw_bytes.decode("utf-16", errors="strict")
                if cls._is_printable_text(text):
                    return text, "utf-16"
            except UnicodeDecodeError:
                return None, None
            return None, None

        # Reject NUL bytes in non-UTF-16 payloads (strong binary indicator)
        if b"\x00" in raw_bytes:
            return None, None

        encoding = "utf-8-sig" if raw_bytes.startswith(UTF8_BOM) else "utf-8"
        try:
            text = raw_bytes.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            return None, None

        if not cls._is_printable_text(text):
            return None, None

        return text, ("utf-8" if input_was_str or encoding == "utf-8" else "utf-8-sig")

    @staticmethod
    def _is_printable_text(text: str) -> bool:
        """Verifies text does not contain binary control characters or Unicode replacement noise."""
        if not text or not text.strip():
            return False
        for ch in text:
            if ch in ("\n", "\r", "\t"):
                continue
            cat = unicodedata.category(ch)
            # Reject C0/C1 control characters ('Cc') and replacement character U+FFFD
            if cat == "Cc" or ch == "\ufffd":
                return False
        return True

    @staticmethod
    def _classify_text_format(text: str) -> DocumentFormat:
        """Classifies verified text into TSV, CSV, or PLAIN_TEXT based on structure."""
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            return DocumentFormat.PLAIN_TEXT

        first_line = lines[0]
        # TSV check: tab-separated columns across header (and rows if present)
        if "\t" in first_line:
            tab_cols = len(first_line.split("\t"))
            if tab_cols >= 2 and (len(lines) == 1 or any("\t" in ln for ln in lines[1:5])):
                return DocumentFormat.TSV

        # CSV check: comma or semicolon structured header without key-value colon lines
        if ("," in first_line or ";" in first_line) and ":" not in first_line:
            delim = ";" if (";" in first_line and "," not in first_line) else ","
            cols = len(first_line.split(delim))
            if cols >= 2 and (len(lines) == 1 or any(delim in ln for ln in lines[1:5])):
                return DocumentFormat.CSV

        return DocumentFormat.PLAIN_TEXT

    @classmethod
    def _check_mismatch_diagnostics(
        cls,
        doc_input: RawDocumentInput,
        detected_key: str,
        diagnostics: List[ExtractionDiagnostic],
    ) -> None:
        """Emits WARNING diagnostics when filename extension or declared MIME contradicts actual content."""
        ext = doc_input.detected_extension
        if not ext and doc_input.original_filename:
            _, ext = os.path.splitext(doc_input.original_filename)
        if ext:
            ext_lower = ext.strip().lower()
            expected_exts = _FORMAT_EXPECTED_EXTENSIONS.get(detected_key, ())
            if ext_lower and expected_exts and ext_lower not in expected_exts:
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="EXTENSION_CONTENT_MISMATCH",
                    diagnostic_message=(
                        f"Filename extension '{ext_lower}' does not match detected content format "
                        f"'{detected_key}'."
                    ),
                    severity="WARNING",
                    raw_content=None,
                    strategy_name="DOCUMENT_DETECTOR",
                ))

        if doc_input.declared_mime_type:
            mime_lower = doc_input.declared_mime_type.split(";")[0].strip().lower()
            expected_mimes = _FORMAT_EXPECTED_MIMES.get(detected_key, ())
            if mime_lower and expected_mimes and mime_lower not in expected_mimes:
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="MIME_CONTENT_MISMATCH",
                    diagnostic_message=(
                        f"Declared MIME type '{mime_lower}' does not match detected content format "
                        f"'{detected_key}'."
                    ),
                    severity="WARNING",
                    raw_content=None,
                    strategy_name="DOCUMENT_DETECTOR",
                ))
