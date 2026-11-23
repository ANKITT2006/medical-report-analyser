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
        fasting_required: bool
        fasting_recommended_hours: Optional[float] = None
        fasting_details: str
        measurement_type: str
        methodology: str
        equation_description: Optional[str] = None
        longitudinal_requirements: Optional[str] = None
        clinical_limitations: Optional[str] = None
        gestational_applicability_type: GestationalApplicabilityType = GestationalApplicabilityType.UNKNOWN
        gestational_contraindication_note: Optional[str] = None
        primary_source_organization: str
        primary_document_title: str
        publication_year: int
        source_url: str
        provenance_verification_status: str
        provenance_clinical_notes: Optional[str] = None

    class PatientContext(BaseModel):
        age_years: Optional[float] = None
        biological_sex: Optional[str] = None       # 'male', 'female', or None
        is_pregnant: Optional[bool] = None         # True, False, or None
        gestational_trimester: Optional[int] = None # 1, 2, 3, or None
        measurement_type: Optional[str] = None
        analytical_method: Optional[str] = None
        institutional_context: Optional[str] = None # e.g. 'MGH'
        fasting_confirmed: Optional[bool] = None   # True, False, or None

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
        fasting_required: bool
        fasting_details: str
        measurement_type: str
        methodology: str
        primary_source_organization: str
        primary_document_title: str
        publication_year: int
        source_url: str
        provenance_verification_status: str
        fasting_recommended_hours: Optional[float] = None
        equation_description: Optional[str] = None
        longitudinal_requirements: Optional[str] = None
        clinical_limitations: Optional[str] = None
        gestational_applicability_type: GestationalApplicabilityType = GestationalApplicabilityType.UNKNOWN
        gestational_contraindication_note: Optional[str] = None
        provenance_clinical_notes: Optional[str] = None

    @dataclass
    class PatientContext:
        age_years: Optional[float] = None
        biological_sex: Optional[str] = None
        is_pregnant: Optional[bool] = None
        gestational_trimester: Optional[int] = None
        measurement_type: Optional[str] = None
        analytical_method: Optional[str] = None
        institutional_context: Optional[str] = None
        fasting_confirmed: Optional[bool] = None

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
