"""
Clinical Report Ingestion & Feature Extraction Parser.
Multi-strategy extraction layer supporting:
1. Delimited text (colon, equals, hyphen).
2. Columnar / whitespace-separated tables.
3. CSV & TSV structured formats (comma, semicolon, tab).
4. Unambiguous multiline label/value pairs.

Strictly preserves backward compatibility with ClinicalReportParser.parse_text() -> List[ParsedObservation].
New extraction pipelines return List[RawObservation] per Phase 3.1 domain contracts.
No diagnostic or clinical interpretation is performed in this layer.
"""

import csv
import io
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from clinical_engine.domain.schemas import (
    RawObservation,
    ExtractionDiagnostic,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    ParsingStatus,
    DocumentFormat,
)

# =============================================================================
# BACKWARD COMPATIBLE LEGACY STRUCTURE
# =============================================================================

@dataclass
class ParsedObservation:
    raw_key: str
    detected_value: Optional[float]
    raw_unit: Optional[str]
    line_number: int
    is_inconclusive: bool = False
    inconclusive_reason: Optional[str] = None


# =============================================================================
# EXTRACTION HELPERS & GUARD RULES
# =============================================================================

# Known units in laboratory medicine to avoid capturing reference range text or noise
KNOWN_UNITS_SET = {
    "g/dl", "mg/dl", "ug/dl", "mmol/l", "umol/l", "µmol/l", "nmol/l", "pmol/l",
    "%", "cells/ul", "cells/mcl", "/ul", "/mcl", "m/ul", "k/ul", "10^3/ul", "10^6/ul",
    "fl", "pg", "u/l", "iu/l", "meq/l", "ml/min", "ml/min/1.73m2", "mg/g", "ug/g",
    "ng/ml", "pg/ml", "ug/ml", "mg/l", "g/l", "mmol/mol", "ratio", "sec", "seconds"
}

# Regex for common dates to avoid misinterpreting them as lab values
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4}|\d{4}[-\/\.]\d{1,2}[-\/\.]\d{1,2})\b"
)

# Regex for metadata labels that should never be extracted as biomarkers
METADATA_LABELS_PATTERN = re.compile(
    r"^(?:patient\s*id|patient\s*name|mrn|dob|date\s*of\s*birth|collection\s*date|collected\s*date|order\s*id|accession|specimen|collected|reported|report\s*status|doctor|physician|hospital|clinic|page|note|notes|comment|comments|impression|interpretation)\b",
    re.IGNORECASE
)

# Regex to detect reference interval patterns like "12.0 - 15.5", "70-99", "< 200", "> 60"
REF_RANGE_PATTERN = re.compile(
    r"^[\[\(]?\s*(?:[<>]|<=|>=)?\s*[+\-]?[0-9]+(?:\.[0-9]+)?\s*(?:-|–|—|to)\s*[+\-]?[0-9]+(?:\.[0-9]+)?\s*[\]\)]?$",
    re.IGNORECASE
)


def clean_label(text: str) -> str:
    """Strips bullets, numbering, asterisks, and whitespace from label text."""
    t = re.sub(r"^[\*\-\•\d\.\s]+", "", text).strip()
    return re.sub(r"[\*:]+$", "", t).strip()


def parse_numeric_and_unit(val_str: str) -> Tuple[Optional[float], str, Optional[str], ParsingStatus]:
    """
    Parses value string into (detected_float, raw_value_text, raw_unit, parsing_status).
    Preserves inequality qualifiers (<, >) and qualitative texts as NON_NUMERIC_RESULT.
    """
    cleaned_val = val_str.strip()
    if not cleaned_val:
        return None, "", None, ParsingStatus.MISSING_VALUE

    # Check for inequality qualifier (e.g. "< 0.05", ">= 126", ">450")
    if re.match(r"^[<>]=?\s*[0-9]", cleaned_val):
        # Qualified numeric: do not invent exact value, mark NON_NUMERIC_RESULT
        parts = cleaned_val.split(None, 1)
        val_text = parts[0]
        unit = parts[1] if len(parts) > 1 else None
        return None, cleaned_val, unit, ParsingStatus.NON_NUMERIC_RESULT

    # Extract leading number (supports comma thousand separator and decimal)
    num_match = re.match(r"^([+\-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)(?:\s*(.*))?$", cleaned_val)
    if num_match:
        num_str = num_match.group(1).replace(",", "")
        trailing = num_match.group(2).strip() if num_match.group(2) else None
        try:
            val = float(num_str)
            return val, num_match.group(1), trailing, ParsingStatus.PARSED
        except ValueError:
            pass

    # Pure qualitative string (e.g. "Trace", "Negative", "Reactive")
    return None, cleaned_val, None, ParsingStatus.NON_NUMERIC_RESULT


