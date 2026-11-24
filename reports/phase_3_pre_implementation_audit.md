# MEDIPULSE AI — PHASE 3.0 INITIAL TECHNICAL AUDIT & INGESTION ARCHITECTURE SPECIFICATION

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-23  
**Lead System Roles:** Senior Healthcare Software Architect, Clinical Data Engineer, Python Backend Engineer, Quality Assurance Engineer  
**Authoritative Project Root:** `C:\Users\Ankit's_YOGA\Desktop\report_analyser\medical-report-analyser\`  
**Target Development Phase:** Phase 3 — Data Ingestion & Unit Normalization Pipeline  
**Execution Constraints Applied:** Zero source modifications, zero dependency installations, zero Git state mutations, zero synthetic data generation, preservation of canonical Phase 2 clinical datasets.

---

## 1. Executive Summary

This technical audit performs a baseline assessment of the ingestion, parsing, extraction, and unit normalization architecture of MediPulse AI prior to commencing Phase 3 implementation.

### Key Audit Findings
1. **Parser & Lexical Extraction Capabilities**:
   - The current ingestion engine relies exclusively on a single regex pattern in `clinical_engine/pipeline/parser.py` (`OBSERVATION_PATTERN`).
   - It only processes single-line colon, hyphen, or equals-separated key-value pairs (e.g. `Hemoglobin: 14.5 g/dL`).
   - It possesses **zero structural tabular ingestion** (CSV, TSV, fixed-width laboratory tables, multi-column reports).
   - It possesses **zero binary document processing** (PDF streams, text streams, OCR on raster images / scanned reports).
2. **Frontend File Dropzone Disconnect**:
   - The web UI (`website/index.html` and `website/script.js`) presents a dropzone advertising support for `.txt`, `.csv`, `.pdf`, `.png`, `.jpg`, and `.jpeg`.
   - In reality, `script.js` uses `FileReader.readAsText()` on all files regardless of MIME type.
   - Dropping a binary PDF or JPEG directly into the dropzone causes binary byte garble to be pasted into the textarea, resulting in complete extraction failure.
   - When backend communication fails, the frontend runs a client-side regex fallback (`executeClientSideTokenizer()`), which renders an unverified report with static placeholder numbers (`score: 100`, `normalCount: N`, `abnormalCount: 0`).
3. **Unit Normalization & Conversion Registry**:
   - The unit conversion registry (`clinical_engine/pipeline/converters.py`) is secure, deterministic, and explicitly allowlisted (`LINEAR_SCALE` and `HBA1C_IFCC_TO_NGSP`), strictly prohibiting dynamic code execution (`eval()` / `exec()`).
   - However, incoming units must match the exact string registered in the SQLite `metric_unit_conversions` table. There is no lexical unit tokenizer or canonical alias mapper for units (e.g., `mg/dl`, `MG/DL`, `mg / dL`, `milligram/deciliter`, `mmol/l`, `µmol/L` vs `umol/L`).
4. **Current Test Suite Health**:
   - The Phase 2 test suite (`tests/test_canonical_phase_2.py` and `tests/test_clinical_engine.py`) has 42 active tests.
   - All 42 tests and the JSON Schema Draft 2020-12 validator (`scripts/validate_phase_2.py`) pass cleanly with exit code 0.
   - However, existing tests cover only clean synthetic strings formatted as `Key: Value Unit`. Zero tests exist for tabular formats, malformed laboratory text, multi-column inputs, PDF extraction, OCR, or file upload handling.

---

## 2. Actual Project Architecture

```
[User Interface / Dropzone]
       │
       ▼ (Raw Text Payload via JSON /analyze)
[website/app.py: MedicalReportHandler]
       │
       ▼ (report_text: str, patient_context)
[clinical_engine/pipeline/engine.py: DiagnosticEngine]
       │
       ├───► [pipeline/parser.py: ClinicalReportParser]
       │         └── Extracts List[ParsedObservation] (raw_key, detected_value, raw_unit)
       │
       ├───► [storage/repository.py: SQLClinicalRepository]
       │         └── Contextual Interval & Critical Limit Query (DeterministicClinicalSelector)
       │
       ├───► [pipeline/converters.py: convert_laboratory_value]
       │         └── Safe Allowlisted Conversion (LINEAR_SCALE / HBA1C_IFCC_TO_NGSP)
       │
       └───► Clinical Finding Generation (Diagnostic Thresholds, Protocols, AnalysisReport)
