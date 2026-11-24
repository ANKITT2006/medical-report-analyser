# MEDIPULSE AI — PHASE 3.3 FINAL TECHNICAL AUDIT REPORT
## INDEPENDENT VERIFICATION OF DETERMINISTIC UNIT NORMALIZATION & BIOMARKER MAPPING

**Date**: 2026-11-24  
**Project Root**: `C:\Users\Ankit's_YOGA\Desktop\report_analyser\medical-report-analyser\`  
**Current Phase**: Phase 3 — Ingestion & Normalization Pipeline  
**Subphase Audited**: 3.3 — Deterministic Unit Normalization & Canonical Biomarker Mapping  
**Auditor**: Antigravity Clinical AI Engineering Agent  

---

## 1. FILES & DATABASE TABLES INSPECTED

### Files Inspected
- `clinical_engine/pipeline/normalizer.py` (Biomarker resolver, lexical normalizer, observation normalizer)
- `clinical_engine/pipeline/converters.py` (Allowlisted conversion handlers, registry)
- `clinical_engine/pipeline/selector.py` (Clinical reference interval and critical limit selector)
- `clinical_engine/pipeline/engine.py` (Diagnostic engine)
- `clinical_engine/domain/schemas.py` (Ingestion contracts, Pydantic and dataclass models)
- `clinical_engine/storage/repository.py` (SQL clinical repository)
- `tests/test_phase_3_normalization.py` (Normalization unit tests)
- `tests/test_canonical_phase_2.py` (Phase 2 canonical clinical evaluation tests)
- `scripts/validate_phase_2.py` (Canonical JSON schema validator)

### Actual SQLite Database Tables Inspected (`data/clinical_knowledge.db`)
1. **`lab_metrics`** (20 rows) — Primary definition of canonical biomarkers, standard units, LOINC codes.
2. **`metric_aliases`** (83 rows) — Canonical biomarker alias mappings.
3. **`metric_unit_conversions`** (21 rows) — Explicit allowlisted metric-specific unit conversions.
4. `metric_reference_intervals` (26 rows)
5. `metric_critical_limits` (12 rows)
6. `metric_diagnostic_thresholds` (22 rows)
7. `metric_treatment_targets` (9 rows)
8. `metric_risk_thresholds` (28 rows)
9. `metric_clinical_context` (20 rows)
10. `clinical_protocols` (4 rows)
11. `condition_metric_mappings` (8 rows)

> [!NOTE]  
> **Table Name Resolution**: The actual table name in `data/clinical_knowledge.db` is **`metric_aliases`** (not `lab_metric_aliases`). Earlier documentation informally referred to `lab_metric_aliases`; this audit confirms `metric_aliases` is the authoritative table used by `SQLClinicalRepository` and `CanonicalBiomarkerResolver`.

---

## 2. DATABASE SCHEMA AND ALIAS RESOLUTION AUDIT

### SQL Queries Executed by `CanonicalBiomarkerResolver`
1. **Direct Match Query**:
   ```sql
   SELECT metric_id, canonical_name, standard_unit, loinc_code, category
   FROM lab_metrics
   WHERE LOWER(metric_id) = ? OR LOWER(canonical_name) = ? OR LOWER(loinc_code) = ?
   ```
2. **Alias Match Query**:
   ```sql
   SELECT m.metric_id, m.canonical_name, m.standard_unit, m.loinc_code, m.category
   FROM metric_aliases a
   JOIN lab_metrics m ON a.metric_id = m.metric_id
   WHERE LOWER(a.alias) = ?
   ```

### Resolution Logic & Safety Evaluation
- **Normalization of Query**: Cleans leading bullets, hyphens, and numbered list artifacts (`1. Hemoglobin`), collapses multiple whitespace characters, and normalizes to lower case. Crucially, hyphenated LOINC codes (e.g., `1558-6`, `718-7`) match `^\d+-\d+$` and are preserved without numeric prefix stripping.
- **Ambiguity & Multi-Match Handling**: Matches across direct and alias queries are collected and deduplicated by `metric_id`.
  - **Exactly 1 match**: Returns `(metric_dict, BiomarkerResolutionStatus.RESOLVED, None)`.
  - **0 matches**: Returns `(None, BiomarkerResolutionStatus.UNKNOWN, "Unrecognized biomarker label...")`.
  - **> 1 distinct matches**: Returns `(None, BiomarkerResolutionStatus.AMBIGUOUS, "Ambiguous biomarker label: matches multiple canonical metrics...")`.
  - **Arbitrary Selection**: **Zero**. If multiple metrics match, execution halts with `BiomarkerResolutionStatus.AMBIGUOUS`; it never picks the first matching row.
  - **Strict Status Decoupling**: The resolver **never assigns `IngestionStatus.VALID`**. Only `ObservationNormalizer` assigns final `IngestionStatus.VALID` after all downstream value, unit presence, compatibility, and mathematical conversion validations pass.

### Alias Resolution Audit Table
| Input Raw Label | Query Normalization | Resolution Match | BiomarkerResolutionStatus | Metric ID Assigned | Verified In Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `hemoglobin` | `hemoglobin` | Exact metric_id | `RESOLVED` | `hemoglobin` | `test_canonical_metric_id_direct_lookup` |
| `Total Cholesterol` | `total cholesterol` | Exact canonical_name | `RESOLVED` | `cholesterol_total` | `test_canonical_name_direct_lookup` |
| `1558-6` | `1558-6` | Exact loinc_code | `RESOLVED` | `glucose_fasting` | `test_loinc_code_direct_lookup` |
| `Hb` | `hb` | Registered alias | `RESOLVED` | `hemoglobin` | `test_registered_alias_resolution` |
| `   hEmOGLoBiN   ` | `hemoglobin` | Casing/whitespace | `RESOLVED` | `hemoglobin` | `test_case_and_whitespace_insensitivity` |
| `Unknown Lab XYZ` | `unknown lab xyz` | Zero matches | `UNKNOWN` | `None` | `test_unknown_biomarker_handling` |
| `""` / `"   "` | Empty string | Empty input guard | `UNKNOWN` | `None` | `test_empty_or_whitespace_label_handling` |

---

## 3. UNIT LEXICAL NORMALIZATION AUDIT

### Analysis of Requested Specific Unit Mappings
| Original Token | Normalized Token | Lexical Equivalence Rationale | Safety Assessment | Verified By Test |
| :--- | :--- | :--- | :--- | :--- |
| `cells/uL` | `/uL` | Laboratory convention: cell counts in whole blood are expressed per microliter (`/uL`). `cells` denotes the entity counted. | **Safe**: Matches standard unit in `lab_metrics` for `wbc` and `platelets`. | `test_cell_count_lexical_variants` |
| `/uL` | `/uL` | Identity mapping to canonical token. | **Safe**: Direct canonical token. | `test_cell_count_lexical_variants` |
| `k/uL` | `x10^3/uL` | Metric prefix abbreviation: `k` (kilo) equals $10^3$ ($1,000$). Standardized to scientific multiplier notation. | **Safe**: Maps to `x10^3/uL` which has an allowlisted linear conversion ($1,000\times$) to `/uL`. | `test_cell_count_k_ul_conversion` |
| `x10^3/uL` | `x10^3/uL` | Identity mapping to canonical scientific token. | **Safe**: Direct canonical token. | `test_cell_count_k_ul_conversion` |
| `mg/dL` | `mg/dL` | Canonical mass concentration token. | **Safe**: Standard unit for lipids, glucose, creatinine, etc. | `test_approved_casing_variations` |
| `mg/dl` | `mg/dL` | Typographic casing variation for deciliter (`dl` -> `dL`). | **Safe**: SI casing normalization. | `test_approved_casing_variations` |
| `mg / dL` | `mg/dL` | Spacing variation around solidus. | **Safe**: Whitespace artifact removal. | `test_harmless_whitespace_variations` |
| `g/dL` | `g/dL` | Canonical mass concentration token for hemoglobin. | **Safe**: Direct standard unit for hemoglobin. | `test_approved_casing_variations` |
| `gm/dL` | `g/dL` | Deprecated abbreviation `gm` for gram (`g`). | **Safe**: Standard SI normalization. | `test_approved_casing_variations` |
| `mmol/L` | `mmol/L` | Canonical molar concentration token. | **Safe**: Molar unit preserved; strictly NOT aliased to mass units. | `test_approved_casing_variations` |
| `umol/L` | `umol/L` | Micro-molar concentration ASCII representation. | **Safe**: Canonical molar unit. | `test_unicode_micro_symbol_variations` |
| `µmol/L` | `umol/L` | Unicode micro symbol (U+00B5 `µ`) normalized to ASCII `u`. | **Safe**: Canonical character normalization. | `test_unicode_micro_symbol_variations` |
| `μmol/L` | `umol/L` | Greek small letter mu (U+03BC `μ`) normalized to ASCII `u`. | **Safe**: Canonical character normalization. | `test_unicode_micro_symbol_variations` |
| `mL/min/1.73m2` | `mL/min/1.73m^2` | Missing exponent caret in eGFR denominator. | **Safe**: Lexical normalization of body surface area. | `test_egfr_body_surface_area_variants` |
| `mL/min/1.73m^2` | `mL/min/1.73m^2` | Identity mapping for eGFR standardized filtration rate. | **Safe**: Direct standard unit for eGFR. | `test_egfr_body_surface_area_variants` |

### Critical Safety Checks in Unit Lexical Normalization
1. **Mathematically Different Units Never Aliased**: `mmol/L` and `mg/dL` are distinct lexical tokens. `UnitLexicalNormalizer` produces distinct keys and never maps molar units to mass units.
2. **SI Casing Preservation**: Micro (`u`/`µ`), milli (`m`), kilo (`k`), and Mega (`M`) are strictly guarded. In cell counting, `M/uL` ($10^6/\mu\text{L}$ for RBC) is distinct from `m/uL` or `k/uL`.
3. **No Silent Unsupported Unit Coercion**: Any unit token not present in the controlled dictionary returns `(None, error_msg)` and is flagged as `IngestionStatus.UNSUPPORTED_UNIT`.

---

## 4. MATHEMATICAL CONVERSIONS & ALLOWLIST VERIFICATION

### Database Conversion Evidence (`metric_unit_conversions`)
| Metric ID | Input Unit | Standard Unit | DB Factor | Canonical Formula | Approved Handler | Verified Output |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cholesterol_total` | `mmol/L` | `mg/dL` | `38.67` | `mg/dL = mmol/L * 38.67` | `LINEAR_SCALE` | $5.0 \times 38.67 = 193.35\text{ mg/dL}$ |
| `glucose_fasting` | `mmol/L` | `mg/dL` | `18.0182` | `mg/dL = mmol/L * 18.0182` | `LINEAR_SCALE` | $5.0 \times 18.0182 = 90.091\text{ mg/dL}$ (round 2: $90.09$) |
| `glucose_random` | `mmol/L` | `mg/dL` | `18.0182` | `mg/dL = mmol/L * 18.0182` | `LINEAR_SCALE` | $10.0 \times 18.0182 = 180.182\text{ mg/dL}$ |
| `hba1c` | `mmol/mol` | `%` | `0.09148` | `NGSP % = (0.09148 * IFCC) + 2.152` | `HBA1C_IFCC_TO_NGSP` | $53\text{ IFCC} \rightarrow 7.00044 \rightarrow 7.0\text{ \%}$ |
| `platelets` | `x10^3/uL` | `/uL` | `1000.0` | `/uL = (x10^3/uL) * 1000` | `LINEAR_SCALE` | $250 \times 1000 = 250,000\text{ /uL}$ |
| `wbc` | `x10^3/uL` | `/uL` | `1000.0` | `/uL = (x10^3/uL) * 1000` | `LINEAR_SCALE` | $7.5 \times 1000 = 7,500\text{ /uL}$ |