# =============================================================================
# STRATEGY 1: DELIMITED TEXT STRATEGY
# =============================================================================

class DelimitedTextStrategy:
    """
    Extracts laboratory observations from key-value text lines delimited by ':', '=', or '-'.
    Supports integers, floats, comma separators, qualitative results, and trailing units.
    Avoids reference ranges, dates, and non-biomarker metadata.
    """

    DELIMITED_PATTERN = re.compile(
        r"^(?P<label>[A-Za-z0-9_\s\(\)\/\-\.]{2,40}?)\s*[:=\-]\s*(?P<rest>.+)$"
    )

    @classmethod
    def extract_result(cls, report_text: str) -> ExtractionResult:
        """Extracts observations and diagnostics into a strongly typed ExtractionResult."""
        if not report_text or not report_text.strip():
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=DocumentFormat.PLAIN_TEXT
            )

        observations: List[RawObservation] = []
        diagnostics: List[ExtractionDiagnostic] = []

        lines = report_text.splitlines()
        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("//"):
                continue

            # Skip lines matching date patterns only or metadata header fields
            if METADATA_LABELS_PATTERN.match(line_str):
                continue

            match = cls.DELIMITED_PATTERN.match(line_str)
            if not match:
                continue

            raw_lbl = clean_label(match.group("label"))
            if not raw_lbl or len(raw_lbl) < 2 or METADATA_LABELS_PATTERN.match(raw_lbl):
                continue

            rest = match.group("rest").strip()

            # Separate value/unit from any trailing reference range (e.g. "13.5 g/dL (12.0 - 15.5)")
            ref_split = re.split(r"[\(\[\{]\s*(?:ref|reference|normal|\d)", rest, maxsplit=1, flags=re.IGNORECASE)
            main_part = ref_split[0].strip()

            # Dissect main_part into value token and unit token
            # Match qualified number, standard number, or qualitative text
            if re.match(r"^[<>=]", main_part) or re.match(r"^[+\-]?[0-9]", main_part):
                val_token_match = re.match(
                    r"^([+\-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[<>]=?\s*[0-9]+(?:\.[0-9]+)?)\s*(.*)$",
                    main_part
                )
                if not val_token_match:
                    continue
                val_str = val_token_match.group(1).strip()
                unit_str = val_token_match.group(2).strip() if val_token_match.group(2) else None
            else:
                # Qualitative result (e.g. "Trace Positive", "Negative")
                val_str = main_part.strip()
                unit_str = None
            # If unit contains reference range like "g/dL 12-15", clean trailing range
            if unit_str:
                unit_str = re.split(r"[\s\(\[\{]+(?:ref|\d+[\s\-\–])", unit_str, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                if not unit_str:
                    unit_str = None

            detected_val, val_text, trailing_unit, p_status = parse_numeric_and_unit(val_str)
            final_unit = unit_str or trailing_unit

            # Calculate char offsets in original line
            start_off = line.find(match.group("label"))
            end_off = len(line)

            loc = SourceLocation(
                line_number=idx,
                char_start_offset=start_off if start_off >= 0 else None,
                char_end_offset=end_off if start_off >= 0 else None
            )

            observations.append(RawObservation(
                raw_label=raw_lbl,
                raw_value_text=val_str,
                detected_value=detected_val,
                raw_unit=final_unit,
                source_location=loc,
                extraction_method="DELIMITED_TEXT",
                extraction_confidence=None,
                parsing_status=p_status
            ))

        status = ExtractionStatus.SUCCESS if observations else ExtractionStatus.SUCCESS_EMPTY
        return ExtractionResult(
            observations=observations,
            diagnostics=diagnostics,
            extraction_status=status,
            detected_format=DocumentFormat.PLAIN_TEXT
        )

    @classmethod
    def extract(cls, report_text: str) -> List[RawObservation]:
        """Backward-compatible extraction method returning List[RawObservation]."""
        return cls.extract_result(report_text).observations


# =============================================================================
# STRATEGY 2: COLUMNAR TABLE STRATEGY
# =============================================================================

class ColumnarTableStrategy:
    """
    Extracts laboratory observations from whitespace-separated and fixed-width tables.
    Recognizes header rows (Test Name, Result, Units, Reference Range).
    Rejects ambiguous multi-column structures.
    """

    HEADER_TEST_NAMES = {"test", "test name", "biomarker", "parameter", "analytic", "description", "analyte", "investigation"}
    HEADER_RESULTS = {"result", "value", "observed value", "measurement", "patient result", "test result"}
    HEADER_UNITS = {"unit", "units", "result unit"}
    HEADER_REFS = {"reference range", "ref range", "biological reference interval", "normal range", "reference interval"}
    HEADER_STATUS = {"status", "flag", "abnormal flag", "interpretation"}

    @classmethod
    def extract_result(cls, report_text: str) -> ExtractionResult:
        if not report_text or not report_text.strip():
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=DocumentFormat.PLAIN_TEXT
            )

        observations: List[RawObservation] = []
        diagnostics: List[ExtractionDiagnostic] = []

        lines = report_text.splitlines()
        header_line_idx = -1
        col_names: List[str] = []

        # 1. Scan for header line
        for idx, line in enumerate(lines, start=1):
            line_str = line.strip().lower()
            if not line_str:
                continue

            # Split by 2 or more spaces or tabs (normalized to lowercase for matching)
            columns = [c.strip().lower() for c in re.split(r"\s{2,}|\t+", line.strip()) if c.strip()]
            has_test = any(c in cls.HEADER_TEST_NAMES for c in columns)
            has_result = any(c in cls.HEADER_RESULTS for c in columns)

            if has_test and has_result:
                header_line_idx = idx
                # Map column positions
                # Check for duplicate result headers -> Ambiguous, reject table with diagnostic
                res_count = sum(1 for c in columns if c in cls.HEADER_RESULTS)
                if res_count > 1:
                    matched_cols = [c for c in columns if c in cls.HEADER_RESULTS]
                    loc = SourceLocation(line_number=idx, row_number=1)
                    diagnostics.append(ExtractionDiagnostic(
                        diagnostic_code="AMBIGUOUS_RESULT_HEADER",
                        diagnostic_message=(
                            f"Ambiguous columnar table header rejected on line {idx}: "
                            f"multiple result columns detected ({', '.join(matched_cols)}). "
                            f"Cannot safely select result column."
                        ),
                        severity="ERROR",
                        source_location=loc,
                        raw_content=line.strip(),
                        strategy_name="COLUMNAR_TABLE"
                    ))
                    return ExtractionResult(
                        observations=[],
                        diagnostics=diagnostics,
                        extraction_status=ExtractionStatus.FAILED,
                        detected_format=DocumentFormat.PLAIN_TEXT
                    )

                # Store column semantic roles in order
                col_names = []
                for c in columns:
                    if c in cls.HEADER_TEST_NAMES:
                        col_names.append("test")
                    elif c in cls.HEADER_RESULTS:
                        col_names.append("result")
                    elif c in cls.HEADER_UNITS:
                        col_names.append("unit")
                    elif c in cls.HEADER_REFS:
                        col_names.append("ref")
                    else:
                        col_names.append("other")
                break

        if header_line_idx == -1:
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=DocumentFormat.PLAIN_TEXT
            )

        if "test" not in col_names or "result" not in col_names:
            loc = SourceLocation(line_number=header_line_idx, row_number=1)
            code = "MISSING_RESULT_COLUMN" if "result" not in col_names else "MISSING_BIOMARKER_HEADER"
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code=code,
                diagnostic_message=f"Columnar table header missing required column: {code}",
                severity="ERROR",
                source_location=loc,
                raw_content=lines[header_line_idx - 1].strip(),
                strategy_name="COLUMNAR_TABLE"
            ))
            return ExtractionResult(
                observations=[],
                diagnostics=diagnostics,
                extraction_status=ExtractionStatus.FAILED,
                detected_format=DocumentFormat.PLAIN_TEXT
            )

        test_idx = col_names.index("test")
        result_idx = col_names.index("result")
        unit_idx = col_names.index("unit") if "unit" in col_names else None

        # 2. Parse data rows following header
        row_counter = 1
        for idx, line in enumerate(lines[header_line_idx:], start=header_line_idx + 1):
            line_str = line.strip()
            if not line_str or line_str.startswith("---") or line_str.startswith("==="):
                continue

            tokens = [c.strip() for c in re.split(r"\s{2,}|\t+", line.strip()) if c.strip()]
            if len(tokens) <= max(test_idx, result_idx):
                loc = SourceLocation(line_number=idx, row_number=row_counter)
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="MALFORMED_TABLE_ROW",
                    diagnostic_message=f"Row on line {idx} has insufficient columns ({len(tokens)} found).",
                    severity="WARNING",
                    source_location=loc,
                    raw_content=line_str,
                    strategy_name="COLUMNAR_TABLE"
                ))
                continue

            test_val = tokens[test_idx]
            result_val = tokens[result_idx]
            unit_val = tokens[unit_idx] if (unit_idx is not None and len(tokens) > unit_idx) else None

            # Guard: ensure result_val is not a reference range (e.g. "12.0 - 15.5")
            if REF_RANGE_PATTERN.match(result_val):
                continue

            # If unit_val matches a reference range pattern, it is not a unit!
            if unit_val and (REF_RANGE_PATTERN.match(unit_val) or re.search(r"\d+[\s\-\–]\d+", unit_val)):
                unit_val = None

            detected_val, val_text, trailing_unit, p_status = parse_numeric_and_unit(result_val)
            final_unit = unit_val or trailing_unit

            loc = SourceLocation(
                line_number=idx,
                row_number=row_counter,
                column_name="Result"
            )
            row_counter += 1

            observations.append(RawObservation(
                raw_label=clean_label(test_val),
                raw_value_text=result_val,
                detected_value=detected_val,
                raw_unit=final_unit,
                source_location=loc,
                extraction_method="COLUMNAR_TABLE",
                extraction_confidence=None,
                parsing_status=p_status
            ))

        if observations and diagnostics:
            status = ExtractionStatus.PARTIAL_SUCCESS
        elif observations:
            status = ExtractionStatus.SUCCESS
        elif diagnostics:
            status = ExtractionStatus.FAILED
        else:
            status = ExtractionStatus.SUCCESS_EMPTY

        return ExtractionResult(
            observations=observations,
            diagnostics=diagnostics,
            extraction_status=status,
            detected_format=DocumentFormat.PLAIN_TEXT
        )

    @classmethod
    def extract(cls, report_text: str) -> List[RawObservation]:
        """Backward-compatible extraction method returning List[RawObservation]."""
        return cls.extract_result(report_text).observations


