# MediPulse AI — Dataset Specification & Clinical Governance Standards

**Document Version:** 1.2.0 (Phase 2 Finalized)  
**Status:** Canonical Clinical Governance Release  
**Effective Date:** 2026-11-22  
**Terminology Standard:** Regenstrief LOINC Version 2.83 (August 2026)  
**Target Architecture:** Schema-Driven Laboratory Ingestion & Machine Learning Pipeline  

---

## 1. Purpose of the Dataset Specification

The MediPulse AI dataset specification establishes strict data contracts, clinical provenance protocols, and demographic constraints governing all laboratory diagnostic records processed by the system.

This specification serves as the architectural foundation for:
1. **Schema Validation**: Enforcing machine-readable structural integrity via JSON Schema Draft 2020-12.
2. **Clinical Safety & Ground Truth Integrity**: Strictly isolating objective laboratory measurements and biological reference interval deviations from confirmed medical disease diagnoses and automated prescriptions.
3. **Harmonized Units of Measurement**: Enforcing canonical measurement standards with mathematically defined conversion multipliers for alternative laboratory representations.
4. **Machine Learning Readiness**: Defining clean, tabular-extractable feature records suitable for supervised diagnostic classification models without target leakage.

---

## 2. Supported Medical Categories

MediPulse AI strictly supports four core clinical laboratory panels. No additional panels or unindexed biomarkers may be ingested without prior schema revision and clinical governance approval.

| Category ID | Canonical Panel Name | Clinical Scope | Target Biomarkers Count |
| :--- | :--- | :--- | :--- |
| `CBC` | Complete Blood Count with Indices | Hematopoietic status, oxygen transport capacity, immune leukocyte count, and primary hemostasis. | 8 |
| `LIPID_PROFILE` | Lipid & Cardiovascular Profile | Circulating atherogenic sterols, reverse cholesterol transport, and metabolic triglyceride levels (supporting both fasting and nonfasting states). | 4 |
| `DIABETES_PROFILE` | Glycemic & Diabetes Profile | Acute fasting glycemia, casual/random postprandial glucose, and 2-to-3-month non-enzymatic glycated hemoglobin (ADA 2026 Standards). | 3 |
| `KFT` | Kidney Function Test (Renal Panel) | Glomerular filtration clearance (2021 CKD-EPI eGFR), nitrogenous waste elimination, and purine catabolism. | 5 |

**Total Candidate Biomarkers:** 20 distinct biological metrics (forming 21 demographic/sex-stratified baseline intervals).

---

## 3. Strict Separation of Medical Data Concepts

> ### ⚠️ CRITICAL CLINICAL SAFETY RULE
> **An abnormal biomarker value is NOT a medical diagnosis, and a clinical guideline threshold is NOT an automated prescription.**
> 
> Across all JSON data stores, schemas, inference scripts, and future ML features, the following five concepts must remain strictly isolated:
> 
> 1. **Laboratory Reference Interval**: The 95% physiological central interval derived from healthy demographic cohorts (e.g., fasting glucose $70\text{--}99\text{ mg/dL}$).
> 2. **Clinical Diagnostic Threshold**: A validated professional consensus cutoff that, when sustained and accompanied by clinical criteria, confirms disease (e.g., ADA 2026 Diabetes criterion: Fasting Plasma Glucose $\ge 126\text{ mg/dL}$ or HbA1c $\ge 6.5\%$ on two separate samples).
> 3. **Critical Laboratory Limit (Panic Value)**: A physiological extreme representing an immediate threat to life mandating urgent telephone notification (e.g., Glucose $< 45\text{ mg/dL}$ or Platelets $< 50,000\text{ /\mu L}$).
> 4. **Treatment Target**: An evidence-based clinical benchmark under active medical therapy (e.g., $LDL < 70\text{ mg/dL}$ in secondary prevention, $HbA1c < 7.0\%$, $Uric\text{ Acid} < 6.0\text{ mg/dL}$ in gout). Stored strictly as clinical guidance references; **never to be used to generate automated prescriptions or drug titration commands.**
> 5. **Risk Classification Tier**: Epidemiological risk categories (e.g., KDIGO GFR Categories G1–G5; NCEP ATP III cholesterol risk tiers).

---

## 4. Lipid Profiling & Fasting Governance

