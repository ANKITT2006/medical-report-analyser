"""
PDF Text Extraction & Page-Level Source Tracking (Step 3.4.2).

Extracts digital PDF text and structured tables page-by-page using pdfplumber,
preserves 1-based SourceLocation.page_number, routes extracted content through
Phase 3.2 CompositeReportExtractor, prevents text/table duplicates per page,
and emits explicit diagnostics for scanned/encrypted/corrupted/oversized PDFs.
"""

import io
from typing import Any, List, Optional, Set, Tuple

import pdfplumber
from pdfminer.pdfdocument import PDFEncryptionError, PDFPasswordIncorrect
from pdfminer.pdfparser import PDFSyntaxError

from clinical_engine.domain.schemas import (
    DocumentFormat,
    ExtractionDiagnostic,
    ExtractionResult,
    ExtractionStatus,
    InputSourceType,
    RawDocumentInput,
    RawObservation,
    SourceLocation,
)
from clinical_engine.pipeline.document_detector import DocumentFormatDetector
from clinical_engine.pipeline.parser import CompositeReportExtractor

# Maximum PDF page limit enforced without silent truncation
MAX_PDF_PAGES: int = 50

# Minimum non-whitespace characters on an image-containing page before flagging OCR required
MIN_TEXT_CHARS_FOR_NON_SCANNED: int = 20