# =============================================================================
# STRATEGY 3: CSV & TSV TABLE STRATEGY
# =============================================================================

class CSVTableStrategy:
    """
    Extracts laboratory observations from CSV and TSV content using python's csv module.
    Detects header mappings using an alias dictionary.
    Supports comma, semicolon, and tab delimiters.
    Rejects ambiguous or duplicate result headers.
    """

    HEADER_ALIASES: Dict[str, List[str]] = {
        "biomarker": ["test", "test name", "test_name", "parameter", "analytic", "description", "analyte", "investigation"],
        "result": ["result", "value", "observed value", "measurement", "test result", "patient result"],
        "unit": ["unit", "units", "result unit", "standard unit"]
    }

    @classmethod
    def extract_result(cls, csv_content: str, delimiter: Optional[str] = None) -> ExtractionResult:
        if not csv_content or not csv_content.strip():
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=DocumentFormat.CSV
            )

        # Determine delimiter
        delim = delimiter
        format_detected = DocumentFormat.CSV
        if delim is None:
            first_line = csv_content.strip().splitlines()[0]
            if "\t" in first_line:
                delim = "\t"
                format_detected = DocumentFormat.TSV
            elif ";" in first_line and "," not in first_line:
                delim = ";"
                format_detected = DocumentFormat.CSV
            else:
                delim = ","
                format_detected = DocumentFormat.CSV
        elif delim == "\t":
            format_detected = DocumentFormat.TSV

        observations: List[RawObservation] = []
        diagnostics: List[ExtractionDiagnostic] = []

        reader = csv.reader(io.StringIO(csv_content), delimiter=delim)
        rows = list(reader)
        if not rows:
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=format_detected
            )

        # Header detection
        raw_header_line = rows[0][0] if len(rows[0]) == 1 else delim.join(rows[0])
        header_row = [c.strip().lower() for c in rows[0]]
        col_map: Dict[str, int] = {}
        result_cols_found = 0

        for idx, col in enumerate(header_row):
            for canon_key, aliases in cls.HEADER_ALIASES.items():
                if col in aliases:
                    if canon_key == "result":
                        result_cols_found += 1
                    if canon_key not in col_map:
                        col_map[canon_key] = idx

        # Disambiguation guard: duplicate result headers -> halt/reject with explicit diagnostic
        if result_cols_found > 1:
            matched_res_headers = [col for col in header_row if any(alias in col for alias in cls.HEADER_ALIASES["result"])]
            loc = SourceLocation(line_number=1, row_number=1)
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code="AMBIGUOUS_RESULT_HEADER",
                diagnostic_message=(
                    f"Ambiguous CSV/TSV table header rejected on line 1: "
                    f"multiple result columns detected ({', '.join(matched_res_headers)}). "
                    f"Cannot safely select result column."
                ),
                severity="ERROR",
                source_location=loc,
                raw_content=raw_header_line,
                strategy_name="CSV_TABLE"
            ))
            return ExtractionResult(
                observations=[],
                diagnostics=diagnostics,
                extraction_status=ExtractionStatus.FAILED,
                detected_format=format_detected
            )

        # Missing mandatory columns -> explicit structured diagnostic
        if "biomarker" not in col_map or "result" not in col_map:
            loc = SourceLocation(line_number=1, row_number=1)
            missing_code = "MISSING_RESULT_COLUMN" if "result" not in col_map else "MISSING_BIOMARKER_HEADER"
            diagnostics.append(ExtractionDiagnostic(
                diagnostic_code=missing_code,
                diagnostic_message=f"CSV/TSV table header missing required column: {missing_code}",
                severity="ERROR",
                source_location=loc,
                raw_content=raw_header_line,
                strategy_name="CSV_TABLE"
            ))
            return ExtractionResult(
                observations=[],
                diagnostics=diagnostics,
                extraction_status=ExtractionStatus.FAILED,
                detected_format=format_detected
            )

        bio_idx = col_map["biomarker"]
        res_idx = col_map["result"]
        unit_idx = col_map.get("unit")

        for row_idx, row in enumerate(rows[1:], start=2):
            if not row or all(not c.strip() for c in row):
                continue

            raw_row_str = delim.join(row)

            # Check for short or malformed row: preserve diagnostic, do NOT create artificial observation
            if len(row) <= max(bio_idx, res_idx):
                loc = SourceLocation(line_number=row_idx, row_number=row_idx - 1)
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="MALFORMED_CSV_ROW",
                    diagnostic_message=f"Malformed row {row_idx - 1} on line {row_idx}: insufficient columns ({len(row)} present, required at least {max(bio_idx, res_idx) + 1}).",
                    severity="WARNING",
                    source_location=loc,
                    raw_content=raw_row_str,
                    strategy_name="CSV_TABLE"
                ))
                continue

            raw_bio_text = row[bio_idx].strip()
            val_str = row[res_idx].strip()
            unit_str = row[unit_idx].strip() if (unit_idx is not None and len(row) > unit_idx and row[unit_idx].strip()) else None

            # Check if biomarker label is missing: create diagnostic, do NOT create artificial observation
            if not raw_bio_text:
                loc = SourceLocation(
                    line_number=row_idx,
                    row_number=row_idx - 1,
                    column_number=bio_idx + 1,
                    column_name=header_row[bio_idx]
                )
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="MISSING_BIOMARKER_LABEL",
                    diagnostic_message=f"Row {row_idx - 1} on line {row_idx} is missing biomarker label.",
                    severity="WARNING",
                    source_location=loc,
                    raw_content=raw_row_str,
                    strategy_name="CSV_TABLE"
                ))
                continue

            # Check if result field is missing: create diagnostic, do NOT create artificial observation
            if not val_str:
                loc = SourceLocation(
                    line_number=row_idx,
                    row_number=row_idx - 1,
                    column_number=res_idx + 1,
                    column_name=header_row[res_idx]
                )
                diagnostics.append(ExtractionDiagnostic(
                    diagnostic_code="MISSING_RESULT_VALUE",
                    diagnostic_message=f"Row {row_idx - 1} on line {row_idx} for '{raw_bio_text}' has empty result value.",
                    severity="WARNING",
                    source_location=loc,
                    raw_content=raw_row_str,
                    strategy_name="CSV_TABLE"
                ))
                continue

            label = clean_label(raw_bio_text)
            detected_val, val_text, trailing_unit, p_status = parse_numeric_and_unit(val_str)
            final_unit = unit_str or trailing_unit

            loc = SourceLocation(
                line_number=row_idx,
                row_number=row_idx - 1,
                column_number=res_idx + 1,
                column_name=header_row[res_idx]
            )

            observations.append(RawObservation(
                raw_label=label,
                raw_value_text=val_str,
                detected_value=detected_val,
                raw_unit=final_unit,
                source_location=loc,
                extraction_method="CSV_TABLE",
                extraction_confidence=None,
                parsing_status=p_status,
                raw_row_content=raw_row_str
            ))

        if observations and diagnostics:
            status = ExtractionStatus.PARTIAL_SUCCESS
        elif observations:
            status = ExtractionStatus.SUCCESS
        elif diagnostics:
            status = ExtractionStatus.FAILED
        else:
            status = ExtractionStatus.SUCCESS_EMPTY

        return ExtractionResult(
            observations=observations,
            diagnostics=diagnostics,
            extraction_status=status,
            detected_format=format_detected
        )

    @classmethod
    def extract(cls, csv_content: str, delimiter: Optional[str] = None) -> List[RawObservation]:
        """Backward-compatible extraction method returning List[RawObservation]."""
        return cls.extract_result(csv_content, delimiter=delimiter).observations