In alignment with verified **2018 AHA/ACC Multi-Society Blood Cholesterol Guidelines** (Grundy SM et al., Circulation 2019;139:e1082-e1143; 2026 update noted as unresolved pending official release):
1. **Nonfasting Testing Supported as Standard**: Nonfasting lipid testing is clinically acceptable and encouraged for initial cardiovascular risk screening. Fasting duration must be recorded if known, but fasting is **NOT mandatory** for all lipid reports.
2. **Indications for Fasting Lipid Profiles**:
   - Initial nonfasting triglycerides $\ge 400\text{ mg/dL}$.
   - History of hypertriglyceridemic pancreatitis.
   - Determining exact baseline in high-risk patients prior to initiating pharmacotherapy.
   - Borderline calculated LDL-C values near critical decision points.
3. **LDL Methodology Transparency**:
   - The dataset must capture whether LDL-C was **calculated** (e.g., Friedewald equation or Martin-Hopkins method, LOINC `13457-7`) or **directly measured** via enzymatic assay (LOINC `18262-6`).
   - When triglycerides exceed $400\text{ mg/dL}$, the Friedewald formula is mathematically invalid; the system must flag calculated LDL as unreliable and require direct LDL or non-HDL cholesterol.

---

## 5. eGFR Calculation & Chronic Kidney Disease Governance

In alignment with the **KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease**:
1. **Mathematical Nature**: eGFR is a calculated mathematical estimate, not a direct clearance measurement (such as inulin or iohexol clearance).
2. **Age-Dependent Physiology & Reference Benchmark**:
   - The normative range of $90\text{--}130\text{ mL/min/1.73m}^2$ is a baseline benchmark derived from healthy young adult cohorts (ages 18–39).
   - In healthy aging adults, GFR naturally declines at approximately $0.75\text{--}1.0\text{ mL/min/1.73m}^2\text{/year}$ after age 40. In patients $\ge 65$ years, an eGFR of $60\text{--}89\text{ mL/min/1.73m}^2$ is a normal age-related physiological finding and does not constitute CKD in the absence of albuminuria, hematuria, or structural renal damage.
3. **Standard Equation**: All eGFR values must be standardized to the **2021 CKD-EPI Creatinine equation** (without race coefficients):
   $$\text{eGFR}_{\text{cr}} = 142 \times \min(S_{\text{cr}}/\kappa, 1)^\alpha \times \max(S_{\text{cr}}/\kappa, 1)^{-1.200} \times 0.9938^{\text{Age}} \times [1.012 \text{ if female}]$$
   where $\kappa = 0.7$ (female) or $0.9$ (male), $\alpha = -0.241$ (female) or $-0.302$ (male).
4. **Mandatory Longitudinal Requirement**:
   - A diagnosis of Chronic Kidney Disease (CKD) requires documented chronicity ($> 3\text{ months}$) of eGFR $< 60\text{ mL/min/1.73m}^2$ OR persistent markers of kidney damage (e.g., albuminuria $\ge 30\text{ mg/g}$).
   - **A single isolated abnormal eGFR must NEVER be classified autonomously as confirmed CKD.** Transient reductions occur frequently in acute dehydration, hemodynamics, sepsis, or medication effects (AKI).

---

## 6. Glycemic & Diabetes Governance (ADA Standards of Care 2026)

In alignment with the **American Diabetes Association Standards of Care in Diabetes (2026)**:
1. **Diagnostic Thresholds**:
   - Fasting Plasma Glucose (FPG) $\ge 126\text{ mg/dL}$ ($7.0\text{ mmol/L}$) following $\ge 8\text{ hours}$ fast.
   - 2-hour plasma glucose $\ge 200\text{ mg/dL}$ ($11.1\text{ mmol/L}$) during 75g OGTT.
   - HbA1c $\ge 6.5\%$ ($48\text{ mmol/mol}$) using an NGSP-certified, DCCT-standardized assay.
   - In patients presenting with classic hyperglycemic symptoms (polyuria, polydipsia, unexplained weight loss) or acute hyperglycemic crisis: Random Plasma Glucose $\ge 200\text{ mg/dL}$ ($11.1\text{ mmol/L}$). In asymptomatic patients, an elevated random glucose is not diagnostic and requires confirmatory FPG or HbA1c testing. Note that $70\text{--}139\text{ mg/dL}$ represents an expected physiological finding in healthy postprandial individuals, not a rigid universal reference interval.
2. **Confirmatory Testing Rule**: In the absence of unequivocal symptomatic hyperglycemia, diagnosis requires two abnormal results from the same sample or two separate samples collected on different days.
3. **Assay Limitations**: In conditions altering erythrocyte lifespan (hemolytic anemia, end-stage renal disease on dialysis, 2nd/3rd trimester pregnancy, recent transfusion), HbA1c is clinically invalid and plasma blood glucose criteria must be utilized exclusively.