### Independence of Biomarker Conversion Factors
- **Total Cholesterol** molecular weight factor: $38.67\text{ mg/dL per mmol/L}$ (based on cholesterol MW $\approx 386.65\text{ g/mol}$).
- **Glucose** molecular weight factor: $18.0182\text{ mg/dL per mmol/L}$ (based on glucose MW $\approx 180.16\text{ g/mol}$).
- **Audit Confirmation**: Total Cholesterol and Glucose **do not share** a generic conversion factor. Each conversion is queried strictly by exact case-sensitive matching: `WHERE metric_id = ? AND alternative_unit = ?`.

### Code Security: Zero `eval()` / `exec()`
Static search of all conversion and clinical engine pipelines:
- `clinical_engine/pipeline/converters.py`: **0** occurrences of `eval` or `exec`.
- `clinical_engine/pipeline/normalizer.py`: **0** occurrences of `eval` or `exec`.
- `clinical_engine/pipeline/selector.py`: **0** occurrences of `eval` or `exec`.
- `clinical_engine/pipeline/engine.py`: **0** occurrences of `eval` or `exec`.

All conversions dispatch strictly via `ALLOWED_CONVERSION_HANDLERS[handler_name]`.

---

## 5. VALUE, UNIT & PROVENANCE PRESERVATION AUDIT

