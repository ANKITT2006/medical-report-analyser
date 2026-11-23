"""
Test suite verifying the decoupled schema-driven clinical ingestion pipeline.
"""

import os
import gc
import unittest
from clinical_engine.storage.repository import SQLClinicalRepository
from clinical_engine.pipeline.parser import ClinicalReportParser
from clinical_engine.pipeline.engine import DiagnosticEngine
from clinical_engine.domain.schemas import MetricStatus

class TestClinicalEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = "data/test_clinical_knowledge.db"
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except OSError:
                pass
        cls.repo = SQLClinicalRepository(db_path=cls.test_db)
        
        # Load canonical dataset
        json_path = os.path.join(os.path.dirname(__file__), "..", "data", "canonical_clinical_dataset.json")
        cls.repo.bulk_load_dataset(json_path)
        cls.engine = DiagnosticEngine(repository=cls.repo)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except OSError:
                pass

    def test_parser_feature_extraction(self):
        text = "Hemoglobin: 10.2 g/dL\nFasting Blood Glucose = 135 mg/dL\nUnknown Marker: 99.5"
        observations = ClinicalReportParser.parse_text(text)
        self.assertEqual(len(observations), 3)
        self.assertEqual(observations[0].raw_key, "Hemoglobin")
        self.assertEqual(observations[0].detected_value, 10.2)
        self.assertEqual(observations[1].raw_key, "Fasting Blood Glucose")
        self.assertEqual(observations[1].detected_value, 135.0)

    def test_database_metric_lookup_and_aliases(self):
        metric_hb = self.repo.get_metric_reference("hb", gender="female")
        self.assertIsNotNone(metric_hb)
        self.assertEqual(metric_hb.metric_id, "hemoglobin")
        self.assertEqual(metric_hb.gender, "female")
        self.assertEqual(metric_hb.min_normal, 12.0)

        metric_fbs = self.repo.get_metric_reference("fasting blood sugar")
        self.assertIsNotNone(metric_fbs)
        self.assertEqual(metric_fbs.metric_id, "glucose_fasting")

    def test_unknown_metric_handling(self):
        text = "SyntheticProteinX: 45.0 ug/L"
        report = self.engine.analyze_report(text)
        self.assertEqual(report.total_metrics, 1)
        self.assertEqual(report.findings[0].status, MetricStatus.UNKNOWN)
        self.assertEqual(report.findings[0].reference_range_text, "Outside Reference Database")
        self.assertFalse(report.findings[0].is_abnormal)

    def test_anemia_abnormal_report(self):
        text = "Hemoglobin: 9.5 g/dL\nRBC Count: 3.1 M/uL"
        report = self.engine.analyze_report(text, gender="female")
        self.assertEqual(report.abnormal_metrics, 2)
        self.assertEqual(report.risk_level, "Medium")
        self.assertTrue(any(p.protocol_id == "PROTO-ANEMIA-01" for p in report.protocols_applied))
        self.assertTrue(len(report.dietary_recommendations) > 0)
        self.assertTrue(any("iron" in item.lower() for item in report.dietary_recommendations))

    def test_critical_abnormal_report(self):
        text = "Hemoglobin: 6.8 g/dL"
        report = self.engine.analyze_report(text, gender="female")
        self.assertEqual(report.critical_metrics, 1)
        self.assertEqual(report.risk_level, "High")

    def test_optimal_healthy_baseline(self):
        text = "Hemoglobin: 14.5 g/dL\nTotal Cholesterol: 160 mg/dL\nFasting Glucose: 85 mg/dL"
        report = self.engine.analyze_report(text, gender="male")
        self.assertEqual(report.abnormal_metrics, 0)
        self.assertEqual(report.risk_level, "Low")
        self.assertIn("All tested parameters comfortably reside within established physiological reference intervals", report.clinical_narrative)

if __name__ == "__main__":
    unittest.main()
