"""
Phase 2 Canonical Clinical Test Suite for MediPulse AI.

Comprehensive verification of:
1. Canonical dataset loading and reconciliation (20 biomarkers, 20 LOINC 2.83 codes, 9 tables).
2. Deterministic interval selection (universal vs biological sex vs age-stratified).
3. Pregnancy safety (prohibiting non-pregnant fallback for pregnant patients, halting on unstated pregnancy status for pregnancy-sensitive metrics, trimester verification).
4. Safe allowlisted unit conversions (linear scale, non-linear HbA1c IFCC-to-NGSP, unsupported unit rejection, zero eval/exec).
5. Critical limit governance (laboratory panic alerts, clinical practice alerts, survey medians).
6. Fail-safe backward compatibility in get_metric_reference() (clean lookup for universal metrics, evaluation_status='INSUFFICIENT_DEMOGRAPHIC_CONTEXT' for sex-dependent metrics with 'all', zero crashes).
7. End-to-end DiagnosticEngine integration (normal, abnormal, critical, inconclusive, unknown biomarker, unsupported unit).
"""

import os
import gc
import unittest
from pathlib import Path

from clinical_engine.storage.repository import SQLClinicalRepository
from clinical_engine.storage.adapter import CanonicalReferenceAdapter
from clinical_engine.pipeline.selector import DeterministicClinicalSelector
from clinical_engine.pipeline.converters import convert_laboratory_value, UnitConversionRegistry
from clinical_engine.pipeline.engine import DiagnosticEngine
from clinical_engine.domain.schemas import (
    PatientContext,
    MetricStatus,
    SeverityLevel,
    GestationalApplicabilityType,
    CriticalLimitType,
)


class TestCanonicalPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = "data/test_phase2_canonical.db"
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except OSError:
                pass

        cls.repo = SQLClinicalRepository(db_path=cls.test_db_path)
        base_ref = Path(__file__).parent.parent / "datasets" / "reference_data"
        cls.panel_paths = [
            base_ref / "cbc_reference.json",
            base_ref / "lipid_reference.json",
            base_ref / "diabetes_reference.json",
            base_ref / "kft_reference.json"
        ]
        cls.counts = cls.repo.ingest_canonical_reference_panels(cls.panel_paths)
        cls.engine = DiagnosticEngine(repository=cls.repo)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except OSError:
                pass

    # =========================================================================
    # 1. DATASET RECONCILIATION & STORAGE
    # =========================================================================

    def test_reconciliation_entity_counts(self):
        """Verify all 20 canonical biomarkers and normalized entities are loaded."""
        self.assertEqual(self.counts["metrics"], 20)
        self.assertEqual(self.counts["reference_intervals"], 26)
        self.assertEqual(self.counts["critical_limits"], 12)
        self.assertEqual(self.counts["diagnostic_thresholds"], 22)
        self.assertEqual(self.counts["treatment_targets"], 9)
        self.assertEqual(self.counts["risk_thresholds"], 28)
        self.assertEqual(self.counts["unit_conversions"], 21)
        self.assertEqual(self.counts["clinical_contexts"], 20)
        self.assertGreaterEqual(self.counts["aliases"], 80)

    def test_loinc_283_specifications(self):
        """Verify all 20 biomarkers carry LOINC version 2.83 and complete LOINC properties."""
        metrics = self.repo.list_all_metrics()
        self.assertEqual(len(metrics), 20)
        
        conn = self.repo._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT metric_id, loinc_code, loinc_version, loinc_component, loinc_property, loinc_system_specimen, loinc_scale_type FROM lab_metrics")
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 20)
            for r in rows:
                self.assertIsNotNone(r["loinc_code"])
                self.assertNotEqual(r["loinc_code"], "UNASSIGNED")
                self.assertIn("2.83", r["loinc_version"])
                self.assertTrue(len(r["loinc_component"]) > 0)
                self.assertTrue(len(r["loinc_property"]) > 0)
                self.assertTrue(len(r["loinc_system_specimen"]) > 0)
                self.assertTrue(any(scale in r["loinc_scale_type"] for scale in ["Qn", "Ord", "Nom"]))
        finally:
            conn.close()

    def test_alias_resolution(self):
        """Verify robust case-insensitive alias resolution for canonical biomarkers."""
        # Test exact canonical name
        ctx = PatientContext(biological_sex="male", age_years=35.0, is_pregnant=False)
        res1 = self.repo.get_contextual_metric_reference("Hemoglobin", ctx)
        self.assertTrue(res1.is_conclusive)
        self.assertEqual(res1.interval.metric_id, "hemoglobin")

        # Test colloquial alias
        res2 = self.repo.get_contextual_metric_reference("Hb", ctx)
        self.assertTrue(res2.is_conclusive)
        self.assertEqual(res2.interval.metric_id, "hemoglobin")

        # Test LOINC code lookup
        res3 = self.repo.get_contextual_metric_reference("718-7", ctx)
        self.assertTrue(res3.is_conclusive)
        self.assertEqual(res3.interval.metric_id, "hemoglobin")

        # Test lipid alias
        res4 = self.repo.get_contextual_metric_reference("Bad Cholesterol", ctx)
        self.assertTrue(res4.is_conclusive)
        self.assertEqual(res4.interval.metric_id, "ldl")

    # =========================================================================
    # 2. DETERMINISTIC INTERVAL SELECTION
    # =========================================================================

    def test_universal_interval_selection(self):
        """Verify metrics with universal intervals (gender='all') evaluate cleanly."""
        # Total Cholesterol is universal (125.0 - 199.0 mg/dL)
        ctx = PatientContext(biological_sex="female", age_years=40.0, is_pregnant=False)
        res = self.repo.get_contextual_metric_reference("Total Cholesterol", ctx)
        self.assertTrue(res.is_conclusive)
        self.assertEqual(res.interval.metric_id, "cholesterol_total")
        self.assertEqual(res.interval.gender, "all")
        self.assertEqual(res.interval.min_normal, 125.0)
        self.assertEqual(res.interval.max_normal, 199.0)

    def test_biological_sex_stratified_selection(self):
        """Verify male and female reference intervals select accurately and distinctively."""
        ctx_m = PatientContext(biological_sex="male", age_years=30.0, is_pregnant=False)
        res_m = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_m)
        self.assertTrue(res_m.is_conclusive)
        self.assertEqual(res_m.interval.gender, "male")
        self.assertEqual(res_m.interval.min_normal, 13.5)
        self.assertEqual(res_m.interval.max_normal, 17.5)

        ctx_f = PatientContext(biological_sex="female", age_years=30.0, is_pregnant=False)
        res_f = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_f)
        self.assertTrue(res_f.is_conclusive)
        self.assertEqual(res_f.interval.gender, "female")
        self.assertEqual(res_f.interval.min_normal, 12.0)
        self.assertEqual(res_f.interval.max_normal, 15.5)

    def test_missing_biological_sex_halts_on_stratified_metric(self):
        """Halt with MISSING_BIOLOGICAL_SEX if patient sex is unstated on sex-dependent metric."""
        ctx = PatientContext(biological_sex=None, age_years=30.0, is_pregnant=False)
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx)
        self.assertFalse(res.is_conclusive)
        self.assertEqual(res.inconclusive_code, "MISSING_BIOLOGICAL_SEX")
        self.assertIn("stratified", res.inconclusive_reason.lower())

    def test_age_out_of_bounds_halts(self):
        """Halt when patient age falls outside adult reference parameters."""
        ctx_pediatric = PatientContext(biological_sex="male", age_years=12.0, is_pregnant=False)
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_pediatric)
        self.assertFalse(res.is_conclusive)
        self.assertEqual(res.inconclusive_code, "AGE_OUT_OF_BOUNDS")

    # =========================================================================
    # 3. PREGNANCY SAFETY GOVERNANCE
    # =========================================================================

    def test_pregnant_patient_with_no_pregnancy_interval_returns_inconclusive(self):
        """
        CORRECTION 1: Never automatically substitute a non-pregnant reference interval
        for a pregnant patient. Returns INCONCLUSIVE (PREGNANCY_RANGE_UNAVAILABLE).
        """
        ctx_preg = PatientContext(
            biological_sex="female",
            age_years=28.0,
            is_pregnant=True
        )
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_preg)
        self.assertFalse(res.is_conclusive)
        self.assertEqual(res.inconclusive_code, "PREGNANCY_RANGE_UNAVAILABLE")
        self.assertIn("non-pregnant reference intervals cannot be safely applied", res.inconclusive_reason)

    def test_unstated_pregnancy_status_on_pregnancy_sensitive_biomarker_halts(self):
        """
        Female of reproductive age with unstated pregnancy status on pregnancy-sensitive biomarker
        halts with UNRESOLVED_PREGNANCY_STATUS.
        """
        ctx_unknown_preg = PatientContext(
            biological_sex="female",
            age_years=25.0,
            is_pregnant=None
        )
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_unknown_preg)
        self.assertFalse(res.is_conclusive)
        self.assertEqual(res.inconclusive_code, "UNRESOLVED_PREGNANCY_STATUS")
        self.assertIn("non-pregnant intervals cannot be safely presumed", res.inconclusive_reason)

    def test_post_menopausal_female_exempt_from_pregnancy_halt(self):
        """Female age > 55 is physiologically exempt from reproductive pregnancy halts."""
        ctx_post_meno = PatientContext(
            biological_sex="female",
            age_years=62.0,
            is_pregnant=None
        )
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_post_meno)
        self.assertTrue(res.is_conclusive)
        self.assertEqual(res.interval.gender, "female")

    def test_pregnant_patient_on_contraindicated_metric_halts(self):
        """If a metric is clinically contraindicated in pregnancy (e.g. eGFR), evaluation halts."""
        ctx_preg = PatientContext(
            biological_sex="female",
            age_years=28.0,
            is_pregnant=True
        )
        res = self.repo.get_contextual_metric_reference("egfr", ctx_preg)
        self.assertFalse(res.is_conclusive)
        self.assertEqual(res.inconclusive_code, "GESTATIONAL_METHODOLOGY_CONTRAINDICATED")

    # =========================================================================
    # 4. SAFE ALLOWLISTED UNIT CONVERSION
    # =========================================================================

    def test_linear_unit_conversion(self):
        """Verify linear scaling unit conversions (e.g. Glucose mmol/L to mg/dL)."""
        conv = self.repo.get_unit_conversion("glucose_fasting", "mmol/L")
        self.assertIsNotNone(conv)
        self.assertEqual(conv.handler_function_name, "LINEAR_SCALE")
        
        result = convert_laboratory_value(
            detected_value=5.0,
            incoming_unit="mmol/L",
            standard_unit="mg/dL",
            conversion_type="LINEAR_SCALE",
            handler_name="LINEAR_SCALE",
            factor=conv.conversion_factor,
            formula_str=conv.canonical_conversion_formula
        )
        self.assertEqual(result["converted_value"], 90.091)
        self.assertEqual(result["audit"]["handler_executed"], "LINEAR_SCALE")

    def test_nonlinear_hba1c_ifcc_to_ngsp_conversion(self):
        """Verify non-linear HbA1c conversion (mmol/mol to %). Formula: (0.09148 * mmol/mol) + 2.152."""
        conv = self.repo.get_unit_conversion("hba1c", "mmol/mol")
        self.assertIsNotNone(conv)
        self.assertEqual(conv.handler_function_name, "HBA1C_IFCC_TO_NGSP")

        result = convert_laboratory_value(
            detected_value=48.0,
            incoming_unit="mmol/mol",
            standard_unit="%",
            conversion_type="FORMULA_CONVERSION",
            handler_name="HBA1C_IFCC_TO_NGSP",
            factor=None,
            formula_str=conv.canonical_conversion_formula
        )
        # (0.09148 * 48.0) + 2.152 = 4.39104 + 2.152 = 6.54304 -> rounded to 6.54
        self.assertEqual(result["converted_value"], 6.54)
        self.assertEqual(result["audit"]["handler_executed"], "HBA1C_IFCC_TO_NGSP")

    def test_unsupported_unit_rejected(self):
        """Reject unconfigured or non-allowlisted units safely."""
        with self.assertRaises(ValueError):
            convert_laboratory_value(
                detected_value=100.0,
                incoming_unit="arbitrary_unit",
                standard_unit="mg/dL",
                conversion_type="LINEAR_SCALE",
                handler_name="unregistered_handler",
                factor=1.0,
                formula_str="value * 1"
            )

    # =========================================================================
    # 5. CRITICAL LIMIT GOVERNANCE
    # =========================================================================

    def test_institutional_panic_alert_selection(self):
        """Verify laboratory-specific panic alert matches when institutional context matches."""
        ctx_mgh = PatientContext(
            biological_sex="male",
            age_years=45.0,
            is_pregnant=False,
            institutional_context="MGH"
        )
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_mgh)
        self.assertTrue(res.is_conclusive)
        self.assertIsNotNone(res.critical_limit)
        self.assertEqual(res.critical_limit.limit_type, CriticalLimitType.LABORATORY_SPECIFIC_PANIC_ALERT)
        self.assertEqual(res.critical_limit.critical_low, 7.0)

    def test_general_consensus_survey_median_fallback(self):
        """Verify consensus survey median or baseline critical limit attaches for notification."""
        ctx_gen = PatientContext(
            biological_sex="male",
            age_years=45.0,
            is_pregnant=False
        )
        res = self.repo.get_contextual_metric_reference("Hemoglobin", ctx_gen)
        self.assertTrue(res.is_conclusive)
        self.assertIsNotNone(res.critical_limit)
        self.assertEqual(res.critical_limit.critical_low, 7.0)

    # =========================================================================
    # 6. FAIL-SAFE BACKWARD COMPATIBILITY
    # =========================================================================

    def test_legacy_universal_lookup(self):
        """Verify legacy get_metric_reference() cleanly returns universal metrics."""
        metric = self.repo.get_metric_reference("Total Cholesterol", gender="all")
        self.assertIsNotNone(metric)
        self.assertEqual(metric.evaluation_status, "CONCLUSIVE")
        self.assertFalse(metric.is_demographic_dependent)
        self.assertEqual(metric.min_normal, 125.0)
        self.assertEqual(metric.max_normal, 199.0)

    def test_legacy_stratified_lookup_with_gender_all_returns_inconclusive(self):
        """
        CORRECTION 3: Calling get_metric_reference() with gender='all' on demographic-stratified
        metric flags evaluation_status='INSUFFICIENT_DEMOGRAPHIC_CONTEXT' and DOES NOT return arbitrary interval.
        """
        metric = self.repo.get_metric_reference("Hemoglobin", gender="all")
        self.assertIsNotNone(metric)
        self.assertTrue(metric.is_demographic_dependent)
        self.assertEqual(metric.evaluation_status, "INSUFFICIENT_DEMOGRAPHIC_CONTEXT")
        self.assertIsNone(metric.min_normal)
        self.assertIsNone(metric.max_normal)

    def test_legacy_stratified_lookup_with_explicit_gender(self):
        """Explicit gender passed to legacy get_metric_reference() succeeds conclusively."""
        metric = self.repo.get_metric_reference("Hemoglobin", gender="female")
        self.assertIsNotNone(metric)
        self.assertEqual(metric.evaluation_status, "CONCLUSIVE")
        self.assertEqual(metric.min_normal, 12.0)
        self.assertEqual(metric.max_normal, 15.5)

    # =========================================================================
    # 7. DIAGNOSTIC ENGINE INTEGRATION & CLINICAL PIPELINE
    # =========================================================================

    def test_engine_normal_finding(self):
        """Engine evaluates physiologically normal findings accurately."""
        text = "Hemoglobin: 14.5 g/dL\nTotal Cholesterol: 160 mg/dL"
        report = self.engine.analyze_report(text, gender="male", age_years=35.0, pregnancy_status="NOT_PREGNANT")
        self.assertEqual(report.abnormal_metrics, 0)
        self.assertEqual(report.critical_metrics, 0)
        self.assertEqual(report.risk_level, "Low")
        self.assertEqual(report.inconclusive_metrics, 0)

    def test_engine_abnormal_finding(self):
        """Engine flags out-of-range findings as abnormal."""
        text = "Hemoglobin: 10.5 g/dL"
        report = self.engine.analyze_report(text, gender="female", age_years=30.0, pregnancy_status="NOT_PREGNANT")
        self.assertEqual(report.abnormal_metrics, 1)
        self.assertEqual(report.critical_metrics, 0)
        self.assertEqual(report.findings[0].status, MetricStatus.LOW)

    def test_engine_critical_finding_alert(self):
        """Engine triggers critical panic alerts for extreme lab values."""
        text = "Hemoglobin: 6.5 g/dL"
        report = self.engine.analyze_report(text, gender="female", age_years=30.0, pregnancy_status="NOT_PREGNANT")
        self.assertEqual(report.critical_metrics, 1)
        self.assertEqual(report.risk_level, "High")
        self.assertEqual(report.findings[0].status, MetricStatus.CRITICAL_LOW)
        self.assertTrue(report.findings[0].is_critical)
        self.assertIn("Critical low alert", report.findings[0].clinical_note)

    def test_engine_unit_conversion_integration(self):
        """Engine seamlessly converts alternative units before reference interval evaluation."""
        # 5.0 mmol/L fasting glucose = ~90.09 mg/dL -> Normal (70 - 99 mg/dL)
        text = "Fasting Blood Glucose: 5.0 mmol/L"
        report = self.engine.analyze_report(text, gender="male", age_years=40.0, pregnancy_status="NOT_PREGNANT")
        self.assertEqual(report.abnormal_metrics, 0)
        self.assertEqual(report.findings[0].status, MetricStatus.NORMAL)
        self.assertEqual(report.findings[0].unit, "mg/dL")

    def test_engine_unsupported_unit_finding(self):
        """Engine marks finding as INCONCLUSIVE when incoming unit is unsupported."""
        text = "Hemoglobin: 12.0 parsec"
        report = self.engine.analyze_report(text, gender="female", age_years=30.0, pregnancy_status="NOT_PREGNANT")
        self.assertEqual(report.findings[0].status, MetricStatus.INCONCLUSIVE)
        self.assertIn("Unsupported unit", report.findings[0].clinical_note)

    def test_engine_unknown_metric(self):
        """Engine marks finding as UNKNOWN for unrecognized biomarker names."""
        text = "Galactic Particle Density: 99.9 units"
        report = self.engine.analyze_report(text, gender="female", age_years=30.0)
        self.assertEqual(report.findings[0].status, MetricStatus.UNKNOWN)
        self.assertIn("not indexed", report.findings[0].clinical_note)

    def test_engine_diagnostic_thresholds_evaluated(self):
        """Engine checks clinical diagnostic thresholds (e.g. Diabetes, Anemia)."""
        text = "Fasting Blood Glucose: 135 mg/dL"
        report = self.engine.analyze_report(text, gender="male", age_years=45.0, pregnancy_status="NOT_PREGNANT")
        self.assertEqual(report.abnormal_metrics, 1)
        self.assertTrue(len(report.findings[0].diagnostic_alerts) > 0)
        self.assertTrue(any("Diabetes" in a for a in report.findings[0].diagnostic_alerts))


if __name__ == "__main__":
    unittest.main()
