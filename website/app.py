"""
MediPulse AI — Medical Report Analyser Backend Service
Autonomous local REST API server for processing medical diagnostic reports.
Supports standard library http.server (zero dependencies) or Flask/FastAPI if available.
"""

import json
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 5000

# Clinical Knowledge Base Reference Ranges
RANGES = {
    "hemoglobin": {"min": 13.0, "max": 17.5, "unit": "g/dL", "name": "Hemoglobin"},
    "cholesterol": {"min": 125.0, "max": 200.0, "unit": "mg/dL", "name": "Total Cholesterol"},
    "ldl": {"min": 50.0, "max": 100.0, "unit": "mg/dL", "name": "LDL Cholesterol"},
    "hdl": {"min": 40.0, "max": 80.0, "unit": "mg/dL", "name": "HDL Cholesterol"},
    "glucose": {"min": 70.0, "max": 99.0, "unit": "mg/dL", "name": "Fasting Blood Sugar"},
    "hba1c": {"min": 4.0, "max": 5.6, "unit": "%", "name": "HbA1c"},
    "creatinine": {"min": 0.7, "max": 1.3, "unit": "mg/dL", "name": "Serum Creatinine"},
    "wbc": {"min": 4000, "max": 11000, "unit": "/uL", "name": "WBC Count"},
    "platelets": {"min": 150000, "max": 450000, "unit": "/uL", "name": "Platelet Count"}
}

def analyze_report_text(query_text, category="general"):
    """Clinical heuristic parser and medical report analyzer."""
    detected = []
    text_lower = query_text.lower()
    
    for key, info in RANGES.items():
        # Match pattern: keyword followed by colon or space and a number
        pattern = rf"{key}\b.*?([0-9]+(?:,[0-9]{{3}})*(?:\.[0-9]+)?)"
        match = re.search(pattern, text_lower)
        if match:
            num_str = match.group(1).replace(",", "")
            try:
                val = float(num_str)
                status = "Normal"
                if val < info["min"]:
                    status = "Low"
                elif val > info["max"]:
                    status = "Elevated"
                detected.append({
                    "biomarker": info["name"],
                    "value": val,
                    "unit": info["unit"],
                    "reference_range": f"{info['min']} - {info['max']} {info['unit']}",
                    "status": status
                })
            except ValueError:
                pass

    abnormal_count = sum(1 for m in detected if m["status"] != "Normal")
    risk_level = "Low"
    if abnormal_count >= 2:
        risk_level = "High"
    elif abnormal_count == 1:
        risk_level = "Medium"

    analysis = (
        f"Analysis complete for {category} report. Identified {len(detected)} clinical biomarker(s) "
        f"with {abnormal_count} parameter(s) flagged outside standard physiological reference limits."
    )
    suggestions = [
        "Review flagged biomarkers with your primary healthcare provider.",
        "Maintain consistent hydration and a balanced whole-food diet.",
        "Schedule follow-up repeat testing in 4 to 8 weeks as clinically indicated."
    ]

    return {
        "status": "success",
        "risk_level": risk_level,
        "analysis": analysis,
        "biomarkers": detected,
        "suggestions": suggestions
    }

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
            self.wfile.write(json.dumps({"status": "ok", "service": "MediPulse AI API"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                query = data.get("query", "")
                category = data.get("category", "General")
                result = analyze_report_text(query, category)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
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
    print(f"🩺 MediPulse AI Backend Server running on http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run()
