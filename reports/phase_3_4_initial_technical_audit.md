# MEDIPULSE AI — PHASE 3.4 INITIAL TECHNICAL AUDIT
## PDF, IMAGE & OCR DOCUMENT INGESTION

**Date**: 2026-11-25  
**Project**: MediPulse AI — Medical Report Analyzer  
**Project Root**: `C:\Users\Ankit's_YOGA\Desktop\report_analyser\medical-report-analyser\`  
**Phase**: Phase 3 — Data Ingestion & Unit Normalization Pipeline  
**Subphase**: 3.4 — PDF, Image & OCR Document Ingestion (Pre-Implementation Audit)  
**Mode**: AUDIT ONLY (Zero source code, data, or dependency modifications performed)  

---

## 1. EXECUTIVE SUMMARY

Phase 3.1 (Domain Contracts), Phase 3.2 (Multi-Strategy Text & Tabular Extractors), and Phase 3.3 (Deterministic Unit Normalization & Canonical Biomarker Mapping) are complete and verified. Before implementing Phase 3.4 (PDF, Image, and OCR Document Ingestion), an empirical technical audit of the codebase, frontend/backend upload pipeline, and runtime environment was conducted.

### Key Audit Conclusions
1. **Domain Contracts Are Ready**: `clinical_engine/domain/schemas.py` already defines `RawDocumentInput`, `DocumentFormat` (`PDF`, `IMAGE`, `UNDETECTED`, `UNSUPPORTED`), `DocumentProcessingStatus`, `SourceLocation` (including `page_number`), `RawObservation.extraction_confidence`, `ExtractionDiagnostic`, and `ExtractionResult`.
2. **Critical Frontend/Backend Binary Upload Gap**: `website/index.html` advertises `.pdf`, `.png`, `.jpg`, `.jpeg` uploads (up to 10 MB), but `website/script.js` calls `FileReader.readAsText(file)` on **all** uploaded files, corrupting binary PDF/image payloads into garbled UTF-8 text and submitting them to the JSON-only `POST /analyze` endpoint in `website/app.py`.
3. **Missing Runtime PDF & OCR Capabilities**:
   - **PDF extraction**: No PDF library (`pypdf`, `PyPDF2`, `fitz`/PyMuPDF, `pdfplumber`, `pdfminer`) and no CLI tool (`pdftotext`, `pdftoppm`, `gs`) is installed.
   - **OCR**: No OCR engine (`pytesseract`, `easyocr`, `rapidocr_onnxruntime`, `onnxruntime`) and no `tesseract.exe` binary is installed.
   - **Image decoding**: `pillow 12.1.0` (`PIL`), `numpy 2.4.2`, `torch 2.14.0`, and `torchvision 0.29.0` **are** installed, enabling basic image validation/metadata inspection, but **not** OCR.
4. **Readiness Verdict**: Architecture and contract design for Phase 3.4 are ready, and **magic-byte format detection + fail-safe binary upload rejection** can be implemented immediately. However, **actual PDF text extraction and OCR cannot execute** in the current environment until approved PDF/OCR dependencies are installed and verified.

---

## 2. EXISTING ARCHITECTURE & ACTUAL FINDINGS

### 2.1 Domain Contracts (`clinical_engine/domain/schemas.py`)
The Phase 3.1/3.2 contracts already anticipate binary document ingestion:
- **`InputSourceType`**: `TEXT_INPUT`, `FILE_UPLOAD`.
- **`DocumentFormat`**: `UNDETECTED`, `PLAIN_TEXT`, `CSV`, `TSV`, `PDF`, `IMAGE`, `UNSUPPORTED`.
- **`RawDocumentInput`**:
  - Accepts `raw_content: Any` (`str` or `bytes`).
  - Stores `original_filename`, `declared_mime_type`, `detected_extension`, `document_id`, and `file_metadata`.
  - **Safety invariant**: `FILE_UPLOAD` defaults `document_format` to `DocumentFormat.UNDETECTED` (never `PLAIN_TEXT`), preventing filename extensions or declared MIME types from being trusted without content inspection.
- **`DocumentProcessingStatus`**: `PENDING`, `EXTRACTED`, `EXTRACTION_FAILED`, `UNSUPPORTED_FORMAT`, `CORRUPTED_DOCUMENT`.
- **`SourceLocation`**: Validates 1-based `page_number`, `line_number`, `row_number`, `column_number`, and non-negative character offsets (`char_start_offset`, `char_end_offset`).
- **`RawObservation`**: Includes `extraction_method: str`, `extraction_confidence: Optional[float]` (validated in `[0.0, 1.0]`), `parsing_status: ParsingStatus`, and `source_location: Optional[SourceLocation]`.
- **`ExtractionResult` & `ExtractionDiagnostic`**: Strictly separates extraction errors/warnings (`diagnostics`) from clinical observations (`observations`), enforcing explicit `ExtractionStatus` (`SUCCESS`, `SUCCESS_EMPTY`, `PARTIAL_SUCCESS`, `FAILED`, `UNSUPPORTED`).

### 2.2 Extraction Pipeline (`clinical_engine/pipeline/parser.py`)
- `CompositeReportExtractor.extract_result(content: str, document_format: DocumentFormat)` currently accepts **`str` only** and dispatches across:
  1. `CSVTableStrategy` (CSV / TSV / semicolon-delimited tables)
  2. `DelimitedTextStrategy` (`:` / `=` / `-` key-value lines)
  3. `ColumnarTableStrategy` (whitespace-aligned tables)
  4. `MultilinePairStrategy` (unambiguous label-then-value line pairs)
- None of these strategies accept `bytes`, `RawDocumentInput`, or multi-page PDF structures, and none currently populate `SourceLocation.page_number` or `RawObservation.extraction_confidence`.

### 2.3 Normalization & Clinical Evaluation Boundary
- **Phase 3.3 (`clinical_engine/pipeline/normalizer.py`)**: `ObservationNormalizer` transforms `List[RawObservation]` into `List[NormalizedObservation]`, enforcing canonical biomarker resolution (`CanonicalBiomarkerResolver`), lexical unit normalization (`UnitLexicalNormalizer`), exact case-sensitive SQL unit matching (`metric_unit_conversions`), and `ConversionAudit` provenance. Only fully validated numeric observations receive `IngestionStatus.VALID`.
- **Phase 2 (`clinical_engine/pipeline/engine.py`)**: `DiagnosticEngine.analyze_report()` still invokes the legacy `ClinicalReportParser.parse_text()` directly and does not yet consume `CompositeReportExtractor` or `ObservationNormalizer`.

---

## 3. INSTALLED LIBRARIES & UNAVAILABLE CAPABILITIES

Audited against the active project Python environment (`Python 3.13`):

| Capability | Inspected Packages / Binaries | Actual Status | Notes |
| :--- | :--- | :--- | :--- |
| **PDF Text / Layout Extraction** | `pypdf`, `PyPDF2`, `fitz` (PyMuPDF), `pdfplumber`, `pdfminer` | **Unavailable** (`False`) | Zero Python PDF libraries installed. |
| **PDF CLI / Rendering Tools** | `pdftotext`, `pdftoppm` (Poppler), `gs` (Ghostscript) | **Unavailable** | `where.exe` returned not found; `C:\Program Files\poppler` absent. |
| **Image Decoding & Manipulation** | `pillow` (`PIL` v12.1.0), `numpy` (v2.4.2) | **Installed** | Can open/verify PNG/JPEG headers, dimensions, DPI, and convert color modes. |
| **OpenCV** | `cv2` | **Unavailable** (`False`) | Not installed; PIL/NumPy can cover basic preprocessing if needed. |
| **OCR Engines (Python)** | `pytesseract`, `easyocr`, `rapidocr_onnxruntime`, `onnxruntime` | **Unavailable** (`False`) | Zero OCR packages installed. |
| **OCR Binaries (System)** | `tesseract.exe` | **Unavailable** | Not on PATH and absent from `C:\Program Files\Tesseract-OCR` and `C:\Program Files (x86)\Tesseract-OCR`. |
| **HTTP / Multipart Parsing** | `http.server` (stdlib), `python-multipart` (v0.0.22), `fastapi` (v0.135.3), `Flask` (v3.1.3) | **Installed** | `website/app.py` currently uses stdlib `http.server`. |
| **Deep Learning Runtime** | `torch` (v2.14.0), `torchvision` (v0.29.0) | **Installed** | Available if a local OCR engine (e.g., EasyOCR) were ever approved, though offline model weights are not present. |

**Conclusion**: Neither PDF text extraction nor image OCR is currently executable in this environment. No PDF or OCR capability may be claimed as working until dependencies are installed and verified against real test inputs.

---

## 4. CURRENT PDF / IMAGE UPLOAD LIMITATIONS

### 4.1 Frontend (`website/index.html` & `website/script.js`)
1. **Misleading UI Acceptance**: `website/index.html` (line 294–299) accepts `.txt,.csv,.pdf,.png,.jpg,.jpeg` and displays `"Supports TXT, CSV, PDF, or image lab reports (Max 10MB)"`.
2. **Binary Corruption via `readAsText()`**: `website/script.js` (`handleUploadedFile`, lines 165–177) executes `reader.readAsText(file)` unconditionally for every file type, decoding raw PDF/PNG/JPEG bytes as UTF-8 text and writing binary garbage into `#report-text`.
3. **No Size Enforcement**: The advertised 10 MB limit is not checked in JavaScript.
4. **JSON-Only Submission**: `analyzeMedicalReport()` (lines 181–210) sends `{ query: text, gender, age, category }` as `application/json` to `POST http://127.0.0.1:5000/analyze`.

