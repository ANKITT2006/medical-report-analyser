# MediPulse AI — Canonical Biomarker Dictionary

**Version:** 1.2.0 (Phase 2 Finalized)  
**Terminology Standard:** LOINC Version 2.83 (Release Date: August 2026, Regenstrief Institute)  
**Last Updated:** 2026-11-22  
**Scope:** 20 Unique Canonical Laboratory Metrics (Covering All 26 Baseline Demographic and Laboratory Context Reference Intervals) across Complete Blood Count (CBC), Lipid Profile, Diabetes Profile, and Kidney Function Test (KFT).

---

## Complete Blood Count (CBC)

### 1. `hemoglobin`
- **Canonical Name**: Hemoglobin
- **LOINC Identifier**: `718-7` — *VERIFIED against LOINC 2.83*
  - **Component**: `Hemoglobin`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Bld` (Whole blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count / Spectrophotometry
- **Category**: `CBC`
- **What it Measures**: Total intravascular mass concentration of the iron-containing metalloprotein in circulating red blood cells that transports oxygen from the pulmonary alveoli to peripheral tissue capillaries.
- **Clinical Relevance**: Primary laboratory indicator for anemia (decreased oxygen carrying capacity) and polycythemia (abnormal increase in red cell mass). Key parameter for evaluating fatigue, hypoxemia, cardiovascular compensation, and acute hemorrhage.
- **Standard Unit**: `g/dL`
- **Supported Alternative Units**:
  - `g/L` ($\text{g/dL} = \text{g/L} \times 0.1$)
  - `mmol/L` ($\text{g/dL} = \text{mmol/L} \times 1.6114$)
- **Common Aliases**: `hemoglobin`, `haemoglobin`, `hb`, `hgb`
- **Applicable Patient Demographics**: Sex-stratified in adults (Male: 13.5–17.5 g/dL; Female: 12.0–15.5 g/dL). Shifts dynamically in pregnancy and with chronic high-altitude exposure.
- **Fasting Requirement**: No.
- **Reference Sources**: World Health Organization (WHO) Haemoglobin Concentrations Guidelines (2011), MedlinePlus Medical Encyclopedia (2024), Tietz Textbook of Clinical Chemistry (6th Ed.).
- **Verification Status**: **VERIFIED**

---

### 2. `rbc`
- **Canonical Name**: Red Blood Cell Count
- **LOINC Identifier**: `789-8` — *VERIFIED against LOINC 2.83*
  - **Component**: `Erythrocytes`
  - **Property**: `NCnc` (Number concentration)
  - **System/Specimen**: `Bld` (Whole blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count
- **Category**: `CBC`
- **What it Measures**: Total concentration of circulating erythrocytes per unit volume of whole blood.
- **Clinical Relevance**: Evaluated alongside hemoglobin and hematocrit to assess erythropoiesis. Decreased in aplastic, hemolytic, or nutritional anemias; increased in primary/secondary polycythemia and hemoconcentration.
- **Standard Unit**: `M/uL` (Million cells per microliter)
- **Supported Alternative Units**:
  - `x10^12/L` ($1.0 \text{ M/uL} = 1.0 \times 10^{12}\text{/L}$)
- **Common Aliases**: `rbc`, `red blood cell`, `red blood cells`, `erythrocytes`, `rbc count`
- **Applicable Patient Demographics**: Sex-stratified in adults (Male: 4.5–5.9 M/uL; Female: 4.0–5.2 M/uL).
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), AACC Laboratory Medicine Guide.
- **Verification Status**: **VERIFIED**

---

### 3. `wbc`
- **Canonical Name**: White Blood Cell Count
- **LOINC Identifier**: `6690-2` — *VERIFIED against LOINC 2.83*
  - **Component**: `Leukocytes`
  - **Property**: `NCnc` (Number concentration)
  - **System/Specimen**: `Bld` (Whole blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count
- **Category**: `CBC`
- **What it Measures**: Total concentration of circulating nucleated leukocytes (neutrophils, lymphocytes, monocytes, eosinophils, basophils) per microliter of blood.
- **Clinical Relevance**: Essential screening parameter for immune defense activation, acute bacterial or viral infection, systemic inflammation, tissue necrosis, leukemia, or bone marrow suppression (leukopenia).
- **Standard Unit**: `/uL`
- **Supported Alternative Units**:
  - `x10^9/L` ($\text{/uL} = \times 10^9\text{/L} \times 1000$)
  - `x10^3/uL` ($\text{/uL} = \times 10^3\text{/uL} \times 1000$)
- **Common Aliases**: `wbc`, `white blood cell`, `white blood cells`, `leukocytes`, `total leukocyte count`
- **Applicable Patient Demographics**: Adults (4,000–11,000 /uL). Pediatric baselines are significantly higher.
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), ACCP/SCCM Sepsis Consensus.
- **Verification Status**: **VERIFIED**

---

### 4. `platelets`
- **Canonical Name**: Platelet Count
- **LOINC Identifier**: `777-3` — *VERIFIED against LOINC 2.83*
  - **Component**: `Platelets`
  - **Property**: `NCnc` (Number concentration)
  - **System/Specimen**: `Bld` (Whole blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count
- **Category**: `CBC`
- **What it Measures**: Number of circulating anucleate cellular fragments (thrombocytes) per microliter of blood.
- **Clinical Relevance**: Crucial for primary hemostasis and vascular clot formation. Thrombocytopenia ($< 150,000\text{ /\mu L}$) increases bleeding risk; extreme thrombocytosis ($> 1,000,000\text{ /\mu L}$) triggers thrombotic and bleeding complications.
- **Standard Unit**: `/uL`
- **Supported Alternative Units**:
  - `x10^9/L` ($\text{/uL} = \times 10^9\text{/L} \times 1000$)
  - `x10^3/uL` ($\text{/uL} = \times 10^3\text{/uL} \times 1000$)
- **Common Aliases**: `platelets`, `platelet count`, `plt`, `thrombocytes`
- **Applicable Patient Demographics**: Adults (150,000–450,000 /uL).
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), American Society of Hematology (ASH).
- **Verification Status**: **VERIFIED**

---

### 5. `mcv`
- **Canonical Name**: Mean Corpuscular Volume
- **LOINC Identifier**: `787-2` — *VERIFIED against LOINC 2.83*
  - **Component**: `Erythrocyte mean corpuscular volume (MCV)`
  - **Property**: `EntVol` (Entitic volume)
  - **System/Specimen**: `RBC` (Red blood cells)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count
- **Category**: `CBC`
- **What it Measures**: Average anatomical volume and physical size of an individual red blood cell.
- **Clinical Relevance**: Fundamental branching metric for morphological anemia classification: microcytic ($< 80\text{ fL}$), normocytic ($80\text{--}100\text{ fL}$), or macrocytic ($> 100\text{ fL}$). Guides downstream testing (iron indices vs. B12/folate).
- **Standard Unit**: `fL` (femtoliters)
- **Supported Alternative Units**: None.
- **Common Aliases**: `mcv`, `mean corpuscular volume`
- **Applicable Patient Demographics**: Adults (80.0–100.0 fL).
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), British Society for Haematology (BSH).
- **Verification Status**: **VERIFIED**

---

### 6. `mch`
- **Canonical Name**: Mean Corpuscular Hemoglobin
- **LOINC Identifier**: `785-6` — *VERIFIED against LOINC 2.83*
  - **Component**: `Erythrocyte mean corpuscular hemoglobin (MCH)`
  - **Property**: `EntMass` (Entitic mass)
  - **System/Specimen**: `RBC` (Red blood cells)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count / Calculated
- **Category**: `CBC`
- **What it Measures**: Average mass of hemoglobin per red blood cell, calculated as $(\text{Hemoglobin} \times 10) / \text{RBC}$.
- **Clinical Relevance**: Reflects cellular hemoglobinization; decreased in hypochromic microcytic anemias.
- **Standard Unit**: `pg` (picograms)
- **Supported Alternative Units**: None.
- **Common Aliases**: `mch`, `mean corpuscular hemoglobin`
- **Applicable Patient Demographics**: Adults (27.0–33.0 pg).
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), Tietz.
- **Verification Status**: **VERIFIED**

---

### 7. `mchc`
- **Canonical Name**: Mean Corpuscular Hemoglobin Concentration
- **LOINC Identifier**: `28540-3` — *VERIFIED against LOINC 2.83*
  - **Component**: `Erythrocyte mean corpuscular hemoglobin concentration (MCHC)`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `RBC` (Red blood cells)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count / Calculated
- **Category**: `CBC`
- **What it Measures**: Average concentration of hemoglobin in a unit volume of packed erythrocytes, calculated as $(\text{Hemoglobin} / \text{Hematocrit}) \times 100$.
- **Clinical Relevance**: Laboratory quality and diagnostic indicator. True elevations ($> 36\text{ g/dL}$) suggest hereditary spherocytosis, severe burn injury, or analyzer artifacts (cold agglutinins, lipemia).
- **Standard Unit**: `g/dL`
- **Supported Alternative Units**:
  - `g/L` ($\text{g/dL} = \text{g/L} \times 0.1$)
- **Common Aliases**: `mchc`, `mean corpuscular hemoglobin concentration`
- **Applicable Patient Demographics**: Adults (32.0–36.0 g/dL).
- **Fasting Requirement**: No.
- **Reference Sources**: International Council for Standardization in Haematology (ICSH), MedlinePlus (2024).
- **Verification Status**: **VERIFIED**

---

### 8. `hematocrit`
- **Canonical Name**: Hematocrit
- **LOINC Identifier**: `4544-3` — *VERIFIED against LOINC 2.83*
  - **Component**: `Hematocrit`
  - **Property**: `VFr` (Volume fraction)
  - **System/Specimen**: `Bld` (Whole blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Automated count
- **Category**: `CBC`
- **What it Measures**: Proportion of whole blood volume occupied by erythrocytes.
- **Clinical Relevance**: Evaluated for anemia and fluid shifts. Serves as a major WHO diagnostic criterion for polycythemia vera ($> 49\%$ in men, $> 48\%$ in women).
- **Standard Unit**: `%`
- **Supported Alternative Units**:
  - `L/L` ($\% = \text{L/L} \times 100$)
- **Common Aliases**: `hematocrit`, `haematocrit`, `hct`, `packed cell volume`, `pcv`
- **Applicable Patient Demographics**: Sex-stratified in adults (Male: 41.0–50.0%; Female: 36.0–46.0%).
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), WHO Hematopoietic Tumour Diagnostic Criteria (2016).
- **Verification Status**: **VERIFIED**

---

## Lipid & Cardiovascular Profile

### 9. `cholesterol_total`
- **Canonical Name**: Total Cholesterol
- **LOINC Identifier**: `2093-3` — *VERIFIED against LOINC 2.83*
  - **Component**: `Cholesterol`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Unspecified / Enzymatic
- **Category**: `LIPID_PROFILE`
- **What it Measures**: Total concentration of circulating cholesterol across all lipoprotein fractions.
- **Clinical Relevance**: Used in global cardiovascular risk calculation (e.g., ASCVD Risk Estimator Plus). Severe elevations ($\ge 290\text{ mg/dL}$) warrant clinical evaluation for familial hypercholesterolemia.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 38.67$)
- **Common Aliases**: `total cholesterol`, `cholesterol total`, `serum cholesterol`, `cholesterol`
- **Applicable Patient Demographics**: Adults ($< 200\text{ mg/dL}$ desirable).
- **Fasting Requirement**: Nonfasting screening is fully acceptable per verified 2018 AHA/ACC guidelines (Circulation 2019;139:e1082-e1143; 2026 update noted as unresolved pending publication).
- **Reference Sources**: 2018 AHA/ACC Blood Cholesterol Guidelines (verified ground truth), NCEP ATP III.
- **Verification Status**: **VERIFIED**

---

### 10. `ldl`
- **Canonical Name**: Low-Density Lipoprotein Cholesterol
- **LOINC Identifier**: `13457-7` — *VERIFIED against LOINC 2.83*
  - **Component**: `Cholesterol.in LDL`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Calculated (Friedewald / Martin-Hopkins equation)
  - *Note on Alternative Direct LOINC*: Direct enzymatic LDL measurement maps to LOINC `18262-6`.
- **Category**: `LIPID_PROFILE`
- **What it Measures**: Cholesterol transported within atherogenic apolipoprotein B-100 particles.
- **Clinical Relevance**: Primary causal risk factor and guideline therapeutic target for atherosclerotic cardiovascular disease. Thresholds ($\ge 190\text{ mg/dL}$ or $< 70\text{ mg/dL}$ target) serve as clinical decision support references, not autonomous prescription instructions.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 38.67$)
- **Common Aliases**: `ldl`, `ldl cholesterol`, `low density lipoprotein`, `bad cholesterol`, `ldl-c`
- **Applicable Patient Demographics**: Adults ($< 100\text{ mg/dL}$ optimal; $< 70\text{ mg/dL}$ or $< 55\text{ mg/dL}$ in high/very-high risk).
- **Fasting Requirement**: Nonfasting screening supported. Fasting (10–12h) recommended if nonfasting triglycerides $\ge 400\text{ mg/dL}$ or when calculating Friedewald LDL in borderline patients.
- **Reference Sources**: 2018 AHA/ACC Cholesterol Guidelines (Circulation 2019;139:e1082-e1143; verified ground truth), ESC/EAS Guidelines.
- **Verification Status**: **VERIFIED**

---

### 11. `hdl`
- **Canonical Name**: High-Density Lipoprotein Cholesterol
- **LOINC Identifier**: `2085-9` — *VERIFIED against LOINC 2.83*
  - **Component**: `Cholesterol.in HDL`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Direct enzymatic or precipitation
- **Category**: `LIPID_PROFILE`
- **What it Measures**: Cholesterol content within high-density lipoproteins mediating reverse cholesterol transport.
- **Clinical Relevance**: Sub-optimal levels ($< 40\text{ mg/dL}$ in men, $< 50\text{ mg/dL}$ in women) serve as one component criterion for Metabolic Syndrome. Levels $\ge 60\text{ mg/dL}$ confer cardioprotection.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 38.67$)
- **Common Aliases**: `hdl`, `hdl cholesterol`, `high density lipoprotein`, `good cholesterol`, `hdl-c`
- **Applicable Patient Demographics**: Sex-stratified (Male: $\ge 40\text{ mg/dL}$; Female: $\ge 50\text{ mg/dL}$).
- **Fasting Requirement**: No. Stable across postprandial states.
- **Reference Sources**: NCEP ATP III, AHA/NHLBI Metabolic Syndrome Statement.
- **Verification Status**: **VERIFIED**

---

### 12. `triglycerides`
- **Canonical Name**: Triglycerides
- **LOINC Identifier**: `2571-8` — *VERIFIED against LOINC 2.83*
  - **Component**: `Triglyceride`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Enzymatic colorimetric assay
- **Category**: `LIPID_PROFILE`
- **What it Measures**: Concentration of circulating glycerol-bound fatty acids.
- **Clinical Relevance**: Elevated in insulin resistance, metabolic syndrome, and hepatic steatosis. Marked elevations ($\ge 500\text{--}1,000\text{ mg/dL}$) trigger significant risk of acute pancreatitis.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 88.57$)
- **Common Aliases**: `triglycerides`, `triglyceride`, `tg`, `serum triglycerides`
- **Applicable Patient Demographics**: Adults ($< 150\text{ mg/dL}$ desirable baseline).
- **Fasting Requirement**: **Both fasting and nonfasting profiles are supported per 2018 AHA/ACC guidelines.** Nonfasting levels are $\sim 20\text{--}30\text{ mg/dL}$ higher. Fasting is specifically recommended when nonfasting levels exceed $400\text{ mg/dL}$ or in recurrent pancreatitis.
- **Reference Sources**: 2018 AHA/ACC Dyslipidemia Guidelines (Circulation 2019;139:e1082-e1143; verified ground truth), Endocrine Society Guidelines, NCEP ATP III.
- **Verification Status**: **VERIFIED**

---

## Glycemic & Diabetes Profile

### 13. `glucose_fasting`
- **Canonical Name**: Fasting Plasma Glucose
- **LOINC Identifier**: `1558-6` — *VERIFIED against LOINC 2.83*
  - **Component**: `Fasting glucose`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Enzymatic (hexokinase or glucose oxidase)
- **Category**: `DIABETES_PROFILE`
- **What it Measures**: Venous plasma glucose concentration following a mandatory fast of at least 8 hours.
- **Clinical Relevance**: Standard screening and diagnostic test for diabetes mellitus per ADA Standards of Care (2026). Diagnostic criteria: Normal ($70\text{--}99\text{ mg/dL}$), Impaired Fasting Glucose ($100\text{--}125\text{ mg/dL}$), Diabetes Mellitus ($\ge 126\text{ mg/dL}$, requiring confirmatory repeat testing).
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 18.0182$)
- **Common Aliases**: `fasting blood glucose`, `fasting glucose`, `fbg`, `fbs`, `fasting blood sugar`
- **Applicable Patient Demographics**: Adults.
- **Fasting Requirement**: **Yes**, strictly $\ge 8$ hours of zero caloric intake.
- **Reference Sources**: American Diabetes Association (ADA) Standards of Care in Diabetes (2026).
- **Verification Status**: **VERIFIED**

---

### 14. `glucose_random`
- **Canonical Name**: Random Plasma Glucose
- **LOINC Identifier**: `2345-7` — *VERIFIED against LOINC 2.83*
  - **Component**: `Glucose`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Enzymatic spectrophotometry
- **Category**: `DIABETES_PROFILE`
- **What it Measures**: Circulating plasma glucose concentration drawn at any time of day regardless of meal timing.
- **Clinical Relevance**: Used in acute triage. In a patient with classic symptoms of hyperglycemia (polyuria, polydipsia, unexplained weight loss) or hyperglycemic crisis, a value $\ge 200\text{ mg/dL}$ establishes a diagnosis of diabetes without requiring repeat testing. In asymptomatic individuals, isolated random elevations require formal confirmatory FPG or HbA1c testing.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 18.0182$)
- **Common Aliases**: `random blood glucose`, `random glucose`, `casual glucose`, `rbg`, `random blood sugar`
- **Applicable Patient Demographics**: Adults ($70\text{--}139\text{ mg/dL}$ represents an expected physiological finding in healthy postprandial individuals depending on meal timing and carbohydrate content, rather than a rigid universal reference interval).
- **Fasting Requirement**: No.
- **Reference Sources**: ADA Standards of Care in Diabetes (2026), MedlinePlus (2024). Diagnostic rule: $\ge 200\text{ mg/dL}$ in the presence of classic hyperglycemic symptoms confirms diabetes without repeat testing; asymptomatic individuals require formal confirmatory FPG or HbA1c testing.
- **Verification Status**: **VERIFIED**

---

### 15. `hba1c`
- **Canonical Name**: Hemoglobin A1c (Glycated Hemoglobin)
- **LOINC Identifier**: `4548-4` — *VERIFIED against LOINC 2.83*
  - **Component**: `Hemoglobin A1c/Hemoglobin.total`
  - **Property**: `MFr` (Mass fraction)
  - **System/Specimen**: `Bld` (Whole blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: HPLC, immunoassay, or capillary electrophoresis NGSP-certified
- **Category**: `DIABETES_PROFILE`
- **What it Measures**: Percentage of circulating hemoglobin molecules with glucose non-enzymatically glycated at the N-terminal valine of the beta chain, reflecting average blood glucose over the preceding 60 to 90 days.
- **Clinical Relevance**: Gold standard for longitudinal glycemic monitoring and diagnosis per ADA (2026). Diagnostic criteria: Normal ($< 5.7\%$), Prediabetes ($5.7\%\text{--}6.4\%$), Diabetes Mellitus ($\ge 6.5\%$). Must be repeated for confirmation in asymptomatic patients. Invalid in conditions altering erythrocyte turnover (hemolysis, hemodialysis, 2nd/3rd trimester pregnancy).
- **Standard Unit**: `%` (NGSP)
- **Supported Alternative Units**:
  - `mmol/mol` (IFCC units; $\text{NGSP \%} = (0.09148 \times \text{IFCC}) + 2.152$)
- **Common Aliases**: `hba1c`, `glycated hemoglobin`, `glycohemoglobin`, `a1c`, `hemoglobin a1c`
- **Applicable Patient Demographics**: Adults.
- **Fasting Requirement**: No.
- **Reference Sources**: ADA Standards of Care in Diabetes (2026), NGSP Harmonization Standards.
- **Verification Status**: **VERIFIED**

---

## Kidney Function Test (KFT / Renal Panel)

### 16. `creatinine`
- **Canonical Name**: Serum Creatinine
- **LOINC Identifier**: `2160-0` — *VERIFIED against LOINC 2.83*
  - **Component**: `Creatinine`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: IDMS-traceable enzymatic or Jaffe reaction
- **Category**: `KFT`
- **What it Measures**: Steady-state muscle creatine breakdown product cleared exclusively via glomerular filtration.
- **Clinical Relevance**: Primary renal filtration indicator and core input into eGFR equations. An increase of $\ge 0.3\text{ mg/dL}$ within 48 hours or $\ge 1.5\times$ baseline defines Acute Kidney Injury (KDIGO Stage 1).
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `umol/L` ($\text{mg/dL} = \mu\text{mol/L} \times 0.01131$)
- **Common Aliases**: `serum creatinine`, `creatinine`, `creat`, `s.creatinine`
- **Applicable Patient Demographics**: Sex-stratified due to muscle mass variance (Male: 0.7–1.3 mg/dL; Female: 0.6–1.1 mg/dL).
- **Fasting Requirement**: No (avoid cooked red meat binges immediately prior to testing).
- **Reference Sources**: KDIGO AKI Guidelines (2012), MedlinePlus (2024).
- **Verification Status**: **VERIFIED**

---

### 17. `urea`
- **Canonical Name**: Blood Urea (Serum Urea)
- **LOINC Identifier**: `22703-3` — *VERIFIED against LOINC 2.83*
  - **Component**: `Urea`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Enzymatic (Urease)
- **Category**: `KFT`
- **What it Measures**: Total mass concentration of circulating urea molecules ($\text{CO(NH}_2)_2$) in blood.
- **Clinical Relevance**: Primary nitrogenous end-product of hepatic protein catabolism excreted by kidneys. Rises in renal impairment, volume depletion, upper GI bleeding, and catabolic states.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 6.006$)
- **Common Aliases**: `blood urea`, `serum urea`, `urea`
- **Applicable Patient Demographics**: Adults (15.0–40.0 mg/dL).
- **Fasting Requirement**: No.
- **Reference Sources**: Tietz Clinical Guide to Laboratory Tests (4th Ed.), IFCC Standards.
- **Verification Status**: **VERIFIED**

---

### 18. `bun`
- **Canonical Name**: Blood Urea Nitrogen
- **LOINC Identifier**: `3094-0` — *VERIFIED against LOINC 2.83*
  - **Component**: `Urea nitrogen`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Enzymatic urease rate
- **Category**: `KFT`
- **What it Measures**: Mass concentration of nitrogen within circulating urea molecules.
- **Clinical Relevance**: Standard renal screening metric in North America. Used in calculating the BUN:Creatinine ratio ($> 20:1$). Critical clinical nuance: A BUN:Creatinine ratio $> 20:1$ is an indirect clinical clue for prerenal hypoperfusion or volume depletion, NOT an autonomous or definitive diagnosis of dehydration. Non-renal etiologies (gastrointestinal bleeding, high-dose corticosteroids, high dietary protein catabolism, low muscle mass) frequently elevate this ratio.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `mmol/L` ($\text{mg/dL} = \text{mmol/L} \times 2.80$)
- **Common Aliases**: `bun`, `blood urea nitrogen`, `urea nitrogen`, `serum bun`
- **Applicable Patient Demographics**: Adults (7.0–20.0 mg/dL).
- **Fasting Requirement**: No.
- **Reference Sources**: MedlinePlus (2024), Tietz (6th Ed.).
- **Verification Status**: **VERIFIED**

---

### 19. `egfr`
- **Canonical Name**: Estimated Glomerular Filtration Rate
- **LOINC Identifier**: `33914-3` — *VERIFIED against LOINC 2.83*
  - **Component**: `Glomerular filtration rate/1.73 sq M.predicted`
  - **Property**: `ArVolRate` (Area-normalized volume rate)
  - **System/Specimen**: `Ser/Plas/Bld` (Serum, Plasma, or Whole Blood)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Calculated by Creatinine-based formula (2021 CKD-EPI without race)
- **Category**: `KFT`
- **What it Measures**: Calculated biological filtration clearance of functional renal nephrons normalized to a standard body surface area ($1.73\text{ m}^2$).
- **Equation & Methodology**: Calculated using the 2021 CKD-EPI Creatinine equation (Inker et al., NEJM 2021; endorsed by KDIGO 2024 and NKF/ASN Task Force):
  $$\text{eGFR}_{\text{cr}} = 142 \times \min(S_{\text{cr}}/\kappa, 1)^\alpha \times \max(S_{\text{cr}}/\kappa, 1)^{-1.200} \times 0.9938^{\text{Age}} \times [1.012 \text{ if female}]$$
  where $\kappa = 0.7$ (female) or $0.9$ (male), $\alpha = -0.241$ (female) or $-0.302$ (male).
- **Required Inputs**: Serum Creatinine (IDMS-traceable, mg/dL), Age (years), and Biological Sex.
- **Longitudinal Measurement Requirement**: KDIGO guidelines mandate that chronicity ($> 3\text{ months}$) be documented before an eGFR $< 60\text{ mL/min/1.73m}^2$ confirms a diagnosis of Chronic Kidney Disease (CKD). **A single abnormal eGFR must NEVER trigger an autonomous diagnosis of CKD.**
- **Clinical Limitations**: Unreliable in extremes of muscle mass (amputees, bodybuilders, severe cachexia), acute hemodynamic instability, and pregnancy.
- **Standard Unit**: `mL/min/1.73m^2`
- **Supported Alternative Units**:
  - `mL/min` (unindexed)
- **Common Aliases**: `egfr`, `estimated gfr`, `glomerular filtration rate`, `gfr`
- **Applicable Patient Demographics**: Healthy young adults aged 18-39 ($90\text{--}130\text{ mL/min/1.73m}^2$ baseline benchmark). Critical distinction: eGFR physiologically declines with normal aging at $\sim 0.75\text{--}1.0\text{ mL/min/1.73m}^2\text{/year}$ after age 40. In healthy adults $\ge 65$, an eGFR of 60-89 mL/min/1.73m² is an expected age-related physiological finding and does not constitute CKD without markers of structural damage (albuminuria).
- **Fasting Requirement**: No (derived mathematically).
- **Reference Sources**: KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease.
- **Verification Status**: **VERIFIED**

---

### 20. `uric_acid`
- **Canonical Name**: Serum Uric Acid
- **LOINC Identifier**: `3084-1` — *VERIFIED against LOINC 2.83*
  - **Component**: `Urate`
  - **Property**: `MCnc` (Mass concentration)
  - **System/Specimen**: `Ser/Plas` (Serum or Plasma)
  - **Scale**: `Qn` (Quantitative)
  - **Method**: Enzymatic (Uricase) / Spectrophotometry
- **Category**: `KFT`
- **What it Measures**: Mass concentration of circulating monosodium urate derived from purine breakdown.
- **Clinical Relevance**: Values $> 6.8\text{ mg/dL}$ exceed physiological solubility in plasma at $37^\circ\text{C}$, permitting crystal precipitation. Crucial clinical guideline rule: Asymptomatic hyperuricemia does NOT establish a diagnosis of clinical gout and guidelines advise against automated urate-lowering pharmacotherapy in asymptomatic patients. Therapeutic target during active gout treatment is $< 6.0\text{ mg/dL}$.
- **Standard Unit**: `mg/dL`
- **Supported Alternative Units**:
  - `umol/L` ($\text{mg/dL} = \mu\text{mol/L} \times 0.01681$)
- **Common Aliases**: `uric acid`, `serum uric acid`, `urate`
- **Applicable Patient Demographics**: Sex-stratified (Male: 3.4–7.0 mg/dL; Female: 2.4–6.0 mg/dL).
- **Fasting Requirement**: No.
- **Reference Sources**: American College of Rheumatology (ACR) Gout Guidelines (2020), MedlinePlus (2024).
- **Verification Status**: **VERIFIED**

---
*End of Corrected Canonical Biomarker Dictionary.*