```

### Inspected Backend Components
- `clinical_engine/pipeline/parser.py`: Pure regex line-by-line extractor returning `ParsedObservation`.
- `clinical_engine/pipeline/converters.py`: Allowlisted mathematical converter with `ConversionAudit` provenance tracking.
- `clinical_engine/pipeline/engine.py`: Orchestrates parsing, unit harmonization, range evaluation, and diagnostic alert attachment.
- `clinical_engine/domain/schemas.py`: Data contracts (`ParsedObservation`, `PatientContext`, `ClinicalContext`, `ReferenceInterval`, `CriticalLimit`, `ClinicalFinding`, `AnalysisReport`).
- `clinical_engine/storage/repository.py`: SQLite DAO layer querying `data/clinical_knowledge.db`.
- `website/app.py`: Standard library `http.server.HTTPServer` exposing `/health`, `/metrics`, and `/analyze`.

---

## 3. Files Inspected & Findings

### 3.1 `clinical_engine/pipeline/parser.py`
- **Class**: `ClinicalReportParser`
- **Data Structure**:
  ```python
  @dataclass
  class ParsedObservation:
      raw_key: str
      detected_value: Optional[float]
      raw_unit: Optional[str]
      line_number: int
      is_inconclusive: bool = False
      inconclusive_reason: Optional[str] = None
  ```
- **Regex Pattern**:
  ```python
  OBSERVATION_PATTERN = re.compile(
      r"(?P<label>[A-Za-z0-9_\s\(\)\/\-\.]{2,40}?)\s*[:=\-]\s*(?P<value>[+\-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?P<unit>[A-Za-z\/%µu\^0-9\-\*]+)?",
      re.IGNORECASE
  )
  ```
- **Observations**:
  * Strips leading noise (bullets, list numbers, asterisks).
  * Requires a delimiter (`:`, `=`, `-`) between biomarker label and value.
  * Cannot parse space-separated or tab-separated tables where no colon exists.
  * Captures everything trailing the value into `unit` without unit validation.

### 3.2 `clinical_engine/pipeline/converters.py`
- **Functions & Handlers**:
  * `UnitConversionRegistry.linear_scale(value, factor)`
  * `UnitConversionRegistry.hba1c_ifcc_to_ngsp(value)`
  * `convert_laboratory_value(...)`
- **Audit Tracking**:
  * Creates `ConversionAudit` containing `original_value`, `original_unit`, `converted_value`, `standard_unit`, `conversion_type`, `formula_used`, and `handler_executed`.
- **Observations**:
  * Prohibits dynamic evaluation (`eval`/`exec`).
  * If incoming unit matches standard unit case-insensitively, bypasses conversion cleanly.
  * Raises `ValueError` if handler is not in `ALLOWED_CONVERSION_HANDLERS`.

### 3.3 `clinical_engine/pipeline/engine.py`
- **Method**: `DiagnosticEngine.evaluate_observation(raw_label, detected_val, raw_unit, patient)`
- **Flow**:
  1. Calls `repository.get_contextual_metric_reference(raw_label, patient)`. Alias resolution is handled in SQL repository via `lab_metric_aliases`.
  2. If raw unit differs from standard canonical unit, queries `repository.get_unit_conversion(metric_id, raw_unit)`.
  3. If conversion is missing, returns `ClinicalFinding` with `status = MetricStatus.INCONCLUSIVE`, `clinical_note = "Unsupported unit '{raw_unit}'..."`.
  4. Preserves `conversion_applied = conversion_info` on the finding.
- **Observations**:
  * The `AnalysisReport` retains `findings[].detected_value`, but replaces `detected_value` with the converted value in `ClinicalFinding.detected_value` while storing original details in `conversion_applied`.
  * `raw_label` is stored on unknown metrics, but on recognized metrics `biomarker_name` is taken from `canonical_name` or `population`.

### 3.4 `clinical_engine/storage/repository.py`
- **Method**: `SQLClinicalRepository.get_contextual_metric_reference(test_name_or_code, patient)`
- **Alias Resolution**:
  * Case-insensitive SQL queries against `lab_metrics.metric_id`, `lab_metrics.canonical_name`, `lab_metrics.loinc_code`, and `lab_metric_aliases.alias_name`.
- **Observations**:
  * Highly robust for indexed canonical biomarkers.
  * Trims whitespace and lowercases search tokens.

### 3.5 `website/app.py`
- **Endpoints**:
  * `GET /health`: Returns service status and biomarker/protocol counts.
  * `GET /metrics`: Returns all registered biomarkers and units.
  * `POST /analyze`: Receives `{ query, gender, age, category }`, passes to `engine.analyze_report()`, and returns JSON response.
- **Observations**:
  * Accepts only JSON text bodies. No `multipart/form-data` endpoint exists.
  * Expects text to already be extracted before reaching `/analyze`.

### 3.6 `website/script.js` & `website/index.html`
- **Upload Dropzone**:
  * Line 294 of `index.html`: `<input type="file" id="file-input" accept=".txt,.csv,.pdf,.png,.jpg,.jpeg">`.
  * Line 170 of `script.js`:
    ```javascript
    const reader = new FileReader();
    reader.onload = (event) => {
        document.getElementById('report-text').value = event.target.result;
        switchInputTab('text');
        showToast(`Loaded ${file.name}`);
    };
    reader.readAsText(file);
    ```
- **Observations**:
  * **Critical Flaw**: `readAsText()` is invoked on PDFs, PNGs, and JPEGs. It dumps raw binary/mojibake into the textarea.
  * **Fallback Risk**: If backend `POST /analyze` fails or is offline, lines 218–324 invoke `executeClientSideTokenizer(text)` which generates an unverified clinical overview with a perfect score (`score: 100`, `normalCount: N`, `abnormalCount: 0`). This violates clinical transparency if unverified outputs are displayed to patients.

---

## 4. Existing Dependencies Inventory

Inspected active Python 3.13 environment (`C:\Users\Ankit's_YOGA\AppData\Local\Programs\Python\Python313\python.exe`):

