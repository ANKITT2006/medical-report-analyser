"""
Domain Schemas for Clinical Report Ingestion & Analysis.
Strict, type-safe data contracts supporting both Pydantic (v1/v2 compatibility) and standard dataclasses.
Fully reconciled with Phase 2 Canonical Reference Schemas.
"""

from typing import List, Optional, Dict, Any
from enum import Enum

try:
    from pydantic import BaseModel, Field

    class SeverityLevel(str, Enum):
        OPTIMAL = "OPTIMAL"
        MILD_LOW = "MILD_LOW"
        MILD_HIGH = "MILD_HIGH"
        CRITICAL_LOW = "CRITICAL_LOW"
        CRITICAL_HIGH = "CRITICAL_HIGH"
        INCONCLUSIVE = "INCONCLUSIVE"
        UNKNOWN = "UNKNOWN"

    class MetricStatus(str, Enum):
        NORMAL = "Normal"
        LOW = "Low"
        ELEVATED = "Elevated"
        CRITICAL_LOW = "Critical Low"
        CRITICAL_HIGH = "Critical High"
        INCONCLUSIVE = "Inconclusive"
        UNKNOWN = "Unknown Metric"

    class CriticalLimitType(str, Enum):
        CLINICAL_PRACTICE_ALERT_THRESHOLD = "CLINICAL_PRACTICE_ALERT_THRESHOLD"
        LABORATORY_SPECIFIC_PANIC_ALERT = "LABORATORY_SPECIFIC_PANIC_ALERT"
        CONSENSUS_PANIC_SURVEY_MEDIAN = "CONSENSUS_PANIC_SURVEY_MEDIAN"

    class GestationalApplicabilityType(str, Enum):
        UNAFFECTED = "UNAFFECTED"
        PHYSIOLOGICAL_SHIFT = "PHYSIOLOGICAL_SHIFT"
        METHODOLOGY_CONTRAINDICATED = "METHODOLOGY_CONTRAINDICATED"
        TRIMESTER_STRATIFIED = "TRIMESTER_STRATIFIED"
        UNKNOWN = "UNKNOWN"

    # =========================================================================
    # PHASE 3 INGESTION & NORMALIZATION STATUS ENUMS
    # =========================================================================

    class InputSourceType(str, Enum):
        TEXT_INPUT = "TEXT_INPUT"
        FILE_UPLOAD = "FILE_UPLOAD"

    class DocumentFormat(str, Enum):
        UNDETECTED = "UNDETECTED"
        PLAIN_TEXT = "PLAIN_TEXT"
        CSV = "CSV"
        TSV = "TSV"
        PDF = "PDF"
        IMAGE = "IMAGE"
        UNSUPPORTED = "UNSUPPORTED"

    class DocumentProcessingStatus(str, Enum):
        PENDING = "PENDING"
        EXTRACTED = "EXTRACTED"
        EXTRACTION_FAILED = "EXTRACTION_FAILED"
        UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
        CORRUPTED_DOCUMENT = "CORRUPTED_DOCUMENT"

    class ExtractionStatus(str, Enum):
        SUCCESS = "SUCCESS"
        SUCCESS_EMPTY = "SUCCESS_EMPTY"
        PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
        FAILED = "FAILED"
        UNSUPPORTED = "UNSUPPORTED"

    class ParsingStatus(str, Enum):
        PARSED = "PARSED"
        NON_NUMERIC_RESULT = "NON_NUMERIC_RESULT"
        MISSING_VALUE = "MISSING_VALUE"
        MISSING_UNIT = "MISSING_UNIT"
        EXTRACTION_FAILED = "EXTRACTION_FAILED"

    class IngestionStatus(str, Enum):
        VALID = "VALID"
        UNKNOWN_BIOMARKER = "UNKNOWN_BIOMARKER"
        AMBIGUOUS_BIOMARKER = "AMBIGUOUS_BIOMARKER"
        MISSING_VALUE = "MISSING_VALUE"
        MISSING_UNIT = "MISSING_UNIT"
        NON_NUMERIC_RESULT = "NON_NUMERIC_RESULT"
        UNSUPPORTED_UNIT = "UNSUPPORTED_UNIT"
        CONVERSION_FAILED = "CONVERSION_FAILED"
        EXTRACTION_FAILED = "EXTRACTION_FAILED"
        INCONCLUSIVE = "INCONCLUSIVE"

    # =========================================================================
    # PHASE 3 INGESTION & NORMALIZATION DOMAIN CONTRACTS
    # =========================================================================

    class ConversionAudit(BaseModel):
        original_value: float
        original_unit: str
        converted_value: float
        standard_unit: str
        conversion_type: str
        formula_used: str
        handler_executed: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class RawDocumentInput(BaseModel):
        raw_content: Any  # str or bytes; not automatically parsed/trusted
        original_filename: Optional[str] = None
        declared_mime_type: Optional[str] = None
        detected_extension: Optional[str] = None
        input_source: InputSourceType = InputSourceType.TEXT_INPUT
        document_id: Optional[str] = None
        file_metadata: Dict[str, Any] = Field(default_factory=dict)
        document_format: DocumentFormat = DocumentFormat.UNDETECTED

        def __init__(self, **data):
            # Format safety: if document_format is not explicitly passed:
            # TEXT_INPUT defaults to PLAIN_TEXT; FILE_UPLOAD strictly remains UNDETECTED
            if "document_format" not in data or data["document_format"] is None:
                src = data.get("input_source", InputSourceType.TEXT_INPUT)
                if src == InputSourceType.TEXT_INPUT:
                    data["document_format"] = DocumentFormat.PLAIN_TEXT
                else:
                    data["document_format"] = DocumentFormat.UNDETECTED
            super().__init__(**data)

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class SourceLocation(BaseModel):
        page_number: Optional[int] = None
        line_number: Optional[int] = None
        row_number: Optional[int] = None
        column_number: Optional[int] = None
        column_name: Optional[str] = None
        char_start_offset: Optional[int] = None
        char_end_offset: Optional[int] = None

        def __init__(self, **data):
            for coord in ("page_number", "line_number", "row_number", "column_number"):
                val = data.get(coord)
                if val is not None and val < 1:
                    raise ValueError(f"{coord} must use positive 1-based indexing (got {val}).")
            start = data.get("char_start_offset")
            end = data.get("char_end_offset")
            if start is not None and start < 0:
                raise ValueError(f"char_start_offset must be non-negative (got {start}).")
            if end is not None and end < 0:
                raise ValueError(f"char_end_offset must be non-negative (got {end}).")
            if start is not None and end is not None and end < start:
                raise ValueError(f"char_end_offset ({end}) cannot precede char_start_offset ({start}).")
            super().__init__(**data)

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class RawObservation(BaseModel):
        raw_label: str
        raw_value_text: str
        detected_value: Optional[float] = None
        raw_unit: Optional[str] = None
        source_location: Optional[SourceLocation] = None
        extraction_method: str = "REGEX_DELIMITED"
        extraction_confidence: Optional[float] = None
        parsing_status: ParsingStatus = ParsingStatus.PARSED
        diagnostic_message: Optional[str] = None
        raw_row_content: Optional[str] = None

        def __init__(self, **data):
            conf = data.get("extraction_confidence")
            if conf is not None:
                if not isinstance(conf, (int, float)) or conf < 0.0 or conf > 1.0:
                    raise ValueError(f"extraction_confidence must be between 0.0 and 1.0 inclusive (got {conf}).")
            super().__init__(**data)

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class ExtractionDiagnostic(BaseModel):
        diagnostic_code: str
        diagnostic_message: str
        severity: str = "ERROR"  # 'INFO', 'WARNING', 'ERROR'
        source_location: Optional[SourceLocation] = None
        raw_content: Optional[str] = None
        strategy_name: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class ExtractionResult(BaseModel):
        observations: List[RawObservation] = Field(default_factory=list)
        diagnostics: List[ExtractionDiagnostic] = Field(default_factory=list)
        extraction_status: ExtractionStatus
        detected_format: DocumentFormat = DocumentFormat.UNDETECTED

        def __init__(self, **data):
            if "extraction_status" not in data or data["extraction_status"] is None:
                raise ValueError("ExtractionResult requires an explicit 'extraction_status' (no silent SUCCESS assumption).")
            status = data["extraction_status"]
            obs = data.get("observations") or []
            diags = data.get("diagnostics") or []

            # Invariant: PARTIAL_SUCCESS requires at least one observation AND at least one diagnostic
            if status == ExtractionStatus.PARTIAL_SUCCESS:
                if not obs:
                    raise ValueError("ExtractionStatus.PARTIAL_SUCCESS requires at least one valid observation.")
                if not diags:
                    raise ValueError("ExtractionStatus.PARTIAL_SUCCESS requires at least one diagnostic.")

            # Invariant: SUCCESS requires no ERROR-severity diagnostics
            if status == ExtractionStatus.SUCCESS:
                error_diags = [d for d in diags if getattr(d, "severity", None) == "ERROR" or (isinstance(d, dict) and d.get("severity") == "ERROR")]
                if error_diags:
                    raise ValueError("ExtractionStatus.SUCCESS cannot contain ERROR diagnostics; use PARTIAL_SUCCESS or FAILED.")

            # Invariant: SUCCESS_EMPTY requires observations to be empty
            if status == ExtractionStatus.SUCCESS_EMPTY and obs:
                raise ValueError("ExtractionStatus.SUCCESS_EMPTY cannot contain observations; use SUCCESS or PARTIAL_SUCCESS.")

            super().__init__(**data)

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class NormalizedObservation(BaseModel):
        # Original Observation Data (Preserved verbatim)
        raw_label: str
        original_value_text: str
        original_detected_value: Optional[float] = None
        original_unit: Optional[str] = None

        # Canonical Biomarker Resolution
        canonical_metric_id: Optional[str] = None
        canonical_biomarker_name: Optional[str] = None
        loinc_code: Optional[str] = None

        # Normalized Measurements
        normalized_value: Optional[float] = None
        normalized_unit: Optional[str] = None

        # Provenance Tracking
        source_document_id: Optional[str] = None
        source_location: Optional[SourceLocation] = None
        conversion_audit: Optional[ConversionAudit] = None

        # Validation & Clinical Governance Status
        ingestion_status: IngestionStatus = IngestionStatus.INCONCLUSIVE
        validation_messages: List[str] = Field(default_factory=list)
        inconclusive_reason: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class LabMetric(BaseModel):
        metric_id: str
        canonical_name: str
        category: str
        unit: str
        gender: str = "all"  # 'all', 'male', 'female'
        min_normal: Optional[float] = None
        max_normal: Optional[float] = None
        loinc_code: Optional[str] = None
        critical_low: Optional[float] = None
        critical_high: Optional[float] = None
        description: Optional[str] = None
        aliases: List[str] = Field(default_factory=list)
        is_demographic_dependent: bool = False
        evaluation_status: str = "CONCLUSIVE"
        demographic_requirement_note: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class ReferenceInterval(BaseModel):
        interval_id: Optional[int] = None
        metric_id: str
        population: str
        gender: str
        age_min_years: float
        age_max_years: float
        pregnancy_status: str
        unit: str
        min_normal: float
        max_normal: float
        interval_context_note: str
        source_reference: str
        verification_status: str
        interval_tier: str = "PRIMARY_POPULATION_BENCHMARK"
        analytical_method_tag: str = "ALL_METHODS"

    class CriticalLimit(BaseModel):
        critical_limit_id: Optional[int] = None
        metric_id: str
        critical_low: Optional[float] = None
        critical_high: Optional[float] = None
        unit: str
        limit_type: CriticalLimitType
        institutional_note: str
        clinical_urgency: str
        source_reference: str
        verification_status: str
        institutional_identifier: Optional[str] = None

    class DiagnosticThreshold(BaseModel):
        diagnostic_id: Optional[int] = None
        metric_id: str
        condition_name: str
        cutoff_value: float
        comparison_operator: str
        unit: str
        requires_repeat_confirmation: bool
        clinical_criteria: str
        source_guideline: str
        verification_status: str

    class TreatmentTarget(BaseModel):
        target_id: Optional[int] = None
        metric_id: str
        target_population: str
        goal_description: str
        target_value: float
        comparison_operator: str
        unit: str
        source_guideline: str
        verification_status: str

    class RiskTier(BaseModel):
        risk_id: Optional[int] = None
        metric_id: str
        tier_name: str
        tier_description: str
        lower_bound: Optional[float] = None
        upper_bound: Optional[float] = None
        unit: str
        clinical_significance: str
        source_classification: str
        verification_status: str

    class UnitConversion(BaseModel):
        conversion_id: Optional[int] = None
        metric_id: str
        alternative_unit: str
        standard_unit: str
        conversion_type: str  # 'LINEAR_SCALE' or 'COMPILED_FUNCTION'
        conversion_factor: Optional[float] = None
        canonical_conversion_formula: str
        formula_description: str
        handler_function_name: str

    class ClinicalContext(BaseModel):
        metric_id: str
        canonical_name: Optional[str] = None
        category: Optional[str] = None
        standard_unit: Optional[str] = None
        fasting_required: bool = False
        fasting_recommended_hours: Optional[float] = None
        fasting_details: Optional[str] = "None"
        measurement_type: Optional[str] = "Quantitative"
        methodology: Optional[str] = "Automated Spectrophotometry"
        equation_description: Optional[str] = None
        longitudinal_requirements: Optional[str] = None
        clinical_limitations: Optional[str] = None
        gestational_applicability_type: GestationalApplicabilityType = GestationalApplicabilityType.UNKNOWN
        gestational_contraindication_note: Optional[str] = None
        primary_source_organization: Optional[str] = "Clinical Laboratory Standards"
        primary_document_title: Optional[str] = "Reference Standard Guideline"
        publication_year: Optional[int] = 2024
        source_url: Optional[str] = "https://loinc.org"
        provenance_verification_status: Optional[str] = "VERIFIED"
        provenance_clinical_notes: Optional[str] = None

    class PatientContext(BaseModel):
        age_years: Optional[float] = None
        biological_sex: Optional[str] = None       # 'male', 'female', or None
        is_pregnant: Optional[bool] = None         # True, False, or None
        gestational_age_weeks: Optional[float] = None # Gestational age in weeks (e.g. 14.5)
        gestational_trimester: Optional[int] = None # 1, 2, 3, or None
        measurement_type: Optional[str] = None
        analytical_method: Optional[str] = None
        institutional_context: Optional[str] = None # e.g. 'MGH'
        fasting_confirmed: Optional[bool] = None   # True, False, or None
        pregnancy_status: Optional[str] = None     # Optional alias for is_pregnant

        def __init__(self, **data):
            if "pregnancy_status" in data and ("is_pregnant" not in data or data["is_pregnant"] is None):
                ps = data.get("pregnancy_status")
                if ps is not None:
                    ps_upper = str(ps).strip().upper()
                    if ps_upper == "PREGNANT":
                        data["is_pregnant"] = True
                    elif ps_upper in ("NOT_PREGNANT", "NON_PREGNANT", "FALSE"):
                        data["is_pregnant"] = False
                    elif ps_upper in ("UNKNOWN", "UNSTATED"):
                        data["is_pregnant"] = None
            super().__init__(**data)

    class IntervalSelectionResult(BaseModel):
        interval: Optional[ReferenceInterval] = None
        critical_limit: Optional[CriticalLimit] = None
        is_conclusive: bool
        inconclusive_code: Optional[str] = None
        inconclusive_reason: Optional[str] = None
        selection_audit_trail: List[str] = Field(default_factory=list)

    class ClinicalProtocol(BaseModel):
        protocol_id: str
        condition_id: str
        condition_name: str
        category: str
        summary_narrative: str
        dietary_guidelines: List[str] = Field(default_factory=list)
        activity_guidelines: List[str] = Field(default_factory=list)
        contraindications_to_avoid: List[str] = Field(default_factory=list)
        physician_discussion_questions: List[str] = Field(default_factory=list)
        escalation_flag: bool = False

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class ClinicalFinding(BaseModel):
        metric_id: str
        biomarker_name: str
        category: str
        detected_value: Optional[float] = None
        unit: str
        reference_range_text: str
        status: MetricStatus
        severity: SeverityLevel
        gauge_percent: int
        is_abnormal: bool
        is_critical: bool
        clinical_note: str
        associated_protocol_ids: List[str] = Field(default_factory=list)
        diagnostic_alerts: List[str] = Field(default_factory=list)
        critical_alert_info: Optional[Dict[str, Any]] = None
        conversion_applied: Optional[Dict[str, Any]] = None

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

    class AnalysisReport(BaseModel):
        status: str
        health_score: int
        risk_level: str
        risk_description: str
        total_metrics: int
        normal_metrics: int
        abnormal_metrics: int
        critical_metrics: int
        inconclusive_metrics: int
        findings: List[ClinicalFinding]
        protocols_applied: List[ClinicalProtocol]
        clinical_narrative: str
        dietary_recommendations: List[str]
        activity_recommendations: List[str]
        contraindications_to_avoid: List[str]
        physician_escalations: List[str]

        def to_dict(self) -> Dict[str, Any]:
            if hasattr(self, "model_dump"):
                return self.model_dump()
            return self.dict()

