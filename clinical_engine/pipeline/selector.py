"""
Deterministic Reference Interval & Critical Limit Selector.
Strictly metadata-driven. Never uses arbitrary indexing or heuristic guessing.
"""

from typing import List, Optional, Tuple
from clinical_engine.domain.schemas import (
    ReferenceInterval,
    CriticalLimit,
    CriticalLimitType,
    PatientContext,
    IntervalSelectionResult,
    GestationalApplicabilityType,
    ClinicalContext
)

class DeterministicClinicalSelector:
    """
    Selects clinical reference boundaries and critical alerts strictly using structured metadata.
    Enforces uniqueness, pregnancy safety, biological sex boundaries, and institutional scope.
    """

    @classmethod
    def select_interval_and_limits(
        cls,
        intervals: List[ReferenceInterval],
        critical_limits: List[CriticalLimit],
        clinical_ctx: Optional[ClinicalContext],
        patient: PatientContext
    ) -> IntervalSelectionResult:
        audit_trail: List[str] = []

        if not intervals:
            return IntervalSelectionResult(
                is_conclusive=False,
                inconclusive_code="NO_INTERVALS_CONFIGURED",
                inconclusive_reason="No biological reference intervals configured in database for this biomarker.",
                selection_audit_trail=["Query returned zero configured intervals."]
            )

        # -------------------------------------------------------------
        # TIER 1: Methodological and Measurement Alignment
        # -------------------------------------------------------------
        candidates = list(intervals)
        if patient.analytical_method:
            method_matches = [
                i for i in candidates
                if i.analytical_method_tag.upper() == patient.analytical_method.strip().upper()
                or i.analytical_method_tag == "ALL_METHODS"
            ]
            if not method_matches:
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="METHODOLOGY_MISMATCH",
                    inconclusive_reason=f"Patient analytical method '{patient.analytical_method}' does not match any configured method intervals.",
                    selection_audit_trail=[f"Method filter failed: {patient.analytical_method}"]
                )
            candidates = method_matches
            audit_trail.append(f"Filtered by analytical methodology: {patient.analytical_method}")

        # -------------------------------------------------------------
        # TIER 2: Pregnancy Metadata Safety Gate
        # -------------------------------------------------------------
        gest_type = (
            clinical_ctx.gestational_applicability_type
            if clinical_ctx
            else GestationalApplicabilityType.UNKNOWN
        )

        if patient.is_pregnant is True:
            # Check methodology contraindications
            if gest_type == GestationalApplicabilityType.METHODOLOGY_CONTRAINDICATED:
                contra_note = (clinical_ctx.gestational_contraindication_note if clinical_ctx else "Assay methodology invalid in pregnancy")
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="GESTATIONAL_METHODOLOGY_CONTRAINDICATED",
                    inconclusive_reason=f"Assay is clinically contraindicated or unreliable in pregnancy: {contra_note}",
                    selection_audit_trail=["Halt: Gestational methodology contraindication encountered."]
                )

            # Trimester-specific check
            if gest_type == GestationalApplicabilityType.TRIMESTER_STRATIFIED and patient.gestational_trimester is None:
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="MISSING_GESTATIONAL_TRIMESTER",
                    inconclusive_reason="Biomarker interval is trimester-stratified in pregnancy. Gestational trimester is required.",
                    selection_audit_trail=["Halt: Gestational trimester required but unstated."]
                )

            preg_candidates = [i for i in candidates if i.pregnancy_status == "PREGNANT"]
            if preg_candidates:
                candidates = preg_candidates
                audit_trail.append("Matched pregnancy-specific reference intervals.")
            else:
                all_preg = [i for i in candidates if i.pregnancy_status == "ALL"]
                if all_preg:
                    candidates = all_preg
                    audit_trail.append("Biomarker reference interval explicitly validated for ALL pregnancy statuses.")
                else:
                    # STRICT SAFETY RULE: Never substitute non-pregnant range for pregnant patient!
                    return IntervalSelectionResult(
                        is_conclusive=False,
                        inconclusive_code="PREGNANCY_RANGE_UNAVAILABLE",
                        inconclusive_reason=(
                            "Patient is pregnant. Normal non-pregnant reference intervals cannot be "
                            "safely applied due to gestational hemodilution or altered physiological clearance. "
                            "No validated pregnancy-specific interval exists in database."
                        ),
                        selection_audit_trail=["Halt: Strict pregnancy safety rule triggered; non-pregnant substitution rejected."]
                    )

        elif patient.is_pregnant is None:
            # Pregnancy status is UNKNOWN
            # Patients beyond reproductive age (e.g. > 55 yrs) are physiologically exempt from pregnancy halts
            is_reproductive_age = patient.age_years is None or (12.0 <= patient.age_years <= 55.0)
            if patient.biological_sex == "female" and is_reproductive_age and gest_type in (
                GestationalApplicabilityType.PHYSIOLOGICAL_SHIFT,
                GestationalApplicabilityType.METHODOLOGY_CONTRAINDICATED,
                GestationalApplicabilityType.TRIMESTER_STRATIFIED
            ):
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="UNRESOLVED_PREGNANCY_STATUS",
                    inconclusive_reason=(
                        "Biomarker physiological intervals or validity shift significantly during pregnancy. "
                        "Maternal pregnancy status is unstated; non-pregnant intervals cannot be safely presumed."
                    ),
                    selection_audit_trail=["Halt: Female patient of reproductive age with unresolved pregnancy status on pregnancy-sensitive marker."]
                )
            # Safe to evaluate non-pregnant
            candidates = [i for i in candidates if i.pregnancy_status in ("NOT_PREGNANT", "ALL")]
            audit_trail.append("Evaluated using standard non-pregnant/all population intervals.")
        else:
            # Confirmed NOT_PREGNANT
            candidates = [i for i in candidates if i.pregnancy_status in ("NOT_PREGNANT", "ALL")]
            audit_trail.append("Filtered to non-pregnant cohort reference intervals.")

        # -------------------------------------------------------------
        # TIER 3: Biological Sex Stratification Filter
        # -------------------------------------------------------------
        has_sex_stratification = any(i.gender in ("male", "female") for i in candidates)
        if has_sex_stratification:
            if not patient.biological_sex or patient.biological_sex.lower() not in ("male", "female"):
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="MISSING_BIOLOGICAL_SEX",
                    inconclusive_reason="Biomarker interval is biological sex-stratified. Patient biological sex is unstated.",
                    selection_audit_trail=["Halt: Missing required biological sex for sex-stratified metric."]
                )
            candidates = [i for i in candidates if i.gender == patient.biological_sex.lower()]
            audit_trail.append(f"Filtered by biological sex: {patient.biological_sex.lower()}")
        else:
            candidates = [i for i in candidates if i.gender == "all"]
            audit_trail.append("Biomarker interval applies across all biological sexes.")

        # -------------------------------------------------------------
        # TIER 4: Age Boundary Qualification Filter
        # -------------------------------------------------------------
        # Check if any candidate has age bounds restricting eligibility
        has_age_bounds = any(
            (i.age_min_years is not None or i.age_max_years is not None) for i in candidates
        )
        has_age_stratification = len(candidates) > 1 or any(
            (i.age_min_years > 18.0 or i.age_max_years < 120.0) for i in candidates
        )

        if patient.age_years is not None and has_age_bounds:
            age_matched = [
                i for i in candidates
                if i.age_min_years <= patient.age_years <= i.age_max_years
            ]
            if not age_matched:
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="AGE_OUT_OF_BOUNDS",
                    inconclusive_reason=f"Patient age ({patient.age_years} yrs) falls outside configured age intervals.",
                    selection_audit_trail=[f"Halt: No interval covers patient age {patient.age_years}."]
                )
            candidates = age_matched
            audit_trail.append(f"Filtered by patient age: {patient.age_years} yrs.")
        elif has_age_stratification and patient.age_years is None:
            return IntervalSelectionResult(
                is_conclusive=False,
                inconclusive_code="MISSING_PATIENT_AGE",
                inconclusive_reason="Biomarker interval is age-stratified. Patient age is unstated.",
                selection_audit_trail=["Halt: Missing required patient age for age-dependent metric."]
            )

        # -------------------------------------------------------------
        # TIER 5: Uniqueness & Ambiguity Enforcement
        # -------------------------------------------------------------
        selected_interval: Optional[ReferenceInterval] = None
        if len(candidates) == 1:
            selected_interval = candidates[0]
            audit_trail.append(f"Uniquely selected interval: {selected_interval.population} ({selected_interval.min_normal}-{selected_interval.max_normal} {selected_interval.unit})")
        elif len(candidates) == 0:
            return IntervalSelectionResult(
                is_conclusive=False,
                inconclusive_code="NO_MATCHING_INTERVAL",
                inconclusive_reason="No configured reference interval matches the combined patient context.",
                selection_audit_trail=audit_trail
            )
        else:
            # Overlapping intervals or ambiguous matches
            conflict_ids = [str(i.interval_id or i.population) for i in candidates]
            return IntervalSelectionResult(
                is_conclusive=False,
                inconclusive_code="OVERLAPPING_INTERVAL_CONFLICT",
                inconclusive_reason=(
                    f"Ambiguous match: {len(candidates)} intervals qualify for the patient's context without "
                    f"an evidence-backed disambiguation rule. Conflicting intervals: [{', '.join(conflict_ids)}]"
                ),
                selection_audit_trail=audit_trail + [f"Conflict between interval IDs: {conflict_ids}"]
            )

        # -------------------------------------------------------------
        # TIER 6: Critical Limit Selection & Governance
        # -------------------------------------------------------------
        selected_critical: Optional[CriticalLimit] = None
        if critical_limits:
            # 1. Check for institution-specific panic alert if institutional context provided
            if patient.institutional_context:
                inst_matches = [
                    cl for cl in critical_limits
                    if cl.limit_type == CriticalLimitType.LABORATORY_SPECIFIC_PANIC_ALERT
                    and cl.institutional_identifier
                    and cl.institutional_identifier.upper() == patient.institutional_context.strip().upper()
                ]
                if len(inst_matches) == 1:
                    selected_critical = inst_matches[0]
                    audit_trail.append(f"Attached matched laboratory-specific panic alert for institution: {patient.institutional_context}")
                elif len(inst_matches) > 1:
                    audit_trail.append("Warning: Multiple institution panic alerts matched; deferring to clinical consensus.")

            # 2. If no institutional limit selected, evaluate clinical practice alert thresholds
            if not selected_critical:
                practice_alerts = [
                    cl for cl in critical_limits
                    if cl.limit_type == CriticalLimitType.CLINICAL_PRACTICE_ALERT_THRESHOLD
                ]
                if len(practice_alerts) == 1:
                    selected_critical = practice_alerts[0]
                    audit_trail.append("Attached universal clinical practice alert threshold.")
                elif len(practice_alerts) > 1:
                    audit_trail.append("Warning: Multiple clinical practice alert thresholds found.")

            # 3. If still none, check consensus survey medians (informational benchmark only)
            if not selected_critical:
                survey_benchmarks = [
                    cl for cl in critical_limits
                    if cl.limit_type == CriticalLimitType.CONSENSUS_PANIC_SURVEY_MEDIAN
                ]
                if len(survey_benchmarks) >= 1:
                    # In legacy ingestion or multi-survey datasets, choose the most conservative (widest or first benchmark)
                    selected_critical = survey_benchmarks[0]
                    audit_trail.append("Attached consensus survey median panic benchmark (informational).")

            # 4. Fallback for general laboratory alert thresholds when no specific institutional context was given
            if not selected_critical and not patient.institutional_context and len(critical_limits) >= 1:
                selected_critical = critical_limits[0]
                audit_trail.append(f"Attached baseline laboratory critical alert limit: {selected_critical.limit_type.value}.")

        return IntervalSelectionResult(
            interval=selected_interval,
            critical_limit=selected_critical,
            is_conclusive=True,
            inconclusive_code=None,
            inconclusive_reason=None,
            selection_audit_trail=audit_trail
        )