| Capability | Installed Library | Version | Status in Project |
| :--- | :--- | :--- | :--- |
| **Data Validation & Schemas** | `pydantic` | 2.12.5 | Actively used in `domain/schemas.py` and `converters.py` |
| **JSON Schema Validation** | `jsonschema` | 4.26.0 | Actively used in `scripts/validate_phase_2.py` |
| **Tabular Data Processing** | `pandas` | 3.0.1 | **Installed in environment, NOT imported in pipeline** |
| **Numeric Array Processing** | `numpy` | 2.4.2 | **Installed in environment, NOT imported in pipeline** |
| **Image Processing** | `pillow` (PIL) | 12.1.0 | **Installed in environment, NOT imported in pipeline** |
| **PDF Extraction** | *None* (No `pypdf`, `pdfplumber`, `pymupdf`, or `pdfminer`) | Not installed | Missing |
| **Optical Character Recognition (OCR)** | *None* (No `pytesseract` or OCR engine) | Not installed | Missing |
| **Web Server Framework** | Python standard library `http.server` | Stdlib | In `website/app.py` |
| **Frontend Tooling** | `vite` | 8.3.0 | In `package.json` devDependencies |

*Verification*: No dependencies were installed or modified during this audit.

---

## 5. Existing Test Results & Coverage

### 5.1 Test Suite Execution
```powershell
& "C:\Users\Ankit's_YOGA\AppData\Local\Programs\Python\Python313\python.exe" -m unittest discover -v tests
```
- **Execution Output**:
  ```text
  Ran 42 tests in 0.475s
  OK
  ```
- **Exit Code**: `0`

### 5.2 Schema Validator Execution
```powershell
& "C:\Users\Ankit's_YOGA\AppData\Local\Programs\Python\Python313\python.exe" scripts/validate_phase_2.py
```
- **Execution Output**:
  ```text
  Total Canonical Biomarkers Cataloged : 20 / 20
  Total Unique LOINC Codes (LOINC 2.83): 20 / 20
  Total Reference Intervals Validated  : 26
  Total Diagnostic Cutoffs Validated   : 22
  Total Critical Limits Validated      : 12
  Total Treatment Targets Documented   : 9
  Total Risk Classification Tiers      : 28
  Total Errors Found                   : 0
  Total Warnings                       : 0
  [VALIDATION SUCCESS]
  ```
