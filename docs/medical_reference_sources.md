# MediPulse AI — Medical Reference Sources & Provenance Index

**Document Version:** 1.2.0 (Phase 2 Finalized)  
**Status:** Audited Clinical Bibliography & Terminology Index  
**Effective Date:** 2026-11-22  
**Terminology Standard:** Regenstrief LOINC Version 2.83 (August 2026)

This index documents every professional medical society clinical practice guideline, consensus criteria document, universal terminology standard, and peer-reviewed laboratory reference source consulted to establish reference intervals, diagnostic criteria, and critical limits for the 20 canonical biomarkers supported by MediPulse AI.

---

## 1. Universal Clinical Terminology Registries

### Logical Observation Identifiers Names and Codes (LOINC 2.83)
- **Organization**: Regenstrief Institute, Inc.
- **Document / Resource Title**: LOINC Universal Laboratory Database (Version 2.83)
- **Publication / Revision Date**: August 2026
- **Official URL**: https://loinc.org
- **Biomarkers Supported**: All 20 canonical metrics:
  - `hemoglobin`: `718-7` (Hemoglobin [Mass/volume] in Blood)
  - `rbc`: `789-8` (Erythrocytes [#/volume] in Blood by Automated count)
  - `wbc`: `6690-2` (Leukocytes [#/volume] in Blood by Automated count)
  - `platelets`: `777-3` (Platelets [#/volume] in Blood by Automated count)
  - `mcv`: `787-2` (MCV [Entitic volume] by Automated count)
  - `mch`: `785-6` (MCH [Entitic mass] by Automated count)
  - `mchc`: `28540-3` (MCHC [Mass/volume] by Automated count)
  - `hematocrit`: `4544-3` (Hematocrit [Volume Fraction] of Blood by Automated count)
  - `cholesterol_total`: `2093-3` (Cholesterol [Mass/volume] in Serum or Plasma)
  - `ldl`: `13457-7` (Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation)
  - `hdl`: `2085-9` (Cholesterol in HDL [Mass/volume] in Serum or Plasma)
  - `triglycerides`: `2571-8` (Triglyceride [Mass/volume] in Serum or Plasma)
  - `glucose_fasting`: `1558-6` (Fasting glucose [Mass/volume] in Serum or Plasma)
  - `glucose_random`: `2345-7` (Glucose [Mass/volume] in Serum or Plasma)
  - `hba1c`: `4548-4` (Hemoglobin A1c/Hemoglobin.total in Blood)
  - `creatinine`: `2160-0` (Creatinine [Mass/volume] in Serum or Plasma)
  - `urea`: `22703-3` (Urea [Mass/volume] in Serum or Plasma)
  - `bun`: `3094-0` (Urea nitrogen [Mass/volume] in Serum or Plasma)
  - `egfr`: `33914-3` (Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area] in Serum, Plasma or Blood by Creatinine-based formula)
  - `uric_acid`: `3084-1` (Urate [Mass/volume] in Serum or Plasma)
- **Information Extracted & Verified**: Complete LOINC fully specified names (Component, Property, Time Aspect, System/Specimen, Scale Type, and Method Type).
- **Licensing / Terms**: Open access worldwide under Regenstrief Institute LOINC terms of use.

---

## 2. Complete Blood Count (CBC) Reference Sources

### World Health Organization (WHO)
- **Organization**: World Health Organization (Department of Nutrition for Health and Development)
- **Document Title**: *Haemoglobin concentrations for the diagnosis of anaemia and assessment of severity* (WHO/NMH/NHD/MNM/11.1)
- **Publication / Revision Date**: 2011
- **Official URL**: https://www.who.int/publications/i/item/WHO-NMH-NHD-MNM-11.1
- **Biomarkers Supported**: `hemoglobin`
- **Information Extracted**: Diagnostic cutoffs for anemia in adult males ($< 13.0\text{ g/dL}$), non-pregnant females ($< 12.0\text{ g/dL}$), and pregnant females ($< 11.0\text{ g/dL}$).
- **Licensing / Terms**: WHO Open Access (CC BY-NC-SA 3.0 IGO).

### International Council for Standardization in Haematology (ICSH)
- **Organization**: International Council for Standardization in Haematology
- **Document Title**: *ICSH recommendations for the analysis of red blood cells and automated cell counting*
- **Publication / Revision Date**: 2014
- **Official URL**: https://onlinelibrary.wiley.com/doi/10.1111/ijlh.12260
- **Biomarkers Supported**: `mcv`, `mch`, `mchc`, `hematocrit`, `rbc`
- **Information Extracted**: Reference interval boundaries for erythrocyte indices ($MCV: 80\text{--}100\text{ fL}$, $MCH: 27\text{--}33\text{ pg}$, $MCHC: 32\text{--}36\text{ g/dL}$), calculation formulas, and quality control limits.
- **Licensing / Terms**: Peer-reviewed medical literature (International Journal of Laboratory Hematology).

### National Library of Medicine (MedlinePlus) — Hematology
- **Organization**: U.S. National Library of Medicine (NLM), National Institutes of Health (NIH)
- **Document Title**: MedlinePlus Medical Encyclopedia Laboratory Test Guides: *RBC count*, *WBC count*, *Platelet count*, *Hematocrit*, *RBC indices*
- **Publication / Revision Date**: 2024–2026
- **Official URL**: https://medlineplus.gov/ency/article/003648.htm
- **Biomarkers Supported**: `rbc`, `wbc`, `platelets`, `hematocrit`, `mcv`, `mch`, `mchc`, `hemoglobin`
- **Information Extracted**: 95% physiological central intervals from healthy adult cohorts, specimen interference factors, and physiological variables.
- **Licensing / Terms**: Public domain (U.S. Federal Government information).

---

## 3. Lipid & Cardiovascular Profile Sources

### American Heart Association / American College of Cardiology (AHA/ACC) — Cholesterol Guidelines
- **Organization**: AHA / ACC / AACVPR / AAPA / ABC / ACPM / ADA / AGS / APhA / ASPC / NLA / PCNA Multi-Society Task Force
- **Document Title**: *2018 AHA/ACC/AACVPR/AAPA/ABC/ACPM/ADA/AGS/APhA/ASPC/NLA/PCNA Guideline on the Management of Blood Cholesterol* (Circulation 2019;139:e1082–e1143)
- **Publication / Revision Date**: 2018 (Officially published in Circulation, June 2019)
- **Official DOI & URL**: https://doi.org/10.1161/CIR.0000000000000625
- **Biomarkers Supported**: `cholesterol_total`, `ldl`, `hdl`, `triglycerides`
- **Information Extracted & Verified**:
  - Full clinical support for **nonfasting lipid profiles** as standard initial screening.
  - Specific clinical criteria for requiring fasting lipid testing (10–12 hours): nonfasting triglycerides $\ge 400\text{ mg/dL}$, personal/family history of severe hypertriglyceridemia, or borderline calculated LDL-C.
  - Severe hypercholesterolemia risk thresholds ($LDL \ge 190\text{ mg/dL}$ or Total Cholesterol $\ge 290\text{ mg/dL}$) prompting physician evaluation.
  - Secondary prevention target benchmarks ($LDL < 70\text{ mg/dL}$, or $< 55\text{ mg/dL}$ in very-high-risk patients).
  - Clarified that guideline thresholds represent **clinical decision-support references**, not automatic prescription rules.
- **Unresolved Citation Note**: Allegations of an official "2026 ACC/AHA Focused Update" were thoroughly audited across medical literature registries. As of November 2026, no standalone publication or formal update by the AHA/ACC titled "2026 Focused Update on Management of Blood Cholesterol" with an active DOI exists. The MediPulse AI knowledge base strictly retains the verified **2018 AHA/ACC Guideline** as the canonical clinical ground truth, and categorizes the alleged 2026 update as `UNRESOLVED_PENDING_OFFICIAL_PUBLICATION`.
- **Licensing / Terms**: Open Access journal publication (AHA/ACC).

### National Cholesterol Education Program (NCEP) Adult Treatment Panel III
- **Organization**: National Heart, Lung, and Blood Institute (NHLBI)
- **Document Title**: *Third Report of the National Cholesterol Education Program (NCEP) Expert Panel on Detection, Evaluation, and Treatment of High Blood Cholesterol in Adults (Adult Treatment Panel III)*
- **Publication / Revision Date**: 2002 (NIH Publication No. 02-5215)
- **Official URL**: https://www.nhlbi.nih.gov/files/docs/guidelines/atp3full.pdf
- **Biomarkers Supported**: `cholesterol_total`, `ldl`, `hdl`, `triglycerides`
- **Information Extracted**: Standard clinical risk classification tiers (Desirable, Borderline High, High) and HDL risk factor cutoffs ($< 40\text{ mg/dL}$ in men, $< 50\text{ mg/dL}$ in women).
- **Licensing / Terms**: Public domain (U.S. Government publication).

---

## 4. Glycemic & Diabetes Profile Sources

### American Diabetes Association (ADA) Standards of Care 2026
- **Organization**: American Diabetes Association (Professional Practice Committee)
- **Document Title**: *Standards of Care in Diabetes—2026: Classification and Diagnosis of Diabetes / Glycemic Targets*
- **Publication / Revision Date**: January 2026
- **Official URL**: https://diabetesjournals.org/care/issue
- **Biomarkers Supported**: `glucose_fasting`, `glucose_random`, `hba1c`
- **Information Extracted**:
  - Diagnostic criteria for Diabetes Mellitus:
    - Fasting Plasma Glucose (FPG) $\ge 126\text{ mg/dL}$ ($7.0\text{ mmol/L}$) following $\ge 8\text{ hours}$ fast.
    - HbA1c $\ge 6.5\%$ ($48\text{ mmol/mol}$) using an NGSP-certified assay.
    - Two-hour plasma glucose $\ge 200\text{ mg/dL}$ during 75g OGTT.
    - In patients with classic hyperglycemic symptoms or crisis: Random Plasma Glucose $\ge 200\text{ mg/dL}$ ($11.1\text{ mmol/L}$).
  - Requirement for confirmatory repeat testing: In the absence of unequivocal symptomatic hyperglycemia, diagnosis requires two abnormal results from the same sample or two separate samples.
  - Prediabetes diagnostic categories: FPG $100\text{--}125\text{ mg/dL}$ (Impaired Fasting Glucose); HbA1c $5.7\%\text{--}6.4\%$.
  - General adult glycemic target: $HbA1c < 7.0\%$ (tailored by clinician to $< 6.5\%$ or $< 8.0\%$ based on patient vulnerability).
  - Explicit documentation of clinical limitations: HbA1c is unreliable in conditions altering erythrocyte turnover (hemolysis, hemodialysis, pregnancy, hemoglobinopathies).
- **Licensing / Terms**: Open access clinical practice guidelines (American Diabetes Association).

---

## 5. Kidney Function Test (KFT / Renal Panel) Sources

### Kidney Disease: Improving Global Outcomes (KDIGO) — CKD
- **Organization**: KDIGO Work Group
- **Document Title**: *KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease* (Kidney International 2024;105(4S):S117–S314)
- **Publication / Revision Date**: April 2024
- **Official URL**: https://kdigo.org/guidelines/ckd-evaluation-and-management/
- **Biomarkers Supported**: `egfr`, `creatinine`
- **Information Extracted**:
  - **Diagnostic Criterion for CKD**: eGFR $< 60\text{ mL/min/1.73m}^2$ documented for $> 3\text{ months}$, OR markers of kidney damage (albuminuria $\ge 30\text{ mg/g}$) present for $> 3\text{ months}$.
  - **Explicit Rule on Single Results**: A single isolated eGFR $< 60$ without historical verification does NOT confirm Chronic Kidney Disease.
  - Adoption of the **2021 CKD-EPI Creatinine equation** without race coefficient.
  - GFR Categories G1 through G5 defined as functional tiers, not standalone disease diagnoses.
- **Licensing / Terms**: Open access under CC BY-NC-ND 4.0 license.

### KDIGO — Acute Kidney Injury (AKI)
- **Organization**: KDIGO Work Group
- **Document Title**: *KDIGO Clinical Practice Guideline for Acute Kidney Injury* (Kidney International Supplements 2012;2(1):1–138)
- **Publication / Revision Date**: March 2012
- **Official URL**: https://kdigo.org/guidelines/acute-kidney-injury/
- **Biomarkers Supported**: `creatinine`, `bun`
- **Information Extracted**: KDIGO AKI staging criteria (increase in serum creatinine by $\ge 0.3\text{ mg/dL}$ within 48h, or $\ge 1.5\times$ baseline). BUN:Creatinine ratio interpretation ($> 20:1$ serves as an indirect clinical clue for prerenal hypoperfusion/volume depletion, but is not an autonomous diagnosis and requires differential exclusion of GI bleeding, corticosteroids, and high protein intake).
- **Licensing / Terms**: Open access under KDIGO permissions.

---

## 6. Critical Laboratory Panic Values & Alert Policy Sources

### Massachusetts General Hospital & Kost National Survey Medians
- **Organizations**: Massachusetts General Hospital (MGH Laboratory Handbook) & College of American Pathologists (CAP) / Kost Critical Values Survey
- **Foundational Documents**:
  - Kost GJ. *Critical limits for urgent clinician notification at US medical centers.* JAMA / Am J Clin Pathol 1990;93(4):511-527.
  - Howanitz PJ, Steindel SJ, Heard NV. *Laboratory critical values policies and practices: a College of American Pathologists Q-Probes study in 623 institutions.* Arch Pathol Lab Med 2002;126(6):663-669.
  - MGH Clinical Laboratory Handbook Critical Values Policy (Current Clinical Standards).
- **Biomarkers Supported**: Panic limits for `hemoglobin`, `wbc`, `platelets`, `hematocrit`, `glucose_fasting`, `glucose_random`, `creatinine`, `urea`, `bun`.
- **Clinical Governance Principle**: Critical laboratory limits are institution-dependent policy benchmarks designed for urgent telephone communication. They reflect hospital-specific patient populations, instrumentation, and outpatient vs. intensive care settings rather than absolute universal biological laws.

### Clinical Practice Guidelines for Critical Disease Alerts
- **Endocrine Society / American Gastroenterological Association (AGA)**: Triglycerides $\ge 1,000\text{ mg/dL}$ designated as a clinical alert threshold for chylomicronemia and acute pancreatitis risk.
- **American Society of Clinical Oncology (ASCO)**: Serum uric acid $> 12.0\text{ mg/dL}$ designated as a clinical alert threshold for acute urate nephropathy and Tumor Lysis Syndrome (TLS).
- **KDIGO Guidelines**: eGFR $< 15\text{ mL/min/1.73m}^2$ designated as a clinical practice alert threshold for Kidney Failure (Stage 5 CKD / G5) prompting urgent renal replacement planning.

### American College of Rheumatology (ACR) — Gout
- **Organization**: American College of Rheumatology
- **Document Title**: *2020 American College of Rheumatology Guideline for the Management of Gout* (Arthritis Care Res 2020;72(6):744–760)
- **Publication / Revision Date**: June 2020
- **Official URL**: https://doi.org/10.1002/acr.24180
- **Biomarkers Supported**: `uric_acid`
- **Information Extracted**: Physicochemical supersaturation threshold ($6.8\text{ mg/dL}$ at $37^\circ\text{C}$); clinical principle that asymptomatic hyperuricemia does NOT establish clinical gout and does NOT warrant automated urate-lowering therapy; therapeutic target during active treatment ($< 6.0\text{ mg/dL}$).
- **Licensing / Terms**: Open access clinical practice guideline.

---
*End of Corrected Medical Reference Sources & Provenance Index.*
