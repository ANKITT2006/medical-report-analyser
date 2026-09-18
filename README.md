# 🩺 MediPulse AI — Medical Report Analyser

An intelligent, AI-powered healthcare web application designed to translate complex medical reports and diagnostic lab results into plain-English, clinically grounded insights.

> ⚠️ **Disclaimer:** MediPulse AI is an educational and demonstrational prototype designed for health literacy and accessibility. It is **not** a substitute for professional medical advice, diagnosis, or clinical treatment. Always consult a licensed healthcare professional.

---

## 📌 Project Overview

Medical lab reports often contain confusing acronyms and reference numbers (e.g. MCV, MCH, HbA1c, eGFR, SGPT) that can be difficult for patients to understand. **MediPulse AI** bridges this gap by automatically extracting biomarkers, evaluating them against gender- and age-calibrated clinical reference ranges, and generating clear patient summaries, dietary suggestions, and doctor consultation questions.

---

## ✨ Features

- ⚡ **Instant Multi-Panel Biomarker Engine:** Automatically detects and extracts 40+ clinical parameters across:
  - **Complete Blood Count (CBC):** Hemoglobin, RBC, WBC, Platelets, Hematocrit, MCV, MCH, Ferritin
  - **Lipid & Cardiovascular Panel:** Total Cholesterol, HDL ("Good"), LDL ("Bad"), Triglycerides
  - **Metabolic & Diabetes Profile:** Fasting Blood Sugar, HbA1c
  - **Kidney / Renal Function:** Serum Creatinine, Blood Urea Nitrogen (BUN), eGFR, Uric Acid
  - **Liver / Hepatic Function:** ALT / SGPT, AST / SGOT, Total Bilirubin
  - **Thyroid:** TSH (Thyroid Stimulating Hormone)
- 📊 **Visual Range Position Meters:** Interactive gauges showing where your biomarker falls (`[ Low | Normal | High ]`).
- 🧪 **1-Click Pre-loaded Clinical Cases:** Test instantly with realistic scenarios:
  1. *Complete Blood Count (CBC) — Microcytic Anemia*
  2. *Lipid Profile — Cardiovascular Risk*
  3. *Comprehensive Metabolic Panel — Diabetes & Renal Strain*
  4. *Routine Wellness Checkup — Optimal Baseline*
- 📄 **Flexible Input Support:** Drag-and-drop file upload (TXT, CSV, PDF/Image OCR preview) or direct text pasting.
- 🥗 **Tailored Lifestyle Guidance:** Personalized dietary recommendations, physical activity plans, and items to avoid based on flagged markers.
- 🩺 **Doctor Discussion Prep Kit:** High-yield questions to ask your healthcare provider at your next visit.
- 💬 **Interactive AI Health Assistant:** In-app medical Q&A chat for follow-up inquiries.
- 🖨️ **Print & Export:** One-click formatted PDF printing and summary clipboard export.
- 🌓 **Dark / Light Theme:** Modern clinical glassmorphism design with persistent theme toggle.

---

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3 (Modern Glassmorphism & Custom Properties), Vanilla JavaScript (ES6+ Modules)
- **Tooling & Dev Server:** Vite 8
- **Backend Service:** Python (Built-in standard library HTTP server or Flask/FastAPI)
- **Typography & Icons:** Google Fonts (*Outfit* & *Plus Jakarta Sans*), Font Awesome 6

---

## 🚀 Quick Start & Installation

### Prerequisites
- **Node.js:** v18.0.0 or later
- **npm:** v9.0.0 or later
- *(Optional)* Python 3.9+ for backend API

### 1. Clone the Repository
```bash
git clone https://github.com/ANKITT2006/medical-report-analyser.git
cd medical-report-analyser
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Run Development Server
```bash
npm run dev
```
Open your browser and navigate to:
```
http://localhost:5173/
```

### 4. Optional: Run Python Backend
```bash
python website/app.py
```
*(The frontend runs fully standalone client-side out of the box, with optional hybrid fallback to the Python backend).*

---

## 📂 Project Structure

```
medical-report-analyser/
├── website/
│   ├── index.html      # Main clinical web application interface
│   ├── style.css       # Healthcare theme styling, animations & dark mode
│   ├── script.js       # Diagnostic parser, biomarker DB & AI logic
│   └── app.py          # Python REST API backend service
├── package.json        # NPM configuration & scripts
├── package-lock.json   # Locked dependency tree
├── .gitignore          # Git exclusion rules
└── README.md           # Project documentation
```

---

## 👨‍💻 Author

**Ankit Nag**  
B.Tech CSE (AI & ML)  
VIT Bhopal University  
- GitHub: [@ANKIT2006-sudo](https://github.com/ANKIT2006-sudo)  
- Repository: [medical-report-analyser](https://github.com/ANKITT2006/medical-report-analyser)

---

## ⭐ Support & Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/ANKITT2006/medical-report-analyser/issues) if you would like to contribute.

If you found this project helpful, please give it a ⭐️!