- **Exit Code**: `0`

### 5.3 Ingestion & Parser Test Coverage Matrix

| Ingestion Category | Tested in Current Suite? | Existing Test Function | Notes / Gaps |
| :--- | :---: | :--- | :--- |
| Simple Colon-Delimited Text | **Yes** | `test_parser_feature_extraction` | `Hemoglobin: 10.2 g/dL` |
| Hyphen / Equals Delimiters | **Yes** | `test_parser_feature_extraction` | `Fasting Blood Glucose = 135` |
| Comma-Separated Thousand Values | **Yes** | Regex `OBSERVATION_PATTERN` | e.g. `210,000 /uL` |
| Unsupported Unit Rejection | **Yes** | `test_engine_unsupported_unit_finding` | Verified `INCONCLUSIVE` output |
| Alternative Unit Linear Conversion | **Yes** | `test_linear_unit_conversion` | Glucose mmol/L to mg/dL |
| Non-Linear Formula Conversion | **Yes** | `test_nonlinear_hba1c_ifcc_to_ngsp_conversion` | HbA1c IFCC to NGSP |
| Tabular Formats (CSV / TSV) | **No** | *None* | Zero CSV extraction tests |
| Multi-column Text / Whitespace Delimited | **No** | *None* | Zero tests for tabular text layouts |
| Real-world Noisy Medical Text | **No** | *None* | Headers, doctor notes, dates not tested |
| PDF Document Ingestion | **No** | *None* | Zero PDF parser tests |
| Image / Scanned Document OCR | **No** | *None* | Zero image tests |
| Multipart Upload API Integration | **No** | *None* | `app.py` has zero test suite coverage |

---

## 6. Detailed Phase 3 Implementation Gap Analysis

### Gap A: File Format Handling & Extraction Disconnect
- **File**: `website/script.js` (lines 170–177), `website/index.html` (lines 292–305)
- **Deficiency**: The UI advertises `.pdf`, `.png`, and `.jpg` support, but executes `FileReader.readAsText(file)`. This corrupts binary files and dumps garbled ASCII/UTF-8 bytes into the textarea, resulting in zero extracted biomarkers.
- **Recommended Correction**:
  1. Introduce dedicated file validation checking magic bytes / file signatures before upload.
  2. Implement backend multipart upload endpoint (`POST /upload` or `POST /analyze/file`) that routes text, CSV, PDF, and image files to specialized parsers.
  3. If binary formats cannot be processed natively without external dependencies, restrict frontend dropzone to validated formats (`.txt`, `.csv`) or provide transparent client-side notifications.

### Gap B: Delimiter-Rigid Plain Text Parsing
- **File**: `clinical_engine/pipeline/parser.py` (lines 26–29)
- **Deficiency**: `OBSERVATION_PATTERN` strictly requires a delimiter (`:`, `=`, or `-`). Real-world reports often format tests as space-separated columns:
  ```text
  Test Name               Result    Unit      Reference Range
  Hemoglobin              13.5      g/dL      12.0 - 15.5
  Serum Creatinine        1.1       mg/dL     0.7 - 1.3
  ```
  The current parser fails completely on this common format.
- **Recommended Correction**: Implement a multi-strategy parsing pipeline in `parser.py`:
  * Strategy 1: Delimited Key-Value regex.
  * Strategy 2: Columnar / Fixed-width tabular regex.
  * Strategy 3: Multi-line value-on-next-line patterns.

### Gap C: Structural CSV & Tabular Parsing
- **File**: `clinical_engine/pipeline/parser.py`
- **Deficiency**: Currently has no dedicated CSV parser. When a CSV file is passed as text, `OBSERVATION_PATTERN` fails unless the line happens to contain colons or hyphens instead of commas.
- **Recommended Correction**:
  * Add a dedicated `TabularReportParser` using Python's built-in `csv.Sniffer` and `csv.reader`.
  * Detect headers (`Test Name`, `Result`, `Units`) and map column indices dynamically.

### Gap D: PDF Text Extraction
- **File**: *Missing in repository*
- **Deficiency**: There is no PDF reader or parser module. No PDF library is imported or invoked.
- **Recommended Correction**:
  * Architect a pluggable document extractor (`clinical_engine/ingestion/extractors/pdf_extractor.py`).
  * If a text-layer PDF is supplied, extract text streams cleanly before routing to the observation parser.
  * Strictly avoid non-deterministic ML/LLM text scrapers.