# =============================================================================
# STRATEGY 4: MULTILINE LABEL/VALUE PAIR STRATEGY
# =============================================================================

class MultilinePairStrategy:
    """
    Extracts laboratory observations when a biomarker label is immediately followed
    on the next line by its measurement value and optional unit.
    Strictly conservative: halts if association is ambiguous or interrupted by other text.
    """

    VALUE_LINE_PATTERN = re.compile(
        r"^([+\-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?|[<>]=?\s*[0-9]+(?:\.[0-9]+)?)\s*([A-Za-z\/%µu\^0-9\-\*]+)?$"
    )

    @classmethod
    def extract_result(cls, report_text: str) -> ExtractionResult:
        if not report_text or not report_text.strip():
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=DocumentFormat.PLAIN_TEXT
            )

        observations: List[RawObservation] = []
        diagnostics: List[ExtractionDiagnostic] = []

        lines = report_text.splitlines()
        i = 0
        n = len(lines)

        while i < n - 1:
            curr_line = lines[i].strip()
            next_line = lines[i + 1].strip()

            # Skip empty lines
            if not curr_line:
                i += 1
                continue

            # Candidate label: 2-40 chars, no colon/delimiter at end, purely alphabetical/alphanumeric
            if (
                2 <= len(curr_line) <= 40
                and not re.search(r"[:=\-]$", curr_line)
                and not METADATA_LABELS_PATTERN.match(curr_line)
                and not re.match(r"^[0-9\.\-\+]", curr_line)  # Cannot start with number
            ):
                val_match = cls.VALUE_LINE_PATTERN.match(next_line)
                if val_match:
                    # Check next+2 line: if it's also a number, curr_line association is ambiguous!
                    if i + 2 < n and cls.VALUE_LINE_PATTERN.match(lines[i + 2].strip()):
                        loc = SourceLocation(line_number=i + 1)
                        diagnostics.append(ExtractionDiagnostic(
                            diagnostic_code="AMBIGUOUS_MULTILINE_ASSOCIATION",
                            diagnostic_message=f"Ambiguous successive numbers following label '{curr_line}' on line {i + 1}.",
                            severity="WARNING",
                            source_location=loc,
                            raw_content=curr_line,
                            strategy_name="MULTILINE_PAIR"
                        ))
                        i += 3  # Ambiguous multiline structure with multiple numbers, skip label and all numbers
                        continue

                    raw_lbl = clean_label(curr_line)
                    val_str = val_match.group(1).strip()
                    unit_str = val_match.group(2).strip() if val_match.group(2) else None

                    detected_val, val_text, trailing_unit, p_status = parse_numeric_and_unit(val_str)
                    final_unit = unit_str or trailing_unit

                    loc = SourceLocation(line_number=i + 1)
                    observations.append(RawObservation(
                        raw_label=raw_lbl,
                        raw_value_text=val_str,
                        detected_value=detected_val,
                        raw_unit=final_unit,
                        source_location=loc,
                        extraction_method="MULTILINE_PAIR",
                        extraction_confidence=None,
                        parsing_status=p_status
                    ))
                    i += 2
                    continue

            i += 1

        if observations and diagnostics:
            status = ExtractionStatus.PARTIAL_SUCCESS
        elif observations:
            status = ExtractionStatus.SUCCESS
        elif diagnostics:
            status = ExtractionStatus.FAILED
        else:
            status = ExtractionStatus.SUCCESS_EMPTY

        return ExtractionResult(
            observations=observations,
            diagnostics=diagnostics,
            extraction_status=status,
            detected_format=DocumentFormat.PLAIN_TEXT
        )

    @classmethod
    def extract(cls, report_text: str) -> List[RawObservation]:
        """Backward-compatible extraction method returning List[RawObservation]."""
        return cls.extract_result(report_text).observations


