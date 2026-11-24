"""
Clinical Data Access Object (DAO) / Repository interfaces and SQL implementation.
Provides abstract decoupling for database persistence (SQLite / PostgreSQL compatible).
Fully reconciled with Phase 2 Canonical Reference Schemas.
"""

import abc
import json
import sqlite3
import os
from pathlib import Path
from typing import List, Optional, Any, Dict
from clinical_engine.domain.schemas import (
    LabMetric,
    ClinicalProtocol,
    ReferenceInterval,
    CriticalLimit,
    CriticalLimitType,
    DiagnosticThreshold,
    TreatmentTarget,
    RiskTier,
    UnitConversion,
    ClinicalContext,
    GestationalApplicabilityType,
    PatientContext,
    IntervalSelectionResult
)
from clinical_engine.storage.adapter import CanonicalReferenceAdapter


class ClinicalRepository(abc.ABC):
    """Abstract interface defining access to clinical knowledge datasets."""

    @abc.abstractmethod
    def get_metric_reference(self, test_name_or_code: str, gender: str = "all") -> Optional[LabMetric]:
        """Fetch standardized biological reference interval by test name, code, or alias."""
        pass

    @abc.abstractmethod
    def get_contextual_metric_reference(
        self, test_name_or_code: str, patient: PatientContext
    ) -> IntervalSelectionResult:
        """Fetch deterministic, demographic-specific biological reference interval and critical limits."""
        pass

    @abc.abstractmethod
    def list_all_metrics(self) -> List[LabMetric]:
        """List all registered clinical biomarkers."""
        pass

    @abc.abstractmethod
    def get_protocols_by_condition(self, condition_id: str) -> List[ClinicalProtocol]:
        """Fetch evidence-based clinical protocols by condition identifier."""
        pass

    @abc.abstractmethod
    def list_all_protocols(self) -> List[ClinicalProtocol]:
        """List all registered clinical protocols."""
        pass

    @abc.abstractmethod
    def bulk_load_dataset(self, data_or_path: Any) -> int:
        """Dynamically load and ingest dataset definitions (JSON/CSV/dict). Returns count of records inserted."""
        pass