### 4.2 Backend (`website/app.py`)
1. **No Binary / Multipart Endpoint**: `MedicalReportHandler.do_POST()` only handles `/analyze` and assumes `json.loads(body.decode("utf-8"))`.
2. **No Upload Size Limit**: `content_length = int(self.headers.get("Content-Length", 0))` reads the entire request body into memory without a max-bytes guard.
3. **No Magic-Byte Format Detection**: No component inspects file signatures (`%PDF-`, PNG `\x89PNG\r\n\x1a\n`, JPEG `\xff\xd8\xff`, UTF-8 text vs binary NUL bytes).
4. **No Phase 3 Pipeline Wiring**: `app.py` calls `engine.analyze_report()` directly rather than `RawDocumentInput` $\rightarrow$ format detection $\rightarrow$ extraction $\rightarrow$ `ObservationNormalizer`.

---

## 5. RECOMMENDED PDF EXTRACTION & OCR ARCHITECTURE

### 5.1 Binary Format Detection & Validation Gate (First Stage)
Before any extraction runs, a deterministic `DocumentFormatDetector` must inspect `RawDocumentInput`:
1. Enforce maximum payload size (e.g., 10 MB) and non-empty content.
2. Inspect **magic bytes** (not file extension or `declared_mime_type`):
   - `%PDF-` (within first 1024 bytes) $\rightarrow$ `DocumentFormat.PDF`
   - `\x89PNG\r\n\x1a\n` or `\xff\xd8\xff` (and verified via `PIL.Image.open().verify()`) $\rightarrow$ `DocumentFormat.IMAGE`
   - Valid UTF-8 / UTF-16 text without NUL bytes: dispatch to CSV/TSV/PLAIN_TEXT detection.
   - Mismatched extension/MIME vs magic bytes (e.g., `.pdf` extension containing PNG bytes or executable bytes) $\rightarrow$ emit `ExtractionDiagnostic` (`FORMAT_SPOOFING_OR_MISMATCH` / `UNSUPPORTED_FORMAT`) and fail safely.