---

## 7. Acute Renal Azotemia & BUN:Creatinine Interpretation Governance

1. **Diagnostic Clue vs. Definitive Diagnosis**:
   - A BUN to Serum Creatinine ratio $> 20:1$ serves as an established diagnostic clue suggesting prerenal azotemia (hypoperfusion or volume depletion).
   - **Crucial Governance Constraint**: This ratio is strictly an indirect clinical clue, NOT an autonomous diagnosis. Non-renal causes frequently cause an elevated ratio including gastrointestinal bleeding (digestion of blood proteins), high-dose corticosteroid catabolism, excessive dietary protein intake, or low baseline muscle mass.
   - Clinical confirmation requires comprehensive volume assessment, urinary indices (e.g. fractional excretion of sodium, FENa), and clinical review.

---

## 7. Expected Record Structure

Every ingested medical report record must validate against [`datasets/schema/medical_report.schema.json`](file:///c:/Users/Ankit's_YOGA/Desktop/report_analyser/datasets/schema/medical_report.schema.json):

```
MedicalReportRecord
├── record_id (UUID / Unique Hex String)
├── provenance (Audit & Origin Tracking)
│   ├── data_tier (REAL_CLINICAL_DEIDENTIFIED | SYNTHETIC_DEVELOPMENT | CANONICAL_BENCHMARK)
│   ├── ingestion_timestamp (ISO 8601 UTC)
│   ├── collection_timestamp (ISO 8601 UTC | null)
│   ├── source_facility_type (HOSPITAL_LAB | OUTPATIENT_DIAGNOSTIC_CENTER | etc.)
│   └── deidentification_method (HIPAA_SAFE_HARBOR | EXPERT_DETERMINATION | etc.)
├── patient_demographics (Clinical Confounders & Interval Selectors)
│   ├── age_years (Integer: 0 to 125)
│   ├── biological_sex (male | female | unspecified)
│   ├── pregnancy_status (NOT_PREGNANT | FIRST_TRIMESTER | etc.)
│   └── fasting_duration_hours (Float: 0.0 to 72.0 | null)
├── panel_type (CBC | LIPID_PROFILE | DIABETES_PROFILE | KFT)
├── observations [Array of Measured Biomarkers]
│   ├── metric_id (Canonical ID)
│   ├── loinc_code (LOINC Universal Code, e.g., '718-7')
│   ├── raw_token (Original text as parsed)
│   ├── measured_value (Float | null)
│   ├── unit (Extracted reported unit)
│   ├── standardized_value (Converted value in canonical unit)
│   ├── standardized_unit (Canonical unit)
│   ├── reference_interval_applied (Demographic-specific range)
│   └── status (NORMAL | LOW | ELEVATED | CRITICAL_LOW | CRITICAL_HIGH | etc.)
└── clinical_assessment (Strictly Segregated Evaluation)
    ├── biomarker_abnormality_summary (Objective text summary)
    ├── has_critical_alert (Boolean)
    ├── confirmed_diagnoses [Array of Validated Medical Diagnoses]
    │   ├── condition_name (Clinical string)
    │   ├── icd_10_code (e.g., 'E11.9', 'D50.9')
    │   ├── diagnostic_evidence_type (REPEATED_CONFIRMATORY_LABS | PHYSICIAN_DOCUMENTED | etc.)
    │   └── verification_source (Hospital registry, physician ID, etc.)
    └── differential_considerations [Array of non-diagnostic patterns]
```

---

## 8. Separation of Synthetic Development and Real Clinical Records

To maintain absolute ethical compliance and benchmark integrity:
1. Every record must declare its `provenance.data_tier`:
   - `REAL_CLINICAL_DEIDENTIFIED`: Real human laboratory records de-identified in strict adherence to HIPAA Safe Harbor (45 CFR § 164.514(b)(2)) or Expert Determination.
   - `SYNTHETIC_DEVELOPMENT`: Computer-generated development records used strictly for UI testing and pipeline unit verification.
   - `CANONICAL_BENCHMARK`: Curated, expert-reviewed benchmark cases used to verify algorithm precision.
2. Synthetic and real clinical records must **never be co-mingled** in the same dataset files or directories.
3. Models intended for clinical validation must be trained and evaluated strictly on verified real clinical records or clearly segregated benchmark splits.

---
*End of Dataset Specification.*
