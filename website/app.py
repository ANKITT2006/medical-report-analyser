"""
MediPulse AI — Decoupled Clinical Report Analyzer Backend Service.
REST API service backed entirely by SQLClinicalRepository and DiagnosticEngine.
Zero in-memory hardcoded ranges or static medical recommendations.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from clinical_engine.storage.repository import SQLClinicalRepository
from clinical_engine.pipeline.engine import DiagnosticEngine

PORT = 5000
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "clinical_knowledge.db"))

# Ensure database exists and is seeded
repository = SQLClinicalRepository(db_path=DB_PATH)
if len(repository.list_all_metrics()) == 0:
    seed_json = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "canonical_clinical_dataset.json"))
    if os.path.exists(seed_json):
        repository.bulk_load_dataset(seed_json)

engine = DiagnosticEngine(repository=repository)

class MedicalReportHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            metric_count = len(repository.list_all_metrics())
            protocol_count = len(repository.list_all_protocols())
            response = {
                "status": "ok",
                "service": "MediPulse Schema-Driven Clinical Engine",
                "database_connected": True,
                "registered_biomarkers": metric_count,
                "active_clinical_protocols": protocol_count
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
        elif self.path == "/metrics":
            # Endpoint exposing dynamic registered biomarkers to client
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            metrics = [m.to_dict() for m in repository.list_all_metrics()]
            self.wfile.write(json.dumps({"status": "success", "metrics": metrics}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                query = data.get("query") or data.get("report_text") or ""
                gender = data.get("gender", "all")
                age_group = data.get("age", "adult")

                # Core execution via database-backed diagnostic engine
                analysis_report = engine.analyze_report(
                    report_text=query,
                    gender=gender,
                    age_group=age_group
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(analysis_report.to_dict()).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run(port=PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, MedicalReportHandler)
    print(f"[OK] MediPulse Clinical Engine API running on http://127.0.0.1:{port}")
    print(f"[OK] Connected to SQLite database: {DB_PATH}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run()