### 5.2 PDF Processing Architecture
1. **Digital PDF Text Extraction (Page-by-Page)**:
   - Use a deterministic Python PDF library (recommended: `pypdf` for pure-Python text extraction, or `pdfplumber` / `pymupdf` for layout-preserving table extraction).
   - Extract text **per page** (`page_number = 1..N`), preserving page boundaries so every `RawObservation` and `ExtractionDiagnostic` carries accurate `SourceLocation(page_number=p, line_number=l)`.
   - Feed each page's extracted text through Phase 3.2 `CompositeReportExtractor.extract_result(...)`, propagating `page_number` onto every resulting `SourceLocation`.
2. **Scanned PDF Detection**:
   - A PDF page (or entire PDF) is classified as **scanned / image-only** when:
     - Extracted character count per page falls below a strict threshold (e.g., `< 20` non-whitespace characters) **and** embedded images exist on the page, OR
     - Extracted text consists solely of replacement characters (`\ufffd`) / control garbage (corrupted font encoding).
   - When a scanned PDF is detected:
     - If OCR is unavailable/disabled: do **not** return `SUCCESS_EMPTY` silently; return `ExtractionStatus.FAILED` or `PARTIAL_SUCCESS` with an explicit `ExtractionDiagnostic` (`SCANNED_PDF_OCR_REQUIRED`).
     - If OCR is available and enabled: rasterize the affected page(s) to images and route to the OCR pipeline with `extraction_method="PDF_OCR"` and explicit `extraction_confidence`.
3. **Encrypted / Corrupted PDFs**:
   - Password-protected PDFs $\rightarrow$ `DocumentProcessingStatus.EXTRACTION_FAILED` / `ExtractionDiagnostic(diagnostic_code="ENCRYPTED_PDF")`.
   - Malformed PDF streams $\rightarrow$ `DocumentProcessingStatus.CORRUPTED_DOCUMENT` / `ExtractionDiagnostic(diagnostic_code="CORRUPTED_PDF")`.