class SQLClinicalRepository(ClinicalRepository):
    """
    SQLite / SQL-backed Clinical Knowledge Repository.
    Executes schema migrations and dynamic queries without in-memory hardcoding.
    """

    def __init__(self, db_path: str = "data/clinical_knowledge.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Create normalized relational schema for clinical metrics, aliases, intervals, and protocols."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 1. Base lab_metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lab_metrics (
                    metric_id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    standard_unit TEXT NOT NULL,
                    description TEXT NOT NULL,
                    loinc_code TEXT NOT NULL,
                    loinc_verification_status TEXT NOT NULL,
                    loinc_version TEXT NOT NULL,
                    loinc_component TEXT NOT NULL,
                    loinc_property TEXT NOT NULL,
                    loinc_system_specimen TEXT NOT NULL,
                    loinc_scale_type TEXT NOT NULL,
                    loinc_method_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. metric_aliases
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_aliases (
                    alias TEXT PRIMARY KEY,
                    metric_id TEXT NOT NULL,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 3. metric_reference_intervals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_reference_intervals (
                    interval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    population TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    age_min_years REAL NOT NULL,
                    age_max_years REAL NOT NULL,
                    pregnancy_status TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    min_normal REAL NOT NULL,
                    max_normal REAL NOT NULL,
                    interval_context_note TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    interval_tier TEXT NOT NULL DEFAULT 'PRIMARY_POPULATION_BENCHMARK',
                    analytical_method_tag TEXT NOT NULL DEFAULT 'ALL_METHODS',
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 4. metric_critical_limits
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_critical_limits (
                    critical_limit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    critical_low REAL,
                    critical_high REAL,
                    unit TEXT NOT NULL,
                    limit_type TEXT NOT NULL,
                    institutional_note TEXT NOT NULL,
                    clinical_urgency TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    institutional_identifier TEXT,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 5. metric_diagnostic_thresholds
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_diagnostic_thresholds (
                    diagnostic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    condition_name TEXT NOT NULL,
                    cutoff_value REAL NOT NULL,
                    comparison_operator TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    requires_repeat_confirmation INTEGER NOT NULL,
                    clinical_criteria TEXT NOT NULL,
                    source_guideline TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 6. metric_treatment_targets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_treatment_targets (
                    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    target_population TEXT NOT NULL,
                    goal_description TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    comparison_operator TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    source_guideline TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 7. metric_risk_thresholds
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_risk_thresholds (
                    risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    tier_name TEXT NOT NULL,
                    tier_description TEXT NOT NULL,
                    lower_bound REAL,
                    upper_bound REAL,
                    unit TEXT NOT NULL,
                    clinical_significance TEXT NOT NULL,
                    source_classification TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 8. metric_unit_conversions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_unit_conversions (
                    conversion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_id TEXT NOT NULL,
                    alternative_unit TEXT NOT NULL,
                    standard_unit TEXT NOT NULL,
                    conversion_type TEXT NOT NULL,
                    conversion_factor REAL,
                    canonical_conversion_formula TEXT NOT NULL,
                    formula_description TEXT NOT NULL,
                    handler_function_name TEXT NOT NULL,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE,
                    CONSTRAINT uq_metric_unit UNIQUE (metric_id, alternative_unit)
                )
            """)

            # 9. metric_clinical_context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metric_clinical_context (
                    metric_id TEXT PRIMARY KEY,
                    fasting_required INTEGER NOT NULL,
                    fasting_recommended_hours REAL,
                    fasting_details TEXT NOT NULL,
                    measurement_type TEXT NOT NULL,
                    methodology TEXT NOT NULL,
                    equation_description TEXT,
                    longitudinal_requirements TEXT,
                    clinical_limitations TEXT,
                    gestational_applicability_type TEXT NOT NULL,
                    gestational_contraindication_note TEXT,
                    primary_source_organization TEXT NOT NULL,
                    primary_document_title TEXT NOT NULL,
                    publication_year INTEGER NOT NULL,
                    source_url TEXT NOT NULL,
                    provenance_verification_status TEXT NOT NULL,
                    provenance_clinical_notes TEXT,
                    FOREIGN KEY (metric_id) REFERENCES lab_metrics(metric_id) ON DELETE CASCADE
                )
            """)

            # 10. Clinical Protocols & Mappings (Preserved)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clinical_protocols (
                    protocol_id TEXT PRIMARY KEY,
                    condition_id TEXT NOT NULL,
                    condition_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    summary_narrative TEXT NOT NULL,
                    dietary_guidelines_json TEXT,
                    activity_guidelines_json TEXT,
                    contraindications_json TEXT,
                    physician_questions_json TEXT,
                    escalation_flag INTEGER NOT NULL DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS condition_metric_mappings (
                    condition_id TEXT NOT NULL,
                    metric_id TEXT NOT NULL,
                    trigger_status TEXT NOT NULL,
                    PRIMARY KEY (condition_id, metric_id, trigger_status)
                )
            """)

            conn.commit()
        finally:
            conn.close()

    def get_metric_reference(self, test_name_or_code: str, gender: str = "all") -> Optional[LabMetric]:
        """
        Backward-compatible reference lookup.
        Returns a LabMetric cleanly for universal metrics or explicit gender lookups.
        For demographic-dependent metrics called with gender='all', flags evaluation_status='INCONCLUSIVE_MISSING_DEMOGRAPHICS'.
        """
        cleaned = test_name_or_code.strip().lower()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_id FROM metric_aliases WHERE LOWER(alias) = ?
                UNION
                SELECT metric_id FROM lab_metrics WHERE LOWER(metric_id) = ? OR LOWER(canonical_name) = ? OR loinc_code = ?
                LIMIT 1
            """, (cleaned, cleaned, cleaned, test_name_or_code.strip()))
            row = cursor.fetchone()
            if not row:
                return None

            resolved_id = row["metric_id"]

            # Fetch base metric
            cursor.execute("SELECT * FROM lab_metrics WHERE metric_id = ?", (resolved_id,))
            m_row = cursor.fetchone()
            if not m_row:
                return None

            # Fetch aliases
            cursor.execute("SELECT alias FROM metric_aliases WHERE metric_id = ?", (resolved_id,))
            aliases = [a["alias"] for a in cursor.fetchall()]

            # Fetch reference intervals
            cursor.execute("SELECT * FROM metric_reference_intervals WHERE metric_id = ?", (resolved_id,))
            intervals = cursor.fetchall()
            if not intervals:
                return None

            has_sex_stratification = any(i["gender"] in ("male", "female") for i in intervals)
            has_age_stratification = any(i["age_max_years"] < 100.0 or i["age_min_years"] > 18.0 for i in intervals)
            # Check methodology stratification (e.g. multiple distinct methodology tags among candidates)
            unique_method_tags = set(i["analytical_method_tag"] for i in intervals if i["analytical_method_tag"] != "ALL_METHODS")
            has_method_stratification = len(unique_method_tags) > 1

            # Check critical limits for consensus alerts
            cursor.execute("""
                SELECT critical_low, critical_high FROM metric_critical_limits
                WHERE metric_id = ? AND limit_type IN ('CLINICAL_PRACTICE_ALERT_THRESHOLD', 'CONSENSUS_PANIC_SURVEY_MEDIAN')
                LIMIT 1
            """, (resolved_id,))
            crit_row = cursor.fetchone()

            # Handle generic gender='all' call
            if gender.lower() == "all":
                if has_sex_stratification or has_age_stratification or has_method_stratification:
                    return LabMetric(
                        metric_id=m_row["metric_id"],
                        canonical_name=m_row["canonical_name"],
                        loinc_code=m_row["loinc_code"],
                        category=m_row["category"],
                        unit=m_row["standard_unit"],
                        gender="all",
                        min_normal=None,
                        max_normal=None,
                        critical_low=float(crit_row["critical_low"]) if crit_row and crit_row["critical_low"] is not None else None,
                        critical_high=float(crit_row["critical_high"]) if crit_row and crit_row["critical_high"] is not None else None,
                        description=m_row["description"],
                        aliases=aliases,
                        is_demographic_dependent=True,
                        evaluation_status="INSUFFICIENT_DEMOGRAPHIC_CONTEXT",
                        demographic_requirement_note="Biomarker interval is biological sex, age, or methodology stratified. Context required."
                    )
                # Universal metric with unique interval
                if len(intervals) != 1:
                    return LabMetric(
                        metric_id=m_row["metric_id"],
                        canonical_name=m_row["canonical_name"],
                        loinc_code=m_row["loinc_code"],
                        category=m_row["category"],
                        unit=m_row["standard_unit"],
                        gender="all",
                        min_normal=None,
                        max_normal=None,
                        critical_low=float(crit_row["critical_low"]) if crit_row and crit_row["critical_low"] is not None else None,
                        critical_high=float(crit_row["critical_high"]) if crit_row and crit_row["critical_high"] is not None else None,
                        description=m_row["description"],
                        aliases=aliases,
                        is_demographic_dependent=True,
                        evaluation_status="INCONCLUSIVE_NON_UNIQUE_INTERVAL",
                        demographic_requirement_note="Multiple candidate intervals exist without disambiguating context."
                    )
                target_inv = intervals[0]
            else:
                # Explicit gender provided
                # CLINICAL GOVERNANCE RULE:
                # Explicit gender lookups must still enforce age applicability, methodology applicability,
                # and interval uniqueness. If age or methodology is stratified, missing context cannot
                # default to an arbitrary range and must return INSUFFICIENT_DEMOGRAPHIC_CONTEXT.
                matching = [i for i in intervals if i["gender"] == gender.lower() or i["gender"] == "all"]
                if not matching:
                    return None

                # Enforce age stratification safety: if metric has age bounds, unstated age cannot resolve
                if has_age_stratification:
                    return LabMetric(
                        metric_id=m_row["metric_id"],
                        canonical_name=m_row["canonical_name"],
                        loinc_code=m_row["loinc_code"],
                        category=m_row["category"],
                        unit=m_row["standard_unit"],
                        gender=gender.lower(),
                        min_normal=None,
                        max_normal=None,
                        critical_low=float(crit_row["critical_low"]) if crit_row and crit_row["critical_low"] is not None else None,
                        critical_high=float(crit_row["critical_high"]) if crit_row and crit_row["critical_high"] is not None else None,
                        description=m_row["description"],
                        aliases=aliases,
                        is_demographic_dependent=True,
                        evaluation_status="INSUFFICIENT_DEMOGRAPHIC_CONTEXT",
                        demographic_requirement_note="Biomarker interval is age-stratified. Patient age context is required."
                    )

                # Enforce methodology stratification safety
                if has_method_stratification:
                    return LabMetric(
                        metric_id=m_row["metric_id"],
                        canonical_name=m_row["canonical_name"],
                        loinc_code=m_row["loinc_code"],
                        category=m_row["category"],
                        unit=m_row["standard_unit"],
                        gender=gender.lower(),
                        min_normal=None,
                        max_normal=None,
                        critical_low=float(crit_row["critical_low"]) if crit_row and crit_row["critical_low"] is not None else None,
                        critical_high=float(crit_row["critical_high"]) if crit_row and crit_row["critical_high"] is not None else None,
                        description=m_row["description"],
                        aliases=aliases,
                        is_demographic_dependent=True,
                        evaluation_status="INSUFFICIENT_DEMOGRAPHIC_CONTEXT",
                        demographic_requirement_note="Biomarker interval is methodology-stratified. Analytical methodology context is required."
                    )

                # Enforce interval uniqueness
                # Prefer exact sex match if available
                exact_sex_matches = [i for i in matching if i["gender"] == gender.lower()]
                candidates = exact_sex_matches if exact_sex_matches else matching

                if len(candidates) > 1:
                    return LabMetric(
                        metric_id=m_row["metric_id"],
                        canonical_name=m_row["canonical_name"],
                        loinc_code=m_row["loinc_code"],
                        category=m_row["category"],
                        unit=m_row["standard_unit"],
                        gender=gender.lower(),
                        min_normal=None,
                        max_normal=None,
                        critical_low=float(crit_row["critical_low"]) if crit_row and crit_row["critical_low"] is not None else None,
                        critical_high=float(crit_row["critical_high"]) if crit_row and crit_row["critical_high"] is not None else None,
                        description=m_row["description"],
                        aliases=aliases,
                        is_demographic_dependent=True,
                        evaluation_status="INCONCLUSIVE_NON_UNIQUE_INTERVAL",
                        demographic_requirement_note="Multiple candidate intervals match biological sex without disambiguating clinical context."
                    )

                target_inv = candidates[0]

            return LabMetric(
                metric_id=m_row["metric_id"],
                canonical_name=m_row["canonical_name"],
                loinc_code=m_row["loinc_code"],
                category=m_row["category"],
                unit=m_row["standard_unit"],
                gender=target_inv["gender"],
                min_normal=float(target_inv["min_normal"]),
                max_normal=float(target_inv["max_normal"]),
                critical_low=float(crit_row["critical_low"]) if crit_row and crit_row["critical_low"] is not None else None,
                critical_high=float(crit_row["critical_high"]) if crit_row and crit_row["critical_high"] is not None else None,
                description=m_row["description"],
                aliases=aliases,
                is_demographic_dependent=has_sex_stratification or has_age_stratification,
                evaluation_status="CONCLUSIVE"
            )
        finally:
            conn.close()

    def get_contextual_metric_reference(
        self, test_name_or_code: str, patient: PatientContext
    ) -> IntervalSelectionResult:
        """Fetch deterministic, demographic-specific biological reference interval and critical limits."""
        cleaned = test_name_or_code.strip().lower()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_id FROM metric_aliases WHERE LOWER(alias) = ?
                UNION
                SELECT metric_id FROM lab_metrics WHERE LOWER(metric_id) = ? OR LOWER(canonical_name) = ? OR loinc_code = ?
                LIMIT 1
            """, (cleaned, cleaned, cleaned, test_name_or_code.strip()))
            row = cursor.fetchone()
            if not row:
                return IntervalSelectionResult(
                    is_conclusive=False,
                    inconclusive_code="UNKNOWN_BIOMARKER",
                    inconclusive_reason=f"Biomarker '{test_name_or_code}' is not indexed in clinical reference repository."
                )

            metric_id = row["metric_id"]

            # Load Reference Intervals
            cursor.execute("SELECT * FROM metric_reference_intervals WHERE metric_id = ?", (metric_id,))
            inv_rows = cursor.fetchall()
            intervals = [
                ReferenceInterval(
                    interval_id=r["interval_id"],
                    metric_id=r["metric_id"],
                    population=r["population"],
                    gender=r["gender"],
                    age_min_years=r["age_min_years"],
                    age_max_years=r["age_max_years"],
                    pregnancy_status=r["pregnancy_status"],
                    unit=r["unit"],
                    min_normal=r["min_normal"],
                    max_normal=r["max_normal"],
                    interval_context_note=r["interval_context_note"],
                    source_reference=r["source_reference"],
                    verification_status=r["verification_status"],
                    interval_tier=r["interval_tier"],
                    analytical_method_tag=r["analytical_method_tag"]
                )
                for r in inv_rows
            ]

            # Load Critical Limits
            cursor.execute("SELECT * FROM metric_critical_limits WHERE metric_id = ?", (metric_id,))
            cl_rows = cursor.fetchall()
            critical_limits = [
                CriticalLimit(
                    critical_limit_id=r["critical_limit_id"],
                    metric_id=r["metric_id"],
                    critical_low=r["critical_low"],
                    critical_high=r["critical_high"],
                    unit=r["unit"],
                    limit_type=CriticalLimitType(r["limit_type"]),
                    institutional_note=r["institutional_note"],
                    clinical_urgency=r["clinical_urgency"],
                    source_reference=r["source_reference"],
                    verification_status=r["verification_status"],
                    institutional_identifier=r["institutional_identifier"]
                )
                for r in cl_rows
            ]

            # Load Clinical Context
            cursor.execute("SELECT * FROM metric_clinical_context WHERE metric_id = ?", (metric_id,))
            c_row = cursor.fetchone()
            clinical_ctx = None
            if c_row:
                clinical_ctx = ClinicalContext(
                    metric_id=c_row["metric_id"],
                    fasting_required=bool(c_row["fasting_required"]),
                    fasting_recommended_hours=c_row["fasting_recommended_hours"],
                    fasting_details=c_row["fasting_details"],
                    measurement_type=c_row["measurement_type"],
                    methodology=c_row["methodology"],
                    equation_description=c_row["equation_description"],
                    longitudinal_requirements=c_row["longitudinal_requirements"],
                    clinical_limitations=c_row["clinical_limitations"],
                    gestational_applicability_type=GestationalApplicabilityType(c_row["gestational_applicability_type"]),
                    gestational_contraindication_note=c_row["gestational_contraindication_note"],
                    primary_source_organization=c_row["primary_source_organization"],
                    primary_document_title=c_row["primary_document_title"],
                    publication_year=c_row["publication_year"],
                    source_url=c_row["source_url"],
                    provenance_verification_status=c_row["provenance_verification_status"],
                    provenance_clinical_notes=c_row["provenance_clinical_notes"]
                )

            # Delegate to Deterministic Selector
            from clinical_engine.pipeline.selector import DeterministicClinicalSelector
            return DeterministicClinicalSelector.select_interval_and_limits(
                intervals=intervals,
                critical_limits=critical_limits,
                clinical_ctx=clinical_ctx,
                patient=patient
            )
        finally:
            conn.close()

    def get_unit_conversion(self, metric_id: str, incoming_unit: str) -> Optional[UnitConversion]:
        """Fetch registered unit conversion for metric and incoming unit."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM metric_unit_conversions
                WHERE metric_id = ? AND LOWER(alternative_unit) = LOWER(?)
            """, (metric_id, incoming_unit.strip()))
            row = cursor.fetchone()
            if not row:
                return None
            return UnitConversion(
                conversion_id=row["conversion_id"],
                metric_id=row["metric_id"],
                alternative_unit=row["alternative_unit"],
                standard_unit=row["standard_unit"],
                conversion_type=row["conversion_type"],
                conversion_factor=row["conversion_factor"],
                canonical_conversion_formula=row["canonical_conversion_formula"],
                formula_description=row["formula_description"],
                handler_function_name=row["handler_function_name"]
            )
        finally:
            conn.close()

    def get_diagnostic_thresholds(self, metric_id: str) -> List[DiagnosticThreshold]:
        """Fetch all guideline clinical diagnostic thresholds for metric."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metric_diagnostic_thresholds WHERE metric_id = ?", (metric_id,))
            return [
                DiagnosticThreshold(
                    diagnostic_id=r["diagnostic_id"],
                    metric_id=r["metric_id"],
                    condition_name=r["condition_name"],
                    cutoff_value=r["cutoff_value"],
                    comparison_operator=r["comparison_operator"],
                    unit=r["unit"],
                    requires_repeat_confirmation=bool(r["requires_repeat_confirmation"]),
                    clinical_criteria=r["clinical_criteria"],
                    source_guideline=r["source_guideline"],
                    verification_status=r["verification_status"]
                )
                for r in cursor.fetchall()
            ]
        finally:
            conn.close()

    def get_clinical_context(self, metric_id: str) -> Optional[ClinicalContext]:
        """Fetch fasting, methodology, and provenance context for metric."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metric_clinical_context WHERE metric_id = ?", (metric_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return ClinicalContext(
                metric_id=r["metric_id"],
                fasting_required=bool(r["fasting_required"]),
                fasting_recommended_hours=r["fasting_recommended_hours"],
                fasting_details=r["fasting_details"],
                measurement_type=r["measurement_type"],
                methodology=r["methodology"],
                equation_description=r["equation_description"],
                longitudinal_requirements=r["longitudinal_requirements"],
                clinical_limitations=r["clinical_limitations"],
                gestational_applicability_type=GestationalApplicabilityType(r["gestational_applicability_type"]),
                gestational_contraindication_note=r["gestational_contraindication_note"],
                primary_source_organization=r["primary_source_organization"],
                primary_document_title=r["primary_document_title"],
                publication_year=r["publication_year"],
                source_url=r["source_url"],
                provenance_verification_status=r["provenance_verification_status"],
                provenance_clinical_notes=r["provenance_clinical_notes"]
            )
        finally:
            conn.close()

    def list_all_metrics(self) -> List[LabMetric]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lab_metrics ORDER BY category, canonical_name")
            rows = cursor.fetchall()
            metrics = []
            for r in rows:
                cursor.execute("SELECT alias FROM metric_aliases WHERE metric_id = ?", (r["metric_id"],))
                aliases = [a["alias"] for a in cursor.fetchall()]

                cursor.execute("SELECT min_normal, max_normal, gender FROM metric_reference_intervals WHERE metric_id = ? LIMIT 1", (r["metric_id"],))
                inv = cursor.fetchone()

                cursor.execute("SELECT critical_low, critical_high FROM metric_critical_limits WHERE metric_id = ? LIMIT 1", (r["metric_id"],))
                crit = cursor.fetchone()

                metrics.append(LabMetric(
                    metric_id=r["metric_id"],
                    canonical_name=r["canonical_name"],
                    category=r["category"],
                    unit=r["standard_unit"],
                    gender=inv["gender"] if inv else "all",
                    min_normal=float(inv["min_normal"]) if inv else None,
                    max_normal=float(inv["max_normal"]) if inv else None,
                    loinc_code=r["loinc_code"],
                    critical_low=float(crit["critical_low"]) if crit and crit["critical_low"] is not None else None,
                    critical_high=float(crit["critical_high"]) if crit and crit["critical_high"] is not None else None,
                    description=r["description"],
                    aliases=aliases
                ))
            return metrics
        finally:
            conn.close()

    def get_protocols_by_condition(self, condition_id: str) -> List[ClinicalProtocol]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clinical_protocols WHERE condition_id = ?", (condition_id.strip(),))
            rows = cursor.fetchall()
            protocols = []
            for r in rows:
                protocols.append(ClinicalProtocol(
                    protocol_id=r["protocol_id"],
                    condition_id=r["condition_id"],
                    condition_name=r["condition_name"],
                    category=r["category"],
                    summary_narrative=r["summary_narrative"],
                    dietary_guidelines=json.loads(r["dietary_guidelines_json"] or "[]"),
                    activity_guidelines=json.loads(r["activity_guidelines_json"] or "[]"),
                    contraindications_to_avoid=json.loads(r["contraindications_json"] or "[]"),
                    physician_discussion_questions=json.loads(r["physician_questions_json"] or "[]"),
                    escalation_flag=bool(r["escalation_flag"])
                ))
            return protocols
        finally:
            conn.close()

    def get_protocols_for_abnormal_metric(self, metric_id: str, trigger_status: str) -> List[ClinicalProtocol]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cp.* FROM clinical_protocols cp
                JOIN condition_metric_mappings cm ON cp.condition_id = cm.condition_id
                WHERE cm.metric_id = ? AND cm.trigger_status = ?
            """, (metric_id, trigger_status.upper()))
            rows = cursor.fetchall()
            protocols = []
            for r in rows:
                protocols.append(ClinicalProtocol(
                    protocol_id=r["protocol_id"],
                    condition_id=r["condition_id"],
                    condition_name=r["condition_name"],
                    category=r["category"],
                    summary_narrative=r["summary_narrative"],
                    dietary_guidelines=json.loads(r["dietary_guidelines_json"] or "[]"),
                    activity_guidelines=json.loads(r["activity_guidelines_json"] or "[]"),
                    contraindications_to_avoid=json.loads(r["contraindications_json"] or "[]"),
                    physician_discussion_questions=json.loads(r["physician_questions_json"] or "[]"),
                    escalation_flag=bool(r["escalation_flag"])
                ))
            return protocols
        finally:
            conn.close()

    def list_all_protocols(self) -> List[ClinicalProtocol]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clinical_protocols ORDER BY condition_name")
            return [
                ClinicalProtocol(
                    protocol_id=r["protocol_id"],
                    condition_id=r["condition_id"],
                    condition_name=r["condition_name"],
                    category=r["category"],
                    summary_narrative=r["summary_narrative"],
                    dietary_guidelines=json.loads(r["dietary_guidelines_json"] or "[]"),
                    activity_guidelines=json.loads(r["activity_guidelines_json"] or "[]"),
                    contraindications_to_avoid=json.loads(r["contraindications_json"] or "[]"),
                    physician_discussion_questions=json.loads(r["physician_questions_json"] or "[]"),
                    escalation_flag=bool(r["escalation_flag"])
                )
                for r in cursor.fetchall()
            ]
        finally:
            conn.close()

    def ingest_canonical_reference_panels(self, panel_paths: List[Path]) -> Dict[str, int]:
        """Ingests all Phase 2 canonical reference JSON panels transactionally."""
        conn = self._get_connection()
        counts = {
            "metrics": 0,
            "aliases": 0,
            "reference_intervals": 0,
            "critical_limits": 0,
            "diagnostic_thresholds": 0,
            "treatment_targets": 0,
            "risk_thresholds": 0,
            "unit_conversions": 0,
            "clinical_contexts": 0
        }
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            for pp in panel_paths:
                parsed = CanonicalReferenceAdapter.parse_panel_file(pp)

                # 1. Base lab_metrics
                for m in parsed["metrics"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO lab_metrics
                        (metric_id, canonical_name, category, standard_unit, description, loinc_code,
                         loinc_verification_status, loinc_version, loinc_component, loinc_property,
                         loinc_system_specimen, loinc_scale_type, loinc_method_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        m["metric_id"], m["canonical_name"], m["category"], m["standard_unit"], m["description"],
                        m["loinc_code"], m["loinc_verification_status"], m["loinc_version"], m["loinc_component"],
                        m["loinc_property"], m["loinc_system_specimen"], m["loinc_scale_type"], m["loinc_method_type"]
                    ))
                    counts["metrics"] += 1

                # 2. Aliases
                for a in parsed["aliases"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO metric_aliases (alias, metric_id)
                        VALUES (?, ?)
                    """, (a["alias"], a["metric_id"]))
                    counts["aliases"] += 1

                # 3. Reference Intervals
                for inv in parsed["reference_intervals"]:
                    cursor.execute("""
                        INSERT INTO metric_reference_intervals
                        (metric_id, population, gender, age_min_years, age_max_years, pregnancy_status,
                         unit, min_normal, max_normal, interval_context_note, source_reference,
                         verification_status, interval_tier, analytical_method_tag)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        inv["metric_id"], inv["population"], inv["gender"], inv["age_min_years"], inv["age_max_years"],
                        inv["pregnancy_status"], inv["unit"], inv["min_normal"], inv["max_normal"],
                        inv["interval_context_note"], inv["source_reference"], inv["verification_status"],
                        inv["interval_tier"], inv["analytical_method_tag"]
                    ))
                    counts["reference_intervals"] += 1

                # 4. Critical Limits
                for cl in parsed["critical_limits"]:
                    cursor.execute("""
                        INSERT INTO metric_critical_limits
                        (metric_id, critical_low, critical_high, unit, limit_type, institutional_note,
                         clinical_urgency, source_reference, verification_status, institutional_identifier)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cl["metric_id"], cl["critical_low"], cl["critical_high"], cl["unit"], cl["limit_type"],
                        cl["institutional_note"], cl["clinical_urgency"], cl["source_reference"],
                        cl["verification_status"], cl["institutional_identifier"]
                    ))
                    counts["critical_limits"] += 1

                # 5. Diagnostic Thresholds
                for dt in parsed["diagnostic_thresholds"]:
                    cursor.execute("""
                        INSERT INTO metric_diagnostic_thresholds
                        (metric_id, condition_name, cutoff_value, comparison_operator, unit,
                         requires_repeat_confirmation, clinical_criteria, source_guideline, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dt["metric_id"], dt["condition_name"], dt["cutoff_value"], dt["comparison_operator"],
                        dt["unit"], dt["requires_repeat_confirmation"], dt["clinical_criteria"],
                        dt["source_guideline"], dt["verification_status"]
                    ))
                    counts["diagnostic_thresholds"] += 1

                # 6. Treatment Targets
                for tt in parsed["treatment_targets"]:
                    cursor.execute("""
                        INSERT INTO metric_treatment_targets
                        (metric_id, target_population, goal_description, target_value, comparison_operator,
                         unit, source_guideline, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        tt["metric_id"], tt["target_population"], tt["goal_description"], tt["target_value"],
                        tt["comparison_operator"], tt["unit"], tt["source_guideline"], tt["verification_status"]
                    ))
                    counts["treatment_targets"] += 1

                # 7. Risk Tiers
                for rt in parsed["risk_thresholds"]:
                    cursor.execute("""
                        INSERT INTO metric_risk_thresholds
                        (metric_id, tier_name, tier_description, lower_bound, upper_bound, unit,
                         clinical_significance, source_classification, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rt["metric_id"], rt["tier_name"], rt["tier_description"], rt["lower_bound"],
                        rt["upper_bound"], rt["unit"], rt["clinical_significance"],
                        rt["source_classification"], rt["verification_status"]
                    ))
                    counts["risk_thresholds"] += 1

                # 8. Unit Conversions
                for uc in parsed["unit_conversions"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO metric_unit_conversions
                        (metric_id, alternative_unit, standard_unit, conversion_type, conversion_factor,
                         canonical_conversion_formula, formula_description, handler_function_name)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        uc["metric_id"], uc["alternative_unit"], uc["standard_unit"], uc["conversion_type"],
                        uc["conversion_factor"], uc["canonical_conversion_formula"], uc["formula_description"],
                        uc["handler_function_name"]
                    ))
                    counts["unit_conversions"] += 1

                # 9. Clinical Context
                for cc in parsed["clinical_contexts"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO metric_clinical_context
                        (metric_id, fasting_required, fasting_recommended_hours, fasting_details,
                         measurement_type, methodology, equation_description, longitudinal_requirements,
                         clinical_limitations, gestational_applicability_type, gestational_contraindication_note,
                         primary_source_organization, primary_document_title, publication_year,
                         source_url, provenance_verification_status, provenance_clinical_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cc["metric_id"], cc["fasting_required"], cc["fasting_recommended_hours"], cc["fasting_details"],
                        cc["measurement_type"], cc["methodology"], cc["equation_description"],
                        cc["longitudinal_requirements"], cc["clinical_limitations"],
                        cc["gestational_applicability_type"], cc["gestational_contraindication_note"],
                        cc["primary_source_organization"], cc["primary_document_title"], cc["publication_year"],
                        cc["source_url"], cc["provenance_verification_status"], cc["provenance_clinical_notes"]
                    ))
                    counts["clinical_contexts"] += 1

            conn.commit()
            return counts
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def bulk_load_dataset(self, data_or_path: Any) -> int:
        """Loads legacy protocols & mappings payload, or canonical panel if passed."""
        payload = data_or_path
        if isinstance(data_or_path, (str, Path)):
            with open(data_or_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

        if not isinstance(payload, dict):
            raise ValueError("Dataset payload must be a dictionary.")

        # Check if canonical panel JSON
        if "panel_category" in payload and "biomarkers" in payload:
            res = self.ingest_canonical_reference_panels([Path(data_or_path)])
            return sum(res.values())

        records_inserted = 0
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            for item in payload.get("metrics", []):
                metric = LabMetric(**item)
                cursor.execute("""
                    INSERT OR REPLACE INTO lab_metrics 
                    (metric_id, canonical_name, category, standard_unit, description, loinc_code,
                     loinc_verification_status, loinc_version, loinc_component, loinc_property,
                     loinc_system_specimen, loinc_scale_type, loinc_method_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_id, metric.canonical_name, metric.category, metric.unit,
                    metric.description or "", metric.loinc_code or "UNASSIGNED",
                    "LEGACY_INGESTION", "2.83", metric.canonical_name, "MCnc", "Bld", "Qn", "Legacy"
                ))

                for alias in metric.aliases:
                    cursor.execute("INSERT OR REPLACE INTO metric_aliases (alias, metric_id) VALUES (?, ?)",
                                   (alias.strip().lower(), metric.metric_id))

                if metric.min_normal is not None and metric.max_normal is not None:
                    cursor.execute("""
                        INSERT INTO metric_reference_intervals
                        (metric_id, population, gender, age_min_years, age_max_years, pregnancy_status,
                         unit, min_normal, max_normal, interval_context_note, source_reference, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metric.metric_id, "Legacy Cohort", metric.gender.lower(), 18.0, 120.0,
                        "ALL", metric.unit, metric.min_normal, metric.max_normal,
                        "Ingested from legacy clinical dataset", "Legacy Reference Dataset", "VERIFIED"
                    ))

                if metric.critical_low is not None or metric.critical_high is not None:
                    cursor.execute("""
                        INSERT INTO metric_critical_limits
                        (metric_id, critical_low, critical_high, unit, limit_type, institutional_note,
                         clinical_urgency, source_reference, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        metric.metric_id, metric.critical_low, metric.critical_high, metric.unit,
                        "CLINICAL_PRACTICE_ALERT_THRESHOLD", "Legacy critical values baseline",
                        "Urgent clinical evaluation advised", "Legacy Clinical Baseline", "VERIFIED"
                    ))

                records_inserted += 1

            for p in payload.get("protocols", []):
                protocol = ClinicalProtocol(**p)
                cursor.execute("""
                    INSERT OR REPLACE INTO clinical_protocols
                    (protocol_id, condition_id, condition_name, category, summary_narrative,
                     dietary_guidelines_json, activity_guidelines_json, contraindications_json,
                     physician_questions_json, escalation_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    protocol.protocol_id, protocol.condition_id, protocol.condition_name, protocol.category,
                    protocol.summary_narrative, json.dumps(protocol.dietary_guidelines),
                    json.dumps(protocol.activity_guidelines), json.dumps(protocol.contraindications_to_avoid),
                    json.dumps(protocol.physician_discussion_questions), 1 if protocol.escalation_flag else 0
                ))
                records_inserted += 1

            for m in payload.get("mappings", []):
                cursor.execute("""
                    INSERT OR REPLACE INTO condition_metric_mappings (condition_id, metric_id, trigger_status)
                    VALUES (?, ?, ?)
                """, (m["condition_id"], m["metric_id"], m["trigger_status"].upper()))
                records_inserted += 1

            conn.commit()
            return records_inserted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
