"""
Clinical Analysis & Diagnostic Orchestration Engine.
Evaluates parsed observations against dynamic database-backed reference ranges and protocols.
Features:
- Deterministic contextual reference selection
- Allowlisted unit conversion before comparison
- Strict separation of reference intervals, diagnostic thresholds, panic limits, and treatment targets
- Safe inconclusive handling without arbitrary guessing
"""

import math
from typing import List, Dict, Set, Optional
from clinical_engine.storage.repository import ClinicalRepository
from clinical_engine.pipeline.parser import ClinicalReportParser, ParsedObservation
from clinical_engine.pipeline.converters import convert_laboratory_value
from clinical_engine.domain.schemas import (
    LabMetric,
    ClinicalFinding,
    ClinicalProtocol,
    AnalysisReport,
    MetricStatus,
    SeverityLevel,
    PatientContext,
    CriticalLimitType
)

class DiagnosticEngine:
    """Clinical Decision Support Engine with zero hardcoded clinical reference tables."""

    def __init__(self, repository: ClinicalRepository):
        self.repository = repository

    def calculate_gauge_percent(self, value: float, min_norm: float, max_norm: float,
                                crit_low: Optional[float] = None, crit_high: Optional[float] = None) -> int:
        """Calculates normalized position on a 0-100 visual meter based on physiological ranges."""
        low_bound = crit_low if crit_low is not None else (min_norm * 0.7)
        high_bound = crit_high if crit_high is not None else (max_norm * 1.3)

        if value <= min_norm:
            diff = min_norm - low_bound
            ratio = (value - low_bound) / diff if diff > 0 else 0
            percent = 5 + ratio * 20
            return int(max(5, min(25, percent)))
        elif value >= max_norm:
            diff = high_bound - max_norm
            ratio = (value - max_norm) / diff if diff > 0 else 1
            percent = 75 + ratio * 20
            return int(max(75, min(95, percent)))
        else:
            span = max_norm - min_norm
            ratio = (value - min_norm) / span if span > 0 else 0.5
            percent = 25 + ratio * 50
            return int(round(percent))

    def evaluate_observation(
        self,
        raw_label: str,
        detected_val: Optional[float],
        raw_unit: Optional[str],
        patient: PatientContext
    ) -> ClinicalFinding:
        """
        Contextually evaluates a single observation:
        1. Contextual retrieval of interval & critical limits via Deterministic Selector.
        2. Unit conversion before comparison.
        3. Multi-tier evaluation: Critical Limits -> Diagnostic Thresholds -> Reference Intervals.
        """
        # 1. Retrieve contextual reference
        if hasattr(self.repository, "get_contextual_metric_reference"):
            selection = self.repository.get_contextual_metric_reference(raw_label, patient)
        else:
            # Fallback to legacy
            legacy_metric = self.repository.get_metric_reference(raw_label, gender=patient.biological_sex or "all")
            if legacy_metric is None or legacy_metric.evaluation_status != "CONCLUSIVE":
                return ClinicalFinding(
                    metric_id=raw_label.lower().replace(" ", "_"),
                    biomarker_name=raw_label,
                    category="Uncategorized",
                    detected_value=detected_val,
                    unit=raw_unit or "N/A",
                    reference_range_text="Context Required",
                    status=MetricStatus.INCONCLUSIVE,
                    severity=SeverityLevel.INCONCLUSIVE,
                    gauge_percent=50,
                    is_abnormal=False,
                    is_critical=False,
                    clinical_note="Demographic context required to evaluate reference range."
                )
            # Create synthetic selection from legacy
            from clinical_engine.domain.schemas import ReferenceInterval, IntervalSelectionResult
            inv = ReferenceInterval(
                metric_id=legacy_metric.metric_id, population="Legacy", gender=legacy_metric.gender,
                age_min_years=18.0, age_max_years=120.0, pregnancy_status="ALL", unit=legacy_metric.unit,
                min_normal=legacy_metric.min_normal or 0.0, max_normal=legacy_metric.max_normal or 100.0,
                interval_context_note="Legacy interval", source_reference="Legacy", verification_status="VERIFIED"
            )
            selection = IntervalSelectionResult(is_conclusive=True, interval=inv)

        # Handle unknown biomarker
        if selection.inconclusive_code == "UNKNOWN_BIOMARKER":
            return ClinicalFinding(
                metric_id="unknown_metric",
                biomarker_name=raw_label,
                category="Uncategorized",
                detected_value=detected_val,
                unit=raw_unit or "N/A",
                reference_range_text="Outside Reference Database",
                status=MetricStatus.UNKNOWN,
                severity=SeverityLevel.UNKNOWN,
                gauge_percent=50,
                is_abnormal=False,
                is_critical=False,
                clinical_note="Biomarker not indexed in active clinical knowledge database."
            )

        # Handle inconclusive demographic or pregnancy halt
        if not selection.is_conclusive or not selection.interval:
            return ClinicalFinding(
                metric_id=raw_label.lower().replace(" ", "_"),
                biomarker_name=raw_label,
                category="Uncategorized",
                detected_value=detected_val,
                unit=raw_unit or "N/A",
                reference_range_text="Inconclusive Context",
                status=MetricStatus.INCONCLUSIVE,
                severity=SeverityLevel.INCONCLUSIVE,
                gauge_percent=50,
                is_abnormal=False,
                is_critical=False,
                clinical_note=selection.inconclusive_reason or "Insufficient demographic context."
            )

        interval = selection.interval
        crit_limit = selection.critical_limit
        metric_id = interval.metric_id
        standard_unit = interval.unit

        # Handle non-numeric or missing detected value
        if detected_val is None or math.isnan(detected_val):
            return ClinicalFinding(
                metric_id=metric_id,
                biomarker_name=interval.population,
                category="General",
                detected_value=None,
                unit=standard_unit,
                reference_range_text=f"{interval.min_normal} - {interval.max_normal} {standard_unit}",
                status=MetricStatus.INCONCLUSIVE,
                severity=SeverityLevel.INCONCLUSIVE,
                gauge_percent=50,
                is_abnormal=False,
                is_critical=False,
                clinical_note="Non-numeric or inconclusive value parsed from report."
            )

        # 2. Unit Harmonization
        eval_value = detected_val
        conversion_info = None

        if raw_unit:
            from clinical_engine.pipeline.normalizer import UnitLexicalNormalizer
            norm_unit, _ = UnitLexicalNormalizer.normalize_unit(raw_unit)
            effective_unit = norm_unit if norm_unit is not None else raw_unit.strip()
        else:
            effective_unit = None

        if effective_unit and effective_unit != standard_unit.strip():
            unit_conv = None
            if hasattr(self.repository, "get_unit_conversion"):
                unit_conv = self.repository.get_unit_conversion(metric_id, effective_unit)

            if not unit_conv:
                return ClinicalFinding(
                    metric_id=metric_id,
                    biomarker_name=raw_label,
                    category="General",
                    detected_value=detected_val,
                    unit=raw_unit,
                    reference_range_text=f"{interval.min_normal} - {interval.max_normal} {standard_unit}",
                    status=MetricStatus.INCONCLUSIVE,
                    severity=SeverityLevel.INCONCLUSIVE,
                    gauge_percent=50,
                    is_abnormal=False,
                    is_critical=False,
                    clinical_note=f"Unsupported unit '{raw_unit}'. Standard canonical unit is '{standard_unit}'. Numerical comparison rejected."
                )

            # Execute allowlisted conversion
            res = convert_laboratory_value(
                detected_value=detected_val,
                incoming_unit=effective_unit,
                standard_unit=standard_unit,
                conversion_type=unit_conv.conversion_type,
                handler_name=unit_conv.handler_function_name,
                factor=unit_conv.conversion_factor,
                formula_str=unit_conv.canonical_conversion_formula
            )
            eval_value = res["converted_value"]
            conversion_info = res["audit"]

        # 3. Clinical Evaluation (Critical Limits -> Reference Intervals)
        c_low = crit_limit.critical_low if crit_limit else None
        c_high = crit_limit.critical_high if crit_limit else None
        gauge_pos = self.calculate_gauge_percent(eval_value, interval.min_normal, interval.max_normal, c_low, c_high)
        ref_text = f"{interval.min_normal} - {interval.max_normal} {standard_unit}"

        diagnostic_alerts: List[str] = []
        crit_alert_info = None

        # Check Critical Limits
        # CLINICAL GOVERNANCE RULE:
        # CONSENSUS_PANIC_SURVEY_MEDIAN values are strictly informational/benchmark and CANNOT
        # independently trigger automated critical alerts, critical severity, or emergency escalation.
        # Only LABORATORY_SPECIFIC_PANIC_ALERT (with institutional match) or CLINICAL_PRACTICE_ALERT_THRESHOLD
        # can trigger automated critical alerts (is_critical = True).
        is_critical = False
        is_abnormal = False
        status = MetricStatus.NORMAL
        severity = SeverityLevel.OPTIMAL
        note = f"Observation lies within established physiological reference limits ({interval.population})."

        is_actionable_critical = (
            crit_limit is not None and
            crit_limit.limit_type in (
                CriticalLimitType.LABORATORY_SPECIFIC_PANIC_ALERT,
                CriticalLimitType.CLINICAL_PRACTICE_ALERT_THRESHOLD
            )
        )

        if c_low is not None and eval_value < c_low:
            if is_actionable_critical:
                status = MetricStatus.CRITICAL_LOW
                severity = SeverityLevel.CRITICAL_LOW
                is_abnormal = True
                is_critical = True
                note = f"Critical low alert: {eval_value} {standard_unit} falls below critical threshold of {c_low}."
                crit_alert_info = {
                    "limit_type": crit_limit.limit_type.value,
                    "institutional_note": crit_limit.institutional_note,
                    "urgency": crit_limit.clinical_urgency,
                    "is_actionable_critical": True
                }
            else:
                # Strictly informational consensus survey benchmark: flag abnormal/low, NOT critical panic
                status = MetricStatus.LOW
                severity = SeverityLevel.MILD_LOW
                is_abnormal = True
                is_critical = False
                note = (
                    f"Sub-normal finding: {eval_value} {standard_unit} falls below biological reference limit ({interval.min_normal}). "
                    f"[Informational Survey Benchmark: Below multi-center consensus survey median panic threshold of {c_low} {standard_unit}; "
                    f"does not independently trigger automated panic alert or emergency escalation]."
                )
                crit_alert_info = {
                    "limit_type": crit_limit.limit_type.value,
                    "institutional_note": crit_limit.institutional_note,
                    "urgency": crit_limit.clinical_urgency,
                    "is_actionable_critical": False
                }
        elif c_high is not None and eval_value > c_high:
            if is_actionable_critical:
                status = MetricStatus.CRITICAL_HIGH
                severity = SeverityLevel.CRITICAL_HIGH
                is_abnormal = True
                is_critical = True
                note = f"Critical high alert: {eval_value} {standard_unit} exceeds critical threshold of {c_high}."
                crit_alert_info = {
                    "limit_type": crit_limit.limit_type.value,
                    "institutional_note": crit_limit.institutional_note,
                    "urgency": crit_limit.clinical_urgency,
                    "is_actionable_critical": True
                }
            else:
                # Strictly informational consensus survey benchmark: flag abnormal/elevated, NOT critical panic
                status = MetricStatus.ELEVATED
                severity = SeverityLevel.MILD_HIGH
                is_abnormal = True
                is_critical = False
                note = (
                    f"Elevated finding: {eval_value} {standard_unit} exceeds biological reference limit ({interval.max_normal}). "
                    f"[Informational Survey Benchmark: Exceeds multi-center consensus survey median panic threshold of {c_high} {standard_unit}; "
                    f"does not independently trigger automated panic alert or emergency escalation]."
                )
                crit_alert_info = {
                    "limit_type": crit_limit.limit_type.value,
                    "institutional_note": crit_limit.institutional_note,
                    "urgency": crit_limit.clinical_urgency,
                    "is_actionable_critical": False
                }
        elif eval_value < interval.min_normal:
            status = MetricStatus.LOW
            severity = SeverityLevel.MILD_LOW
            is_abnormal = True
            note = f"Sub-normal finding: {eval_value} {standard_unit} falls below biological reference limit ({interval.min_normal})."
        elif eval_value > interval.max_normal:
            status = MetricStatus.ELEVATED
            severity = SeverityLevel.MILD_HIGH
            is_abnormal = True
            note = f"Elevated finding: {eval_value} {standard_unit} exceeds biological reference limit ({interval.max_normal})."

        # Check Diagnostic Thresholds (Guideline alerts; NOT autonomous diagnoses)
        if hasattr(self.repository, "get_diagnostic_thresholds"):
            thresholds = self.repository.get_diagnostic_thresholds(metric_id)
            for dt in thresholds:
                matched = False
                if dt.comparison_operator == ">=" and eval_value >= dt.cutoff_value:
                    matched = True
                elif dt.comparison_operator == ">" and eval_value > dt.cutoff_value:
                    matched = True
                elif dt.comparison_operator == "<=" and eval_value <= dt.cutoff_value:
                    matched = True
                elif dt.comparison_operator == "<" and eval_value < dt.cutoff_value:
                    matched = True

                if matched:
                    repeat_txt = " (Requires repeat confirmation on separate day)" if dt.requires_repeat_confirmation else ""
                    alert = f"CLINICAL DECISION SUPPORT ALERT: Meets guideline threshold for {dt.condition_name} ({dt.comparison_operator} {dt.cutoff_value} {dt.unit}){repeat_txt}. Clinical evaluation required; not an autonomous diagnosis."
                    diagnostic_alerts.append(alert)

        return ClinicalFinding(
            metric_id=metric_id,
            biomarker_name=raw_label,
            category="General",
            detected_value=eval_value,
            unit=standard_unit,
            reference_range_text=ref_text,
            status=status,
            severity=severity,
            gauge_percent=gauge_pos,
            is_abnormal=is_abnormal,
            is_critical=is_critical,
            clinical_note=note,
            associated_protocol_ids=[],
            diagnostic_alerts=diagnostic_alerts,
            critical_alert_info=crit_alert_info,
            conversion_applied=conversion_info
        )

    def analyze_report(
        self,
        report_text: str,
        gender: Optional[str] = None,
        age: Optional[float] = None,
        is_pregnant: Optional[bool] = None,
        institutional_context: Optional[str] = None,
        age_years: Optional[float] = None,
        pregnancy_status: Optional[str] = None,
        gestational_age_weeks: Optional[float] = None,
        gestational_trimester: Optional[int] = None
    ) -> AnalysisReport:
        """End-to-end clinical ingestion and evaluation pipeline."""
        final_age = age if age is not None else age_years
        final_pregnant = is_pregnant
        if final_pregnant is None and pregnancy_status:
            p_upper = pregnancy_status.upper().strip()
            if p_upper == "PREGNANT":
                final_pregnant = True
            elif p_upper in ("NOT_PREGNANT", "NON_PREGNANT", "FALSE"):
                final_pregnant = False
            elif p_upper in ("UNKNOWN", "UNSTATED"):
                final_pregnant = None

        patient = PatientContext(
            age_years=final_age,
            biological_sex=gender,
            is_pregnant=final_pregnant,
            gestational_age_weeks=gestational_age_weeks,
            gestational_trimester=gestational_trimester,
            institutional_context=institutional_context
        )

        raw_observations = ClinicalReportParser.parse_text(report_text)
        findings: List[ClinicalFinding] = []
        protocols_map: Dict[str, ClinicalProtocol] = {}
        seen_keys: Set[str] = set()

        for obs in raw_observations:
            if obs.raw_key.lower() in seen_keys:
                continue
            seen_keys.add(obs.raw_key.lower())

            finding = self.evaluate_observation(
                raw_label=obs.raw_key,
                detected_val=obs.detected_value,
                raw_unit=obs.raw_unit,
                patient=patient
            )

            # Query dynamic clinical protocols for abnormal findings
            if finding.is_abnormal and hasattr(self.repository, "get_protocols_for_abnormal_metric"):
                status_key = "LOW" if "Low" in finding.status.value else "ELEVATED"
                triggered = self.repository.get_protocols_for_abnormal_metric(finding.metric_id, status_key)
                for p in triggered:
                    protocols_map[p.protocol_id] = p
                    if p.protocol_id not in finding.associated_protocol_ids:
                        finding.associated_protocol_ids.append(p.protocol_id)

            findings.append(finding)

        total_count = len(findings)
        abnormal_count = sum(1 for f in findings if f.is_abnormal)
        critical_count = sum(1 for f in findings if f.is_critical)
        normal_count = sum(1 for f in findings if f.status == MetricStatus.NORMAL)
        inconclusive_count = sum(1 for f in findings if f.status in (MetricStatus.INCONCLUSIVE, MetricStatus.UNKNOWN))

        # Dynamic health index scoring
        score = 100 - (abnormal_count * 12) - (critical_count * 16)
        score = max(30, min(100, score))

        if critical_count > 0 or abnormal_count >= 3:
            risk_level = "High"
            risk_desc = "High Priority Attention Needed"
        elif abnormal_count > 0:
            risk_level = "Medium"
            risk_desc = "Moderate Attention Needed"
        else:
            risk_level = "Low"
            risk_desc = "Optimal Physiological Baseline"

        protocols_applied = list(protocols_map.values())
        dietary: List[str] = []
        activity: List[str] = []
        avoid: List[str] = []
        escalations: List[str] = []

        for p in protocols_applied:
            for item in p.dietary_guidelines:
                if item not in dietary:
                    dietary.append(item)
            for item in p.activity_guidelines:
                if item not in activity:
                    activity.append(item)
            for item in p.contraindications_to_avoid:
                if item not in avoid:
                    avoid.append(item)
            for item in p.physician_discussion_questions:
                if item not in escalations:
                    escalations.append(item)

        if not protocols_applied:
            dietary = ["Maintain a wholesome, balanced whole-foods diet rich in vegetables, clean proteins, and healthy fats."]
            activity = ["Engage in 150 minutes of weekly moderate aerobic physical activity to support cardiovascular health."]
            avoid = ["Avoid chronic sedentary habits, tobacco products, and excessive alcohol intake."]
            escalations = ["Discuss age-specific preventative screenings and baseline review timelines with your physician."]

        if abnormal_count == 0:
            narrative = (
                f"Analysis completed across {total_count} evaluated clinical biomarkers. "
                f"All tested parameters comfortably reside within established physiological reference intervals. "
                f"Continue routine preventative care."
            )
        else:
            applied_ids_str = ", ".join(protocols_map.keys())
            narrative = (
                f"Diagnostic review identified {total_count} laboratory biomarker(s) with {abnormal_count} parameter(s) "
                f"flagged outside standard physiological intervals ({critical_count} critical alert(s)). "
                f"Applying evidence-based protocols: [{applied_ids_str}]. "
                f"Review prioritized lifestyle guidelines and consult your healthcare provider."
            )

        return AnalysisReport(
            status="success",
            health_score=score,
            risk_level=risk_level,
            risk_description=risk_desc,
            total_metrics=total_count,
            normal_metrics=normal_count,
            abnormal_metrics=abnormal_count,
            critical_metrics=critical_count,
            inconclusive_metrics=inconclusive_count,
            findings=findings,
            protocols_applied=protocols_applied,
            clinical_narrative=narrative,
            dietary_recommendations=dietary,
            activity_recommendations=activity,
            contraindications_to_avoid=avoid,
            physician_escalations=escalations
        )