### 5.3 Image Processing & OCR Architecture
1. **Image Validation & Preprocessing**:
   - Verify integrity with `PIL.Image.open(io.BytesIO(raw_bytes)).verify()`, enforce pixel dimension limits (decompression bomb protection via `Image.MAX_IMAGE_PIXELS`), normalize EXIF orientation (`ImageOps.exif_transpose`), and convert to RGB/grayscale.
2. **OCR Engine & Confidence Governance**:
   - Every OCR-extracted line/token must retain word/line-level confidence scores normalized to `[0.0, 1.0]` in `RawObservation.extraction_confidence`.
   - **Strict Low-Confidence Safety Gate**:
     - Define an explicit confidence threshold (e.g., `MIN_OCR_CONFIDENCE = 0.75`).
     - Observations with `extraction_confidence < MIN_OCR_CONFIDENCE` must **never** be passed to Phase 3.3 as trusted numeric values (`ParsingStatus.PARSED`); instead, record an `ExtractionDiagnostic` (`LOW_OCR_CONFIDENCE`, `severity="WARNING"` or `"ERROR"`) preserving the raw OCR text and `SourceLocation`, or mark `ParsingStatus.EXTRACTION_FAILED` so Phase 3.3 assigns `IngestionStatus.EXTRACTION_FAILED`.
     - Never silently coerce ambiguous OCR characters (e.g., `O` vs `0`, `l` vs `1`, `u` vs `µ`) into numeric values without preserving the exact raw text.

---

## 6. REQUIRED BACKEND & FRONTEND CHANGES (FUTURE PHASE 3.4 IMPLEMENTATION)

### 6.1 Backend (`website/app.py` & `clinical_engine/pipeline/`)
- Add `clinical_engine/pipeline/document_loader.py` (or `binary_extractor.py`) to handle:
  - `RawDocumentInput` validation and magic-byte `DocumentFormat` detection.
  - `PDFExtractor` (page-level text extraction + scanned-page detection).
  - `ImageOCRExtractor` (PIL verification + OCR adapter with confidence gating).
- Add `POST /analyze-document` (or extend `POST /analyze` to branch on `Content-Type`):
  - Accept `multipart/form-data` (for raw binary file uploads) or JSON text requests.
  - Enforce 10 MB size cap (`413 Payload Too Large` on excess).
  - Return structured `ExtractionResult` diagnostics alongside normalized/clinical results so users see explicit reasons when a PDF is scanned/encrypted or OCR is unavailable.

### 6.2 Frontend (`website/script.js` & `website/index.html`)
- Replace unconditional `reader.readAsText(file)` in `handleUploadedFile(file)`:
  - Enforce the 10 MB client-side size check before reading.
  - Only use `readAsText` for `.txt`/`.csv` files.
  - For `.pdf`, `.png`, `.jpg`, `.jpeg`, store the `File` object and send it as binary (`FormData` / `multipart/form-data`) to the backend document endpoint instead of dumping binary bytes into `#report-text`.
  - Render extraction diagnostics (e.g., scanned PDF warnings, low-confidence OCR notices, unsupported format errors) cleanly in the UI.

---

## 7. SECURITY & CLINICAL DATA-INTEGRITY CONSIDERATIONS

1. **No Extension or MIME Trust**: Format detection must rely strictly on magic bytes and structural parsing (`PIL.verify()`, PDF header/trailer validation), never on filename extensions or browser `File.type`.
2. **Decompression Bombs & Resource Exhaustion**: Cap upload size (10 MB), PDF page count (e.g., max 50 pages), and `PIL.Image.MAX_IMAGE_PIXELS` to prevent memory exhaustion on malformed images or PDFs.
3. **Zero Fabrication & Zero Unit Inference**:
   - Missing units on OCR/PDF lines remain `MISSING_UNIT` in Phase 3.3.
   - Missing or unreadable values remain `MISSING_VALUE` or `EXTRACTION_FAILED`.
   - Low-confidence OCR observations cannot become `IngestionStatus.VALID`.
4. **Separation of Diagnostics & Observations**: Unreadable pages, low-confidence lines, and corrupted files emit `ExtractionDiagnostic` records and never masquerade as `RawObservation` records.
5. **Preserve Phase 3.3 & Phase 2 Boundaries**: PDF/OCR extractors only produce `ExtractionResult` (`List[RawObservation]` + `List[ExtractionDiagnostic]`). All unit normalization remains in Phase 3.3 `ObservationNormalizer`, and all clinical interpretation remains in Phase 2 `DiagnosticEngine`.