class PDFTextExtractor:
    """
    Deterministic digital PDF text and table extractor.

    Safety & clinical data-integrity rules:
    - Accepts validated PDF bytes via RawDocumentInput (verified with DocumentFormatDetector).
    - Uses pdfplumber.open() with an in-memory io.BytesIO stream.
    - Preserves 1-based page_number, line_number, and row_number in SourceLocation.
    - Never assigns artificial extraction_confidence to digital PDF text (remains None).
    - Never infers missing units or fabricates missing cells/values.
    - Never exposes raw PDF bytes or patient content in exception messages.
    - Flags image-only/scanned pages with SCANNED_PAGE_OCR_REQUIRED (never silent SUCCESS_EMPTY).
    - Rejects PDFs exceeding MAX_PDF_PAGES (50) with an explicit diagnostic.
    """

    @classmethod
    def extract_from_bytes(
        cls,
        pdf_bytes: bytes,
        original_filename: Optional[str] = None,
        declared_mime_type: Optional[str] = None,
    ) -> ExtractionResult:
        """Convenience entry point wrapping raw bytes into RawDocumentInput."""
        doc = RawDocumentInput(
            raw_content=pdf_bytes,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
            input_source=InputSourceType.FILE_UPLOAD,
        )
        return cls.extract_result(doc)

    @classmethod
    def extract_result(cls, doc_input: RawDocumentInput) -> ExtractionResult:
        """Extracts observations and diagnostics from a PDF RawDocumentInput."""
        # 1. Validate format and size via Phase 3.4.1 DocumentFormatDetector
        det = DocumentFormatDetector.detect(doc_input)
        carried_diagnostics = [
            d for d in det.diagnostics
            if d.diagnostic_code != "PDF_CANDIDATE_NOT_STRUCTURALLY_VALIDATED"
        ]

        if not det.is_valid_for_ingestion or det.detected_format != DocumentFormat.PDF:
            if det.detected_format not in (DocumentFormat.PDF, DocumentFormat.UNSUPPORTED):
                carried_diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="UNEXPECTED_DOCUMENT_FORMAT",
                    diagnostic_message=(
                        f"Expected PDF document, but detected format '{det.detected_format.value}'."
                    ),
                    severity="ERROR",
                    raw_content=None,
                    strategy_name="PDF_TEXT_EXTRACTOR",
                ))
            status = (
                ExtractionStatus.UNSUPPORTED
                if det.detected_format == DocumentFormat.UNSUPPORTED
                else ExtractionStatus.FAILED
            )
            return ExtractionResult(
                observations=[],
                diagnostics=carried_diagnostics,
                extraction_status=status,
                detected_format=det.detected_format,
            )

        raw_bytes = (
            doc_input.raw_content.encode("utf-8")
            if isinstance(doc_input.raw_content, str)
            else bytes(doc_input.raw_content)
        )

        # 2. Open PDF via pdfplumber with explicit encrypted/corrupted handling
        try:
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                total_pages = len(pdf.pages)

                if total_pages == 0:
                    carried_diagnostics.append(ExtractionDiagnostic(
                        diagnostic_code="EMPTY_PDF",
                        diagnostic_message="PDF document contains 0 pages.",
                        severity="ERROR",
                        raw_content=None,
                        strategy_name="PDF_TEXT_EXTRACTOR",
                    ))
                    return ExtractionResult(
                        observations=[],
                        diagnostics=carried_diagnostics,
                        extraction_status=ExtractionStatus.FAILED,
                        detected_format=DocumentFormat.PDF,
                    )

                if total_pages > MAX_PDF_PAGES:
                    carried_diagnostics.append(ExtractionDiagnostic(
                        diagnostic_code="PDF_PAGE_LIMIT_EXCEEDED",
                        diagnostic_message=(
                            f"PDF page count ({total_pages}) exceeds maximum allowed limit "
                            f"of {MAX_PDF_PAGES} pages. Document rejected without truncation."
                        ),
                        severity="ERROR",
                        raw_content=None,
                        strategy_name="PDF_TEXT_EXTRACTOR",
                    ))
                    return ExtractionResult(
                        observations=[],
                        diagnostics=carried_diagnostics,
                        extraction_status=ExtractionStatus.FAILED,
                        detected_format=DocumentFormat.PDF,
                    )

                all_observations: List[RawObservation] = []
                all_diagnostics: List[ExtractionDiagnostic] = list(carried_diagnostics)
                scanned_pages_detected = 0
                failed_pages = 0

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_obs, page_diags, is_scanned = cls._extract_single_page(page, page_num)
                        all_observations.extend(page_obs)
                        all_diagnostics.extend(page_diags)
                        if is_scanned:
                            scanned_pages_detected += 1
                    except Exception as exc:
                        failed_pages += 1
                        all_diagnostics.append(ExtractionDiagnostic(
                            diagnostic_code="PDF_PAGE_EXTRACTION_FAILED",
                            diagnostic_message=(
                                f"Failed to extract content from PDF page {page_num}: {type(exc).__name__}."
                            ),
                            severity="ERROR",
                            source_location=SourceLocation(page_number=page_num),
                            raw_content=None,
                            strategy_name="PDF_TEXT_EXTRACTOR",
                        ))

        except (PDFPasswordIncorrect, PDFEncryptionError):
            carried_diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="ENCRYPTED_PDF",
                diagnostic_message="PDF document is encrypted or password-protected and cannot be read.",
                severity="ERROR",
                raw_content=None,
                strategy_name="PDF_TEXT_EXTRACTOR",
            ))
            return ExtractionResult(
                observations=[],
                diagnostics=carried_diagnostics,
                extraction_status=ExtractionStatus.FAILED,
                detected_format=DocumentFormat.PDF,
            )
        except (PDFSyntaxError, OSError, ValueError, TypeError) as exc:
            carried_diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="CORRUPTED_PDF",
                diagnostic_message=f"Malformed or corrupted PDF structure: {type(exc).__name__}.",
                severity="ERROR",
                raw_content=None,
                strategy_name="PDF_TEXT_EXTRACTOR",
            ))
            return ExtractionResult(
                observations=[],
                diagnostics=carried_diagnostics,
                extraction_status=ExtractionStatus.FAILED,
                detected_format=DocumentFormat.PDF,
            )
        except Exception as exc:
            carried_diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="CORRUPTED_PDF",
                diagnostic_message=f"Unexpected PDF parsing failure: {type(exc).__name__}.",
                severity="ERROR",
                raw_content=None,
                strategy_name="PDF_TEXT_EXTRACTOR",
            ))
            return ExtractionResult(
                observations=[],
                diagnostics=carried_diagnostics,
                extraction_status=ExtractionStatus.FAILED,
                detected_format=DocumentFormat.PDF,
            )

        # 3. Determine final ExtractionStatus per ExtractionResult invariants
        has_error_diag = any(d.severity == "ERROR" for d in all_diagnostics)

        if all_observations and (all_diagnostics and (has_error_diag or scanned_pages_detected > 0 or failed_pages > 0)):
            final_status = ExtractionStatus.PARTIAL_SUCCESS
        elif all_observations and all_diagnostics:
            # Non-error diagnostics (e.g. WARNING) with valid observations -> PARTIAL_SUCCESS or SUCCESS
            final_status = ExtractionStatus.PARTIAL_SUCCESS
        elif all_observations:
            final_status = ExtractionStatus.SUCCESS
        elif has_error_diag or scanned_pages_detected > 0 or failed_pages > 0:
            final_status = ExtractionStatus.FAILED
        else:
            all_diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="PDF_NO_EXTRACTABLE_TEXT",
                diagnostic_message="PDF contains no extractable text or structured observations.",
                severity="INFO",
                raw_content=None,
                strategy_name="PDF_TEXT_EXTRACTOR",
            ))
            final_status = ExtractionStatus.SUCCESS_EMPTY

        return ExtractionResult(
            observations=all_observations,
            diagnostics=all_diagnostics,
            extraction_status=final_status,
            detected_format=DocumentFormat.PDF,
        )

    @classmethod
    def _extract_single_page(
        cls,
        page: Any,
        page_num: int,
    ) -> Tuple[List[RawObservation], List[ExtractionDiagnostic], bool]:
        """
        Extracts observations and diagnostics from one pdfplumber page.
        Runs table extraction first, then layout-preserving text extraction,
        preventing duplicate observations on the same page.
        """
        page_obs: List[RawObservation] = []
        page_diags: List[ExtractionDiagnostic] = []
        seen_signatures: Set[Tuple[str, str, str]] = set()

        # 1. Structured table extraction via pdfplumber
        tables = page.extract_tables() or []
        for table in tables:
            tsv_lines: List[str] = []
            for row in table or []:
                if not row:
                    continue
                cleaned_cells = [
                    (cell or "").replace("\r", " ").replace("\n", " ").strip()
                    for cell in row
                ]
                if any(cleaned_cells):
                    tsv_lines.append("\t".join(cleaned_cells))

            if not tsv_lines:
                continue

            tsv_payload = "\n".join(tsv_lines)
            table_res = CompositeReportExtractor.extract_result(
                tsv_payload,
                document_format=DocumentFormat.TSV,
            )
            for obs in table_res.observations:
                cls._attach_page_location_to_observation(obs, page_num)
                sig = cls._observation_signature(obs)
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    page_obs.append(obs)
            for diag in table_res.diagnostics:
                # Ignore missing-header diagnostics from non-lab bordered boxes (e.g. patient/clinic metadata tables)
                if (
                    not table_res.observations
                    and diag.diagnostic_code in ("MISSING_BIOMARKER_HEADER", "MISSING_RESULT_COLUMN")
                ):
                    continue
                cls._attach_page_location_to_diagnostic(diag, page_num)
                page_diags.append(diag)

        # 2. Layout-preserving text extraction
        page_text = page.extract_text(layout=True) or ""
        non_ws_chars = len("".join(page_text.split()))
        has_images = bool(getattr(page, "images", None))

        # Check for scanned / image-only page
        if non_ws_chars < MIN_TEXT_CHARS_FOR_NON_SCANNED and has_images and not page_obs:
            page_diags.append(ExtractionDiagnostic(
                diagnostic_code="SCANNED_PAGE_OCR_REQUIRED",
                diagnostic_message=(
                    f"Page {page_num} contains embedded image(s) with insufficient extractable "
                    f"digital text ({non_ws_chars} non-whitespace characters). OCR is required."
                ),
                severity="ERROR",
                source_location=SourceLocation(page_number=page_num),
                raw_content=None,
                strategy_name="PDF_TEXT_EXTRACTOR",
            ))
            return page_obs, page_diags, True

        if page_text.strip():
            text_res = CompositeReportExtractor.extract_result(
                page_text,
                document_format=DocumentFormat.PLAIN_TEXT,
            )
            for obs in text_res.observations:
                cls._attach_page_location_to_observation(obs, page_num)
                sig = cls._observation_signature(obs)
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    page_obs.append(obs)
            for diag in text_res.diagnostics:
                cls._attach_page_location_to_diagnostic(diag, page_num)
                page_diags.append(diag)

        return page_obs, page_diags, False

    @staticmethod
    def _observation_signature(obs: RawObservation) -> Tuple[str, str, str]:
        """Deterministic per-page deduplication key preserving exact case-sensitive raw_unit."""
        return (
            obs.raw_label.strip().lower(),
            obs.raw_value_text.strip(),
            (obs.raw_unit or "").strip(),
        )

    @staticmethod
    def _attach_page_location_to_observation(obs: RawObservation, page_num: int) -> None:
        obs.extraction_confidence = None  # Never assign artificial confidence to digital PDF text
        if obs.source_location is None:
            obs.source_location = SourceLocation(page_number=page_num)
        else:
            obs.source_location.page_number = page_num

    @staticmethod
    def _attach_page_location_to_diagnostic(diag: ExtractionDiagnostic, page_num: int) -> None:
        if diag.source_location is None:
            diag.source_location = SourceLocation(page_number=page_num)
        else:
            diag.source_location.page_number = page_num