except ImportError:
    from dataclasses import dataclass, field, asdict

    # Enums are identical
    class SeverityLevel(str, Enum):
        OPTIMAL = "OPTIMAL"
        MILD_LOW = "MILD_LOW"
        MILD_HIGH = "MILD_HIGH"
        CRITICAL_LOW = "CRITICAL_LOW"
        CRITICAL_HIGH = "CRITICAL_HIGH"
        INCONCLUSIVE = "INCONCLUSIVE"
        UNKNOWN = "UNKNOWN"

    class MetricStatus(str, Enum):
        NORMAL = "Normal"
        LOW = "Low"
        ELEVATED = "Elevated"
        CRITICAL_LOW = "Critical Low"
        CRITICAL_HIGH = "Critical High"
        INCONCLUSIVE = "Inconclusive"
        UNKNOWN = "Unknown Metric"

    class CriticalLimitType(str, Enum):
        CLINICAL_PRACTICE_ALERT_THRESHOLD = "CLINICAL_PRACTICE_ALERT_THRESHOLD"
        LABORATORY_SPECIFIC_PANIC_ALERT = "LABORATORY_SPECIFIC_PANIC_ALERT"
        CONSENSUS_PANIC_SURVEY_MEDIAN = "CONSENSUS_PANIC_SURVEY_MEDIAN"

    class GestationalApplicabilityType(str, Enum):
        UNAFFECTED = "UNAFFECTED"
        PHYSIOLOGICAL_SHIFT = "PHYSIOLOGICAL_SHIFT"
        METHODOLOGY_CONTRAINDICATED = "METHODOLOGY_CONTRAINDICATED"
        TRIMESTER_STRATIFIED = "TRIMESTER_STRATIFIED"
        UNKNOWN = "UNKNOWN"

    # =========================================================================
    # PHASE 3 INGESTION & NORMALIZATION STATUS ENUMS
    # =========================================================================

    class InputSourceType(str, Enum):
        TEXT_INPUT = "TEXT_INPUT"
        FILE_UPLOAD = "FILE_UPLOAD"

    class DocumentFormat(str, Enum):
        UNDETECTED = "UNDETECTED"
        PLAIN_TEXT = "PLAIN_TEXT"
        CSV = "CSV"
        TSV = "TSV"
        PDF = "PDF"
        IMAGE = "IMAGE"
        UNSUPPORTED = "UNSUPPORTED"

    class DocumentProcessingStatus(str, Enum):
        PENDING = "PENDING"
        EXTRACTED = "EXTRACTED"
        EXTRACTION_FAILED = "EXTRACTION_FAILED"
        UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
        CORRUPTED_DOCUMENT = "CORRUPTED_DOCUMENT"

    class ExtractionStatus(str, Enum):
        SUCCESS = "SUCCESS"
        SUCCESS_EMPTY = "SUCCESS_EMPTY"
        PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
        FAILED = "FAILED"
        UNSUPPORTED = "UNSUPPORTED"

    class ParsingStatus(str, Enum):
        PARSED = "PARSED"
        NON_NUMERIC_RESULT = "NON_NUMERIC_RESULT"
        MISSING_VALUE = "MISSING_VALUE"
        MISSING_UNIT = "MISSING_UNIT"
        EXTRACTION_FAILED = "EXTRACTION_FAILED"

    class IngestionStatus(str, Enum):
        VALID = "VALID"
        UNKNOWN_BIOMARKER = "UNKNOWN_BIOMARKER"
        AMBIGUOUS_BIOMARKER = "AMBIGUOUS_BIOMARKER"
        MISSING_VALUE = "MISSING_VALUE"
        MISSING_UNIT = "MISSING_UNIT"
        NON_NUMERIC_RESULT = "NON_NUMERIC_RESULT"
        UNSUPPORTED_UNIT = "UNSUPPORTED_UNIT"
        CONVERSION_FAILED = "CONVERSION_FAILED"
        EXTRACTION_FAILED = "EXTRACTION_FAILED"
        INCONCLUSIVE = "INCONCLUSIVE"

    # =========================================================================
    # PHASE 3 INGESTION & NORMALIZATION DOMAIN CONTRACTS
    # =========================================================================

    @dataclass
    class ConversionAudit:
        original_value: float
        original_unit: str
        converted_value: float
        standard_unit: str
        conversion_type: str
        formula_used: str
        handler_executed: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class RawDocumentInput:
        raw_content: Any  # str or bytes; not automatically parsed/trusted
        original_filename: Optional[str] = None
        declared_mime_type: Optional[str] = None
        detected_extension: Optional[str] = None
        input_source: InputSourceType = InputSourceType.TEXT_INPUT
        document_id: Optional[str] = None
        file_metadata: Dict[str, Any] = field(default_factory=dict)
        document_format: DocumentFormat = DocumentFormat.UNDETECTED

        def __post_init__(self):
            # Format safety: if document_format is default UNDETECTED:
            # TEXT_INPUT defaults to PLAIN_TEXT; FILE_UPLOAD strictly remains UNDETECTED
            if self.document_format == DocumentFormat.UNDETECTED and self.input_source == InputSourceType.TEXT_INPUT:
                self.document_format = DocumentFormat.PLAIN_TEXT

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class SourceLocation:
        page_number: Optional[int] = None
        line_number: Optional[int] = None
        row_number: Optional[int] = None
        column_number: Optional[int] = None
        column_name: Optional[str] = None
        char_start_offset: Optional[int] = None
        char_end_offset: Optional[int] = None

        def __post_init__(self):
            for coord_name, val in (
                ("page_number", self.page_number),
                ("line_number", self.line_number),
                ("row_number", self.row_number),
                ("column_number", self.column_number)
            ):
                if val is not None and val < 1:
                    raise ValueError(f"{coord_name} must use positive 1-based indexing (got {val}).")
            if self.char_start_offset is not None and self.char_start_offset < 0:
                raise ValueError(f"char_start_offset must be non-negative (got {self.char_start_offset}).")
            if self.char_end_offset is not None and self.char_end_offset < 0:
                raise ValueError(f"char_end_offset must be non-negative (got {self.char_end_offset}).")
            if (
                self.char_start_offset is not None and
                self.char_end_offset is not None and
                self.char_end_offset < self.char_start_offset
            ):
                raise ValueError(
                    f"char_end_offset ({self.char_end_offset}) cannot precede char_start_offset ({self.char_start_offset})."
                )

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class RawObservation:
        raw_label: str
        raw_value_text: str
        detected_value: Optional[float] = None
        raw_unit: Optional[str] = None
        source_location: Optional[SourceLocation] = None
        extraction_method: str = "REGEX_DELIMITED"
        extraction_confidence: Optional[float] = None
        parsing_status: ParsingStatus = ParsingStatus.PARSED
        diagnostic_message: Optional[str] = None
        raw_row_content: Optional[str] = None

        def __post_init__(self):
            if self.extraction_confidence is not None:
                if (
                    not isinstance(self.extraction_confidence, (int, float)) or
                    self.extraction_confidence < 0.0 or
                    self.extraction_confidence > 1.0
                ):
                    raise ValueError(
                        f"extraction_confidence must be between 0.0 and 1.0 inclusive (got {self.extraction_confidence})."
                    )

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class ExtractionDiagnostic:
        diagnostic_code: str
        diagnostic_message: str
        severity: str = "ERROR"
        source_location: Optional[SourceLocation] = None
        raw_content: Optional[str] = None
        strategy_name: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class ExtractionResult:
        extraction_status: ExtractionStatus
        observations: List[RawObservation] = field(default_factory=list)
        diagnostics: List[ExtractionDiagnostic] = field(default_factory=list)
        detected_format: DocumentFormat = DocumentFormat.UNDETECTED

        def __post_init__(self):
            if self.extraction_status is None:
                raise ValueError("ExtractionResult requires an explicit 'extraction_status' (no silent SUCCESS assumption).")

            # Invariant: PARTIAL_SUCCESS requires at least one observation AND at least one diagnostic
            if self.extraction_status == ExtractionStatus.PARTIAL_SUCCESS:
                if not self.observations:
                    raise ValueError("ExtractionStatus.PARTIAL_SUCCESS requires at least one valid observation.")
                if not self.diagnostics:
                    raise ValueError("ExtractionStatus.PARTIAL_SUCCESS requires at least one diagnostic.")

            # Invariant: SUCCESS cannot contain ERROR diagnostics
            if self.extraction_status == ExtractionStatus.SUCCESS:
                error_diags = [d for d in self.diagnostics if getattr(d, "severity", None) == "ERROR" or (isinstance(d, dict) and d.get("severity") == "ERROR")]
                if error_diags:
                    raise ValueError("ExtractionStatus.SUCCESS cannot contain ERROR diagnostics; use PARTIAL_SUCCESS or FAILED.")

            # Invariant: SUCCESS_EMPTY requires observations to be empty
            if self.extraction_status == ExtractionStatus.SUCCESS_EMPTY and self.observations:
                raise ValueError("ExtractionStatus.SUCCESS_EMPTY cannot contain observations; use SUCCESS or PARTIAL_SUCCESS.")

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class NormalizedObservation:
        # Original Observation Data (Preserved verbatim)
        raw_label: str
        original_value_text: str
        original_detected_value: Optional[float] = None
        original_unit: Optional[str] = None

        # Canonical Biomarker Resolution
        canonical_metric_id: Optional[str] = None
        canonical_biomarker_name: Optional[str] = None
        loinc_code: Optional[str] = None

        # Normalized Measurements
        normalized_value: Optional[float] = None
        normalized_unit: Optional[str] = None

        # Provenance Tracking
        source_document_id: Optional[str] = None
        source_location: Optional[SourceLocation] = None
        conversion_audit: Optional[ConversionAudit] = None

        # Validation & Clinical Governance Status
        ingestion_status: IngestionStatus = IngestionStatus.INCONCLUSIVE
        validation_messages: List[str] = field(default_factory=list)
        inconclusive_reason: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class LabMetric:
        metric_id: str
        canonical_name: str
        category: str
        unit: str
        gender: str = "all"
        min_normal: Optional[float] = None
        max_normal: Optional[float] = None
        loinc_code: Optional[str] = None
        critical_low: Optional[float] = None
        critical_high: Optional[float] = None
        description: Optional[str] = None
        aliases: List[str] = field(default_factory=list)
        is_demographic_dependent: bool = False
        evaluation_status: str = "CONCLUSIVE"
        demographic_requirement_note: Optional[str] = None

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class ReferenceInterval:
        metric_id: str
        population: str
        gender: str
        age_min_years: float
        age_max_years: float
        pregnancy_status: str
        unit: str
        min_normal: float
        max_normal: float
        interval_context_note: str
        source_reference: str
        verification_status: str
        interval_id: Optional[int] = None
        interval_tier: str = "PRIMARY_POPULATION_BENCHMARK"
        analytical_method_tag: str = "ALL_METHODS"

    @dataclass
    class CriticalLimit:
        metric_id: str
        unit: str
        limit_type: CriticalLimitType
        institutional_note: str
        clinical_urgency: str
        source_reference: str
        verification_status: str
        critical_limit_id: Optional[int] = None
        critical_low: Optional[float] = None
        critical_high: Optional[float] = None
        institutional_identifier: Optional[str] = None

    @dataclass
    class DiagnosticThreshold:
        metric_id: str
        condition_name: str
        cutoff_value: float
        comparison_operator: str
        unit: str
        requires_repeat_confirmation: bool
        clinical_criteria: str
        source_guideline: str
        verification_status: str
        diagnostic_id: Optional[int] = None

    @dataclass
    class TreatmentTarget:
        metric_id: str
        target_population: str
        goal_description: str
        target_value: float
        comparison_operator: str
        unit: str
        source_guideline: str
        verification_status: str
        target_id: Optional[int] = None

    @dataclass
    class RiskTier:
        metric_id: str
        tier_name: str
        tier_description: str
        unit: str
        clinical_significance: str
        source_classification: str
        verification_status: str
        risk_id: Optional[int] = None
        lower_bound: Optional[float] = None
        upper_bound: Optional[float] = None

    @dataclass
    class UnitConversion:
        metric_id: str
        alternative_unit: str
        standard_unit: str
        conversion_type: str
        canonical_conversion_formula: str
        formula_description: str
        handler_function_name: str
        conversion_id: Optional[int] = None
        conversion_factor: Optional[float] = None

    @dataclass
    class ClinicalContext:
        metric_id: str
        canonical_name: Optional[str] = None
        category: Optional[str] = None
        standard_unit: Optional[str] = None
        fasting_required: bool = False
        fasting_recommended_hours: Optional[float] = None
        fasting_details: Optional[str] = "None"
        measurement_type: Optional[str] = "Quantitative"
        methodology: Optional[str] = "Automated Spectrophotometry"
        equation_description: Optional[str] = None
        longitudinal_requirements: Optional[str] = None
        clinical_limitations: Optional[str] = None
        gestational_applicability_type: GestationalApplicabilityType = GestationalApplicabilityType.UNKNOWN
        gestational_contraindication_note: Optional[str] = None
        primary_source_organization: Optional[str] = "Clinical Laboratory Standards"
        primary_document_title: Optional[str] = "Reference Standard Guideline"
        publication_year: Optional[int] = 2024
        source_url: Optional[str] = "https://loinc.org"
        provenance_verification_status: Optional[str] = "VERIFIED"
        provenance_clinical_notes: Optional[str] = None

    @dataclass
    class PatientContext:
        age_years: Optional[float] = None
        biological_sex: Optional[str] = None
        is_pregnant: Optional[bool] = None
        gestational_age_weeks: Optional[float] = None
        gestational_trimester: Optional[int] = None
        measurement_type: Optional[str] = None
        analytical_method: Optional[str] = None
        institutional_context: Optional[str] = None
        fasting_confirmed: Optional[bool] = None
        pregnancy_status: Optional[str] = None

        def __post_init__(self):
            if self.pregnancy_status is not None and self.is_pregnant is None:
                ps_upper = str(self.pregnancy_status).strip().upper()
                if ps_upper == "PREGNANT":
                    self.is_pregnant = True
                elif ps_upper in ("NOT_PREGNANT", "NON_PREGNANT", "FALSE"):
                    self.is_pregnant = False
                elif ps_upper in ("UNKNOWN", "UNSTATED"):
                    self.is_pregnant = None

    @dataclass
    class IntervalSelectionResult:
        is_conclusive: bool
        interval: Optional[ReferenceInterval] = None
        critical_limit: Optional[CriticalLimit] = None
        inconclusive_code: Optional[str] = None
        inconclusive_reason: Optional[str] = None
        selection_audit_trail: List[str] = field(default_factory=list)

    @dataclass
    class ClinicalProtocol:
        protocol_id: str
        condition_id: str
        condition_name: str
        category: str
        summary_narrative: str
        dietary_guidelines: List[str] = field(default_factory=list)
        activity_guidelines: List[str] = field(default_factory=list)
        contraindications_to_avoid: List[str] = field(default_factory=list)
        physician_discussion_questions: List[str] = field(default_factory=list)
        escalation_flag: bool = False

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class ClinicalFinding:
        metric_id: str
        biomarker_name: str
        category: str
        unit: str
        reference_range_text: str
        status: MetricStatus
        severity: SeverityLevel
        gauge_percent: int
        is_abnormal: bool
        is_critical: bool
        clinical_note: str
        detected_value: Optional[float] = None
        associated_protocol_ids: List[str] = field(default_factory=list)
        diagnostic_alerts: List[str] = field(default_factory=list)
        critical_alert_info: Optional[Dict[str, Any]] = None
        conversion_applied: Optional[Dict[str, Any]] = None

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)

    @dataclass
    class AnalysisReport:
        status: str
        health_score: int
        risk_level: str
        risk_description: str
        total_metrics: int
        normal_metrics: int
        abnormal_metrics: int
        critical_metrics: int
        inconclusive_metrics: int
        findings: List[ClinicalFinding]
        protocols_applied: List[ClinicalProtocol]
        clinical_narrative: str
        dietary_recommendations: List[str]
        activity_recommendations: List[str]
        contraindications_to_avoid: List[str]
        physician_escalations: List[str]

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)