---

## 8. DEPENDENCIES REQUIRED (NOT INSTALLED DURING AUDIT)

To enable actual PDF and OCR execution in Phase 3.4, the following dependencies would need explicit user approval and installation:

| Purpose | Candidate Package(s) | Notes / Trade-offs |
| :--- | :--- | :--- |
| **PDF Text & Layout Extraction** | `pypdf` (pure Python) and/or `pdfplumber` (built on `pdfminer.six`) | `pypdf` is lightweight with no native C build issues; `pdfplumber` improves multi-column lab table extraction. |
| **OCR Engine (Option A - Local Python)** | `rapidocr-onnxruntime` (or `easyocr`, using already-installed `torch`) | Pure pip-installable without external OS installer; `rapidocr-onnxruntime` is lightweight, whereas `easyocr` uses `torch` (already installed) + downloads model weights on first run. |
| **OCR Engine (Option B - Tesseract)** | `pytesseract` + Windows `tesseract.exe` binary | Requires external system binary installation outside `pip`. |
| **PDF-to-Image Rasterization (for scanned PDFs)** | `pypdfium2` (pure pip wheel, no Poppler required) or `pdf2image` + Poppler | `pypdfium2` avoids external Windows Poppler binary setup. |

> [!IMPORTANT]
> No packages or OCR models were installed or downloaded during this audit.

---

## 9. IMPLEMENTATION RISKS & UNRESOLVED DECISIONS

1. **OCR Engine Choice**: Selecting between `rapidocr-onnxruntime` (lightweight ONNX), `easyocr` (leverages already-installed `torch`, requires model weights), or `pytesseract` (requires external `tesseract.exe` system binary).
2. **PDF Table Fidelity**: Clinical lab reports frequently use multi-column tables (Test Name | Result | Units | Reference Range). Plain `pypdf` text extraction can scramble column order compared to `pdfplumber` word-bounding-box extraction.
3. **Minimum OCR Confidence Policy**: Exact `MIN_OCR_CONFIDENCE` cutoff (e.g., `0.75` vs `0.85`) and whether low-confidence lines should halt the entire document or allow `PARTIAL_SUCCESS` with explicit per-line warnings.
4. **Backend Upload Transport**: Whether `website/app.py` continues on stdlib `http.server` (parsing `multipart/form-data` via `python-multipart` or `email.parser`) or transitions to `FastAPI`/`Flask` (already installed in the environment).

---

## 10. PROPOSED SMALL IMPLEMENTATION SEQUENCE FOR PHASE 3.4

1. **Step 3.4.1 — Binary Format Detector & Safe Upload Contract**:
   - Implement magic-byte `DocumentFormatDetector` (size limits, PDF/PNG/JPEG/Text detection, extension/MIME mismatch diagnostics) and unit tests using in-memory byte headers.
2. **Step 3.4.2 — PDF Text & Page-Location Extractor**:
   - Install approved PDF library (`pypdf` / `pdfplumber`), implement page-by-page extraction preserving `SourceLocation(page_number=...)`, scanned-PDF detection, and encrypted/corrupted PDF error handling.
3. **Step 3.4.3 — Image Preprocessing & OCR Extractor with Confidence Gate**:
   - Install approved OCR library, implement `PIL` validation + OCR extraction with `[0.0, 1.0]` confidence scoring and strict low-confidence rejection (`ExtractionDiagnostic`).
4. **Step 3.4.4 — Frontend Binary Upload & Backend Endpoint Integration**:
   - Update `website/script.js` (remove `readAsText` on binary files, send `FormData` with 10 MB check) and `website/app.py` (add binary upload handling wired through Phase 3.2 $\rightarrow$ Phase 3.3 $\rightarrow$ Phase 2).

---

## 11. READINESS STATEMENT

**Phase 3.4 implementation is technically ready to begin** at the design and binary-validation level (Step 3.4.1), because Phase 3.1 contracts (`RawDocumentInput`, `DocumentFormat`, `SourceLocation.page_number`, `ExtractionDiagnostic`, `ExtractionResult`) and Phase 3.2/3.3 pipelines are already in place and verified. However, **Steps 3.4.2 and 3.4.3 (live PDF text extraction and OCR) cannot be executed until the user approves and installs the required PDF and OCR dependencies**.