Every `NormalizedObservation` preserves verbatim original observation fields:
- `raw_label`: Verbatim label extracted by parser (e.g. `"  Total Cholesterol  "`).
- `original_value_text`: Verbatim string representation from source document (e.g. `"  5.00  "`).
- `original_detected_value`: Float parsed by extractor (e.g. `5.0`).
- `original_unit`: Verbatim unit string (e.g. `"  mmol/l  "`).
- `source_document_id`: Preserved unaltered.
- `source_location`: Structured `SourceLocation` (page, line, row, column offsets) preserved.
- `normalized_value`: Stored separately (e.g. `193.35`).
- `normalized_unit`: Stored separately (e.g. `"mg/dL"`).
- `conversion_audit`: Structured `ConversionAudit` containing `original_value`, `original_unit`, `converted_value`, `standard_unit`, `conversion_type`, `formula_used`, and `handler_executed`.

### Missing Units & Unsupported Units Safety
- When incoming unit is `None` or whitespace for a unit-dependent metric: `ingestion_status = IngestionStatus.MISSING_UNIT`. No default unit is assumed; `normalized_value` is set to `None`.
- When incoming unit is incompatible (e.g. `"kg/m^2"` for Cholesterol): `ingestion_status = IngestionStatus.UNSUPPORTED_UNIT`. No conversion is attempted; `normalized_value` is set to `None`.