### Gap E: Image & Scanned OCR
- **File**: *Missing in repository*
- **Deficiency**: No OCR engine or image processing pipeline exists.
- **Recommended Correction**:
  * Architect an abstract `BaseExtractor` interface with a `scanned_image` adapter.
  * Clearly define failure states: if OCR dependencies are missing or image quality is unreadable, emit a structured `UNPROCESSED_FILE_TYPE` or `UNREADABLE_IMAGE` error rather than silently failing.

### Gap F: Unit Variation & Normalization Mismatch
- **File**: `clinical_engine/pipeline/engine.py` (lines 159–179)
- **Deficiency**: The engine checks:
  ```python
  if raw_unit and raw_unit.strip().lower() != standard_unit.strip().lower():
      unit_conv = self.repository.get_unit_conversion(metric_id, raw_unit)
  ```
  If incoming unit is `mg/dl` and conversion table stores `mg/dL`, it succeeds. But if incoming unit is `MG/DL` or contains punctuation/formatting variations (e.g., `mg / dL`, `g/dl.`, `gm/dL`, `cells/mcL` vs `cells/uL`), lookup fails and marks the observation `INCONCLUSIVE`.
- **Recommended Correction**:
  * Implement a deterministic `UnitNormalizer` utility that standardizes common unit representations (e.g. `gm/dl` $\to$ `g/dL`, `mg / dl` $\to$ `mg/dL`, `u/l` $\to$ `U/L`, `mcl` $\to$ `uL`) prior to conversion registry lookup.

### Gap G: Preservation of Original vs. Converted Measurements
- **File**: `clinical_engine/pipeline/engine.py` (lines 320–329) and `domain/schemas.py` (`ClinicalFinding`)
- **Deficiency**: When unit conversion occurs (e.g. 5.0 mmol/L $\to$ 90.09 mg/dL), `ClinicalFinding.detected_value` is overwritten with the converted value (`90.09`), while original value `5.0` and unit `mmol/L` are nested inside `finding.conversion_applied["original_value"]`.
- **Recommended Correction**:
  * Elevate data contracts in `ClinicalFinding` to explicitly include top-level fields:
    * `original_detected_value: Optional[float]`
    * `original_unit: Optional[str]`
    * `normalized_value: Optional[float]`
    * `normalized_unit: str`
    * `conversion_audit: Optional[ConversionAudit]`

### Gap H: Client-Side Fallback Clinical Safety Violation
- **File**: `website/script.js` (lines 278–324)
- **Deficiency**: When the backend API is unreachable, `executeClientSideTokenizer` generates a synthetic green report (`score: 100`, `normalCount: N`, `riskClass: 'badge-normal'`).
- **Recommended Correction**:
  * Remove synthetic fallback scoring. If backend connection fails, display a clear, transparent error message: `"Backend engine unavailable. Clinical verification cannot be performed offline."`

---

## 7. Required Target Ingestion Architecture (Phase 3)

The Phase 3 architecture will enforce this deterministic 8-stage pipeline:

```
[Stage 1: Raw Ingestion & File Validation]
  ├── Format Detection (Magic bytes / MIME / Extension)
  └── Integrity Check (Empty file, size limits, binary vs text)
            │
            ▼
[Stage 2: Text & Table Extraction]
  ├── TextStreamExtractor (Plain text, log streams)
  ├── TabularExtractor (CSV / TSV delimiter detection)
  ├── PDFStreamExtractor (Native text stream parser)
  └── OCRExtractor (Scanned documents - if engine present)
            │
            ▼
[Stage 3: Observation Lexical Tokenization]
  ├── Line-by-line Delimited Parsing
  ├── Columnar / Tabular Layout Parsing
  └── Extraction Metadata (Source line, column, raw tokens)
            │
            ▼
[Stage 4: Canonical Biomarker Resolution]
  ├── Normalized Token Cleaning (Punctuation, case, noise)
  ├── Database Alias Registry Lookup (SQL Repository)
  └── Status Flagging (MATCHED, UNKNOWN_BIOMARKER, AMBIGUOUS)
            │
            ▼
[Stage 5: Unit Recognition & Normalization]
  ├── Lexical Unit Standardization (Format, casing, symbols)
  ├── Standard Unit Alignment Check
  └── Allowlisted Mathematical Conversion (LINEAR / FORMULA)
            │
            ▼
[Stage 6: Ingestion Validation & Audit Packaging]
  ├── Range Sanity Checks (Extreme non-physiological values)
  └── Complete Provenance Packaging:
        - raw_label, canonical_id
        - original_value, original_unit
        - normalized_value, normalized_unit
        - source_file, source_line
        - conversion_provenance
            │
            ▼
[Stage 7: Clinical Evaluation Engine]
  └── Ingests validated NormalizedObservation into DiagnosticEngine
```