# =============================================================================
# UNIFIED COMPOSITE EXTRACTOR ENGINE
# =============================================================================

class CompositeReportExtractor:
    """
    Orchestrates extraction strategies across plain text, columnar tables, CSV, TSV,
    and multiline structures into standardized ExtractionResult and List[RawObservation].
    """

    @classmethod
    def extract_result(
        cls,
        content: str,
        document_format: DocumentFormat = DocumentFormat.PLAIN_TEXT
    ) -> ExtractionResult:
        if not content or not content.strip():
            return ExtractionResult(
                observations=[],
                diagnostics=[],
                extraction_status=ExtractionStatus.SUCCESS_EMPTY,
                detected_format=document_format
            )

        # 1. Format-specific dispatch
        if document_format in (DocumentFormat.CSV, DocumentFormat.TSV):
            delim = "\t" if document_format == DocumentFormat.TSV else None
            return CSVTableStrategy.extract_result(content, delimiter=delim)

        first_line = content.strip().splitlines()[0]

        # 2. Check for explicit TSV table format (contains tabs with biomarker/result headers)
        if "\t" in first_line:
            header_tokens = [t.strip().lower() for t in first_line.split("\t") if t.strip()]
            has_bio = any(any(alias in t for alias in CSVTableStrategy.HEADER_ALIASES["biomarker"]) for t in header_tokens)
            has_res = any(any(alias in t for alias in CSVTableStrategy.HEADER_ALIASES["result"]) for t in header_tokens)
            if has_bio and has_res:
                return CSVTableStrategy.extract_result(content, delimiter="\t")

        # 3. Check for explicit CSV / Semicolon structured table
        if ("," in first_line or ";" in first_line) and not re.search(r"[:=\-]", first_line):
            delim = ";" if (";" in first_line and "," not in first_line) else ","
            header_tokens = [t.strip().lower() for t in first_line.split(delim) if t.strip()]
            has_bio = any(any(alias in t for alias in CSVTableStrategy.HEADER_ALIASES["biomarker"]) for t in header_tokens)
            has_res = any(any(alias in t for alias in CSVTableStrategy.HEADER_ALIASES["result"]) for t in header_tokens)
            if has_bio and has_res:
                return CSVTableStrategy.extract_result(content, delimiter=delim)

        # 4. Standard Delimited Text extraction (colon, equals, hyphen)
        res_delim = DelimitedTextStrategy.extract_result(content)
        if res_delim.observations:
            return res_delim

        # 5. Check for Columnar table format (fixed width / multi-space separated)
        res_col = ColumnarTableStrategy.extract_result(content)
        if res_col.observations or res_col.diagnostics:
            return res_col

        # 6. Multiline Pair fallback
        res_multi = MultilinePairStrategy.extract_result(content)
        if res_multi.observations or res_multi.diagnostics:
            return res_multi

        # 7. Fallback if no strategy produced observations: return empty success or delimiter result
        return res_delim

    @classmethod
    def extract_observations(
        cls,
        content: str,
        document_format: DocumentFormat = DocumentFormat.PLAIN_TEXT
    ) -> List[RawObservation]:
        """Backward-compatible extraction method returning List[RawObservation]."""
        return cls.extract_result(content, document_format).observations