---

## 6. NON-NUMERIC AND QUALIFIED RESULTS AUDIT

| Raw Value Text | ParsingStatus | Detected Value | IngestionStatus Assigned | Normalized Value | Mathematical Conversion |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Negative` | `NON_NUMERIC_RESULT` | `None` | `NON_NUMERIC_RESULT` | `None` | **Skipped** |
| `Positive` | `NON_NUMERIC_RESULT` | `None` | `NON_NUMERIC_RESULT` | `None` | **Skipped** |
| `Trace` | `NON_NUMERIC_RESULT` | `None` | `NON_NUMERIC_RESULT` | `None` | **Skipped** |
| `<0.01` | `NON_NUMERIC_RESULT` | `None` | `NON_NUMERIC_RESULT` | `None` | **Skipped** |
| `>100` | `NON_NUMERIC_RESULT` | `None` | `NON_NUMERIC_RESULT` | `None` | **Skipped** |
| `3+` | `NON_NUMERIC_RESULT` | `None` | `NON_NUMERIC_RESULT` | `None` | **Skipped** |

**Audit Finding**: Zero non-numeric or inequality-qualified strings are coerced to numeric floats or passed into mathematical functions. They are preserved uncoerced as `original_value_text` with `normalized_value = None`.

---

## 7. CLINICAL ENGINE SEPARATION AUDIT

Inspection of `clinical_engine/pipeline/normalizer.py` and `clinical_engine/domain/schemas.py`:
- `NormalizedObservation` contains **no clinical evaluation attributes**:
  - No `severity`
  - No `status` / `metric_status`
  - No `is_abnormal` / `is_critical`
  - No `reference_interval`
  - No `diagnostic_status`
  - No `clinical_findings`
  - No `risk_score` / `treatment_recommendations`
- Reference interval matching and clinical evaluation occur exclusively in Phase 2 `DeterministicClinicalSelector` and `DiagnosticEngine`.
- Only records with `ingestion_status == IngestionStatus.VALID` can be evaluated clinically.

---

## 8. REGRESSION TESTING & VERIFICATION RESULTS

### 8.1 Full Test Suite Discovery (`python -m unittest discover -v tests`)
- **Total Tests Executed**: **142** (125 baseline tests + 15 Phase 3.3 integrity/case-sensitivity tests + 2 legacy engine unit-safety tests)
- **Test Failures**: **0**
- **Test Errors**: **0**
- **Exit Code**: **0**

#### Breakdown of Executed Test Suites:
1. `tests/test_canonical_phase_2.py`: **38 tests** (36 Phase 2 canonical reference/clinical tests + 2 legacy engine SI unit-safety tests) — **PASS**
2. `tests/test_clinical_engine.py`: **6 tests** (Core clinical engine evaluations) — **PASS**
3. `tests/test_phase_3_contracts.py`: **16 tests** (Phase 3 domain contracts, validation rules, SourceLocation, format safety) — **PASS**
4. `tests/test_phase_3_extractors.py`: **39 tests** (All text and tabular extraction strategies, diagnostics, layout parsers) — **PASS**
5. `tests/test_phase_3_normalization.py`: **43 tests** (28 baseline tests across Categories A–G + 15 focused integrity & case-sensitivity tests in `TestIngestionStatusIntegrity`) — **PASS**

### 8.2 Canonical Reference & Schema Validator (`python scripts/validate_phase_2.py`)
```
======================================================================
  VALIDATION SUMMARY