---

## 8. Ordered Phase 3 Implementation Breakdown

The recommended execution plan for Phase 3 consists of 5 modular steps:

### Step 3.1: Ingestion Domain Contracts & Ingestion Schemas
- Enhance `clinical_engine/domain/schemas.py`:
  * Define `RawDocumentInput` (content, mime_type, file_name).
  * Define `NormalizedObservation` with explicit separation of original vs. normalized measurements and source locations.
  * Define structured ingestion status enums (`VALID`, `UNKNOWN_BIOMARKER`, `UNSUPPORTED_UNIT`, `CORRUPT_VALUE`, `UNSUPPORTED_FORMAT`).

### Step 3.2: Multi-Strategy Text & Tabular Extractors
- Expand `clinical_engine/pipeline/parser.py`:
  * Implement `DelimitedTextStrategy` (improved regex for multi-delimiter formats).
  * Implement `ColumnarTableStrategy` (whitespace and column-aligned text).
  * Implement `CSVTableStrategy` (structured CSV parsing with header sniffing).

### Step 3.3: Deterministic Unit Lexical Normalizer
- Enhance `clinical_engine/pipeline/converters.py`:
  * Implement `UnitLexicalNormalizer` mapping typographic variations (e.g. `mg/dl`, `MG/DL`, `mg / dL`, `g/dl`, `gm/dL`, `u/l`, `IU/L`) to standard canonical tokens.
  * Preserve strict allowlisting and zero `eval()` execution.

### Step 3.4: Backend Upload Handler & Engine Integration
- Update `clinical_engine/pipeline/engine.py` and `website/app.py`:
  * Accept both raw text payloads and structured multi-format documents.
  * Update `website/script.js` to eliminate unsafe `readAsText()` on binary files.
  * Eliminate misleading client-side mock scoring on backend failure.

### Step 3.5: Comprehensive Phase 3 Test Suite
- Author `tests/test_phase_3_ingestion.py`:
  * Tabular CSV extraction tests.
  * Columnar text report extraction tests.
  * Unit normalization and alias mapping tests.
  * Unsupported format rejection tests.
  * Provenance and original-value preservation tests.

---

## 9. Identified Risks & Blockers

1. **Missing Binary PDF / OCR Dependencies**:
   - The environment currently lacks libraries for PDF parsing (`pypdf`/`pdfminer`) and OCR (`pytesseract`).
   - *Mitigation*: Architect the extraction layer with graceful fallbacks. If binary PDF or image is uploaded and underlying extraction libraries are not present in the runtime, halt with explicit structured error: `UNSUPPORTED_FORMAT: PDF/OCR extraction engine not available in environment`, rather than crashing or pasting corrupt bytes.
2. **Ambiguous Column Headers in CSVs**:
   - Different laboratory exports use varying header names (`Test`, `Analytic`, `Description`, `Result`, `Value`, `Units`).
   - *Mitigation*: Implement dictionary-based header classification with confidence scoring.
3. **Preservation of Phase 2 Baselines**:
   - All improvements to parsing and ingestion must maintain 100% backward compatibility with `DiagnosticEngine.analyze_report()` and pass all 42 Phase 2 canonical tests.

---

## 10. Audit Sign-off

- **Current Architecture Status**: Inspected and verified.
- **Phase 2 Regression Status**: **42 / 42 PASS**, Schema Validator **PASS**.
- **Implementation Status**: **AUDIT COMPLETE — READY FOR PHASE 3 ARCHITECTURE REVIEW**. Zero application source files were modified during this audit.