# =============================================================================
# BACKWARD COMPATIBILITY ADAPTER FOR CLINICAL REPORT PARSER
# =============================================================================

class ClinicalReportParser:
    """
    Parser strictly dedicated to feature extraction and lexical tokenization.
    Preserves 100% backward compatibility for parse_text() -> List[ParsedObservation].
    """

    OBSERVATION_PATTERN = re.compile(
        r"(?P<label>[A-Za-z0-9_\s\(\)\/\-\.]{2,40}?)\s*[:=\-]\s*(?P<value>[+\-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?P<unit>[A-Za-z\/%µu\^0-9\-\*]+)?",
        re.IGNORECASE
    )

    @classmethod
    def parse_text(cls, report_text: str) -> List[ParsedObservation]:
        """Legacy interface returning List[ParsedObservation]."""
        observations: List[ParsedObservation] = []
        if not report_text:
            return observations

        lines = report_text.splitlines()
        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("//"):
                continue

            matches = list(cls.OBSERVATION_PATTERN.finditer(line_str))
            for match in matches:
                label = match.group("label").strip()
                val_str = match.group("value").replace(",", "").strip()
                unit = match.group("unit").strip() if match.group("unit") else None

                label = re.sub(r"^[\*\-\•\d\.\s]+", "", label).strip()
                if not label:
                    continue

                try:
                    val = float(val_str)
                    observations.append(ParsedObservation(
                        raw_key=label,
                        detected_value=val,
                        raw_unit=unit,
                        line_number=idx,
                        is_inconclusive=False
                    ))
                except ValueError:
                    observations.append(ParsedObservation(
                        raw_key=label,
                        detected_value=None,
                        raw_unit=unit,
                        line_number=idx,
                        is_inconclusive=True,
                        inconclusive_reason=f"Unable to parse numeric value: '{val_str}'"
                    ))

        return observations

    @classmethod
    def extract_raw_observations(
        cls,
        report_text: str,
        document_format: DocumentFormat = DocumentFormat.PLAIN_TEXT
    ) -> List[RawObservation]:
        """Phase 3 extraction interface returning List[RawObservation]."""
        return CompositeReportExtractor.extract_observations(report_text, document_format)

    @classmethod
    def extract_report(
        cls,
        report_text: str,
        document_format: DocumentFormat = DocumentFormat.PLAIN_TEXT
    ) -> ExtractionResult:
        """Phase 3 extraction interface returning strongly typed ExtractionResult."""
        return CompositeReportExtractor.extract_result(report_text, document_format)