======================================================================
Total Canonical Biomarkers Cataloged : 20 / 20
Total Unique LOINC Codes (LOINC 2.83): 20 / 20
Total Reference Intervals Validated  : 26
Total Diagnostic Cutoffs Validated   : 22
Total Critical Limits Validated      : 12
Total Treatment Targets Documented   : 9
Total Risk Classification Tiers      : 28
Total Errors Found                   : 0
Total Warnings                       : 0

[VALIDATION SUCCESS] All Draft 2020-12 schemas, reference data instances,
                     metadata, and clinical governance constraints PASSED cleanly.
Exiting with status code 0.
```

---

## 9. INGESTION STATUS INTEGRITY & RESOLUTION SEPARATION AUDIT

### 9.1 Core Invariant
Only a fully normalized, validated numeric observation may have:
```python
ingestion_status == IngestionStatus.VALID
```
A successful biomarker alias match alone **never** confers `IngestionStatus.VALID` or clinical eligibility.

### 9.2 Architecture Refactoring: `BiomarkerResolutionStatus`
To strictly decouple internal biomarker resolution from final observation validity:
- Introduced `BiomarkerResolutionStatus(str, Enum)` with states `RESOLVED`, `UNKNOWN`, and `AMBIGUOUS`.
- `CanonicalBiomarkerResolver.resolve()` returns `(canonical_dict, BiomarkerResolutionStatus, explanation)`.
- Internal biomarker resolution never outputs `IngestionStatus.VALID`.
- `ObservationNormalizer` maps intermediate resolution states:
  - `BiomarkerResolutionStatus.AMBIGUOUS` $\rightarrow$ `IngestionStatus.AMBIGUOUS_BIOMARKER`
  - `BiomarkerResolutionStatus.UNKNOWN` $\rightarrow$ `IngestionStatus.UNKNOWN_BIOMARKER`
  - `BiomarkerResolutionStatus.RESOLVED` permits the pipeline to proceed to steps 2–7 (value check, unit presence, lexical normalization, compatibility, mathematical conversion).

### 9.3 Verification of Required Test Cases (`TestIngestionStatusIntegrity`)
The `TestIngestionStatusIntegrity` class in `tests/test_phase_3_normalization.py` contains **11 executed test methods**:
- **9 Scenario-Specific Tests**:
  1. `test_case_1_known_biomarker_valid_canonical_unit_is_valid` (Known biomarker + canonical unit $\rightarrow$ `VALID`)
  2. `test_case_2_known_biomarker_alias_supported_unit_valid_after_conversion` (Known biomarker + alias + alternative unit $\rightarrow$ `VALID` only post-conversion)
  3. `test_case_3_known_biomarker_missing_required_unit_is_missing_unit` (Known biomarker + missing unit $\rightarrow$ `MISSING_UNIT`)
  4. `test_case_4_known_biomarker_unsupported_unit_is_unsupported_unit` (Known biomarker + unsupported unit $\rightarrow$ `UNSUPPORTED_UNIT`)
  5. `test_case_5_unknown_biomarker_is_unknown_biomarker` (Unknown biomarker $\rightarrow$ `UNKNOWN_BIOMARKER`)
  6. `test_case_6_ambiguous_biomarker_is_ambiguous_biomarker` (Ambiguous biomarker $\rightarrow$ `AMBIGUOUS_BIOMARKER`)
  7. `test_case_7_qualitative_result_is_non_numeric_result` (Qualitative / inequality result $\rightarrow$ `NON_NUMERIC_RESULT`)
  8. `test_case_8_failed_conversion_is_conversion_failed` (Failed mathematical conversion $\rightarrow$ `CONVERSION_FAILED`)
  9. `test_case_9_missing_numeric_value_is_missing_value` (Missing numeric value text $\rightarrow$ `MISSING_VALUE`)
- **2 Invariant & SI Sensitivity Tests**:
  10. `test_resolution_success_alone_does_not_make_observation_valid` (Explicit invariant test: successful resolution + missing value, missing unit, or unsupported unit never produces `VALID`)
  11. `test_si_prefix_and_case_sensitivity` (Prefix sensitivity test: `M/uL`, `x10^3/uL`, and `/uL` are strictly non-identical, distinct tokens; cross-biomarker unit collisions are rejected)

| Test Method | Input Scenario | Assigned IngestionStatus | Clinical Ineligibility Enforced |
| :--- | :--- | :--- | :--- |
| `test_case_1_known_biomarker_valid_canonical_unit_is_valid` | Known biomarker + valid canonical unit | `VALID` | Eligible for Phase 2 |
| `test_case_2_known_biomarker_alias_supported_unit_valid_after_conversion` | Known biomarker + alias + alternative unit | `VALID` | Eligible only after conversion |
| `test_case_3_known_biomarker_missing_required_unit_is_missing_unit` | Known biomarker + missing required unit | `MISSING_UNIT` | Ineligible (cannot presume unit) |
| `test_case_4_known_biomarker_unsupported_unit_is_unsupported_unit` | Known biomarker + unsupported unit | `UNSUPPORTED_UNIT` | Ineligible (no conversion pathway) |
| `test_case_5_unknown_biomarker_is_unknown_biomarker` | Unknown biomarker | `UNKNOWN_BIOMARKER` | Ineligible (unregistered biomarker) |
| `test_case_6_ambiguous_biomarker_is_ambiguous_biomarker` | Ambiguous biomarker | `AMBIGUOUS_BIOMARKER` | Ineligible (unresolved collision) |
| `test_case_7_qualitative_result_is_non_numeric_result` | Qualitative / inequality result | `NON_NUMERIC_RESULT` | Ineligible for numeric intervals |
| `test_case_8_failed_conversion_is_conversion_failed` | Failed mathematical conversion | `CONVERSION_FAILED` | Ineligible (runtime calculation error) |
| `test_case_9_missing_numeric_value_is_missing_value` | Missing numeric value text | `MISSING_VALUE` | Ineligible (empty result text) |
| `test_resolution_success_alone_does_not_make_observation_valid` | Resolved biomarker + invalid downstream data | `MISSING_UNIT`, `MISSING_VALUE`, `UNSUPPORTED_UNIT` | Invariant verified |
| `test_si_prefix_and_case_sensitivity` | Prefix-sensitive units (`M/uL` vs `k/uL` vs `/uL`) | `UNSUPPORTED_UNIT` on mismatch | Case sensitivity verified |

---

## 10. SQL UNIT CASE-SENSITIVITY AUDIT

### 10.1 Exact SQL Queries Inspected
1. **`clinical_engine/pipeline/normalizer.py` (`ObservationNormalizer.normalize_observation`)**:
   - **Before**: `WHERE metric_id = ? AND LOWER(alternative_unit) = ?` with `cursor.fetchone()`.
   - **After**:
     ```sql
     SELECT conversion_id, alternative_unit, standard_unit, conversion_type,
            conversion_factor, canonical_conversion_formula, handler_function_name
     FROM metric_unit_conversions
     WHERE metric_id = ? AND alternative_unit = ?
     ```
     with `cursor.fetchall()` and explicit ambiguity guard (`if len(conv_rows) > 1` $\rightarrow$ `IngestionStatus.CONVERSION_FAILED`).
2. **`clinical_engine/storage/repository.py` (`SQLClinicalRepository.get_unit_conversion`)**:
   - **Before**: `WHERE metric_id = ? AND LOWER(alternative_unit) = LOWER(?)` with `cursor.fetchone()`.
   - **After**:
     ```sql
     SELECT * FROM metric_unit_conversions
     WHERE metric_id = ? AND alternative_unit = ?
     ```
     with `cursor.fetchall()` and exact uniqueness check (`if len(rows) != 1: return None`).
3. **`clinical_engine/pipeline/converters.py` (`convert_laboratory_value`)**:
   - **Before**: `if incoming_unit.strip().lower() == standard_unit.strip().lower():`
   - **After**: `if incoming_unit.strip() == standard_unit.strip():`

### 10.2 Actual Database Unit Records (`data/clinical_knowledge.db`)
Inspection of `metric_unit_conversions` (21 rows) and `lab_metrics` (20 rows):
- **`M/uL`**: Exists in `lab_metrics` as `standard_unit` for `rbc`. Not present as an `alternative_unit` in `metric_unit_conversions`.
- **`m/uL`**: Does **not** exist anywhere in `data/clinical_knowledge.db`.
- **`k/uL`**: Does **not** exist in `data/clinical_knowledge.db`; `UnitLexicalNormalizer` maps `k/uL` $\rightarrow$ `x10^3/uL` while preserving `original_unit = "k/uL"`.
- **`x10^3/uL`**: Exists in `metric_unit_conversions` for `wbc` and `platelets` (`x10^3/uL` $\rightarrow$ `/uL`, factor `1000.0`, `LINEAR_SCALE`).
- **`/uL`**: Exists in `lab_metrics` as `standard_unit` for `wbc` and `platelets`.
- **Case-Distinct Collision Check**: Production `data/clinical_knowledge.db` currently contains **0** case-distinct `alternative_unit` pairs on the same `metric_id`.

### 10.3 Before-and-After Matching Behavior
- **Before**: `UnitLexicalNormalizer.normalize_unit()` blindly lowercased `"m/uL"` and `"M/uL"` to `"m/ul"`, collapsing both to `"M/uL"`. Additionally, `repository.get_unit_conversion()` used `LOWER(alternative_unit) = LOWER(?)` with `fetchone()`, risking arbitrary selection if case-distinct records existed.
- **After**:
  - `UnitLexicalNormalizer.CASE_SENSITIVE_UNIT_MAP` checks exact case for SI-prefix-sensitive tokens (`"M/uL"`, `"M / uL"`, `"M/mcL"`, `"M/µL"`, `"M/μL"`) before any lowercased lookup, and `"m/ul"` was removed from `CONTROLLED_UNIT_MAP`. Thus `"M/uL"` $\rightarrow$ `"M/uL"` while `"m/uL"` returns `(None, error)` (`UNSUPPORTED_UNIT`).
  - Both `normalizer.py` and `repository.py` execute exact case-sensitive SQL lookups (`WHERE metric_id = ? AND alternative_unit = ?`) and refuse to return an arbitrary row if multiple rows match.

### 10.4 Case-Sensitivity Test Results & Files Modified
- **New Focused Tests in `tests/test_phase_3_normalization.py`**:
  - `test_m_ul_and_lowercase_m_ul_never_collide`: Proves `M/uL` and `m/uL` never resolve to the same token and `m/uL` is rejected as `UNSUPPORTED_UNIT`.
  - `test_k_ul_and_x10_3_ul_distinct_until_conversion`: Proves `k/uL` preserves `original_unit="k/uL"` and applies the explicit `1000.0` `LINEAR_SCALE` conversion to `/uL`.
  - `test_isolated_case_distinct_sql_conversion_records_do_not_collide`: Uses an isolated temporary SQLite database containing both `'M/uL'` (`1000000.0`) and `'m/uL'` (`0.001`) for `test_cell` without modifying production data; confirms exact case lookup returns the exact matching factor and `'m/UL'` returns `None`.
  - `test_existing_core_conversions_remain_correct`: Confirms glucose (`18.0182`), cholesterol (`38.67`), HbA1c (`HBA1C_IFCC_TO_NGSP`), WBC (`1000.0`), and platelets (`1000.0`) remain exact.
- **Files Modified**:
  - `clinical_engine/pipeline/normalizer.py`
  - `clinical_engine/storage/repository.py`
  - `clinical_engine/pipeline/converters.py`
  - `clinical_engine/pipeline/engine.py`
  - `tests/test_phase_3_normalization.py`
  - `tests/test_canonical_phase_2.py`
  - `reports/phase_3_3_final_audit_report.md`

### 10.5 Legacy `DiagnosticEngine` Unit-Safety Correction (`clinical_engine/pipeline/engine.py`)
- **Issue Identified**: `DiagnosticEngine.evaluate_finding()` previously checked `raw_unit.strip().lower() != standard_unit.strip().lower()`, which could bypass unit validation/conversion when an SI-prefix-sensitive unit differed only by case (e.g., `m/uL` vs `M/uL` for RBC).
- **Correction**: Replaced the broad `.lower()` comparison with controlled `UnitLexicalNormalizer.normalize_unit(raw_unit)` resolution followed by exact case-sensitive comparison (`effective_unit != standard_unit.strip()`), and passed `effective_unit` into `repository.get_unit_conversion()` and `convert_laboratory_value()`.
- **Regression Tests Added (`tests/test_canonical_phase_2.py`)**:
  - `test_legacy_engine_rbc_standard_unit_M_ul_valid`: Verifies `RBC: 5.0 M/uL` follows the valid standard-unit path (`MetricStatus.NORMAL`).
  - `test_legacy_engine_rbc_lowercase_m_ul_rejected_as_unsupported`: Verifies `RBC: 5.0 m/uL` is rejected as `MetricStatus.INCONCLUSIVE` (`Unsupported unit 'm/uL'`) and is never evaluated clinically.

### 10.6 Remaining Limitations
- Phase 3.4 (PDF & OCR document ingestion) is not yet implemented.

---

## 11. CONCLUSION & UNRESOLVED DEFECTS

- **Unresolved Defects**: **0**.
- **Status Integrity & Unit Case-Sensitivity Guaranteed**: `IngestionStatus.VALID` strictly represents complete end-to-end normalization, and SI prefix case sensitivity is preserved across both `UnitLexicalNormalizer` and SQLite conversion lookups.
- **Compliance with Restrictions**:
  - No canonical clinical datasets or conversion factors modified.
  - No clinical thresholds altered.
  - No frontend/backend routes modified.
  - No dependencies installed.
  - No Git workflows modified.
  - Phase 3.4 not initiated.
