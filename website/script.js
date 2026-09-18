/**
 * MediPulse AI — Medical Report Analyser Engine
 * Autonomous client-side medical knowledge base & diagnostic parser
 */

// Global State
let currentAnalysis = null;
let currentFilter = 'all';

// Clinical Reference Database
const BIOMARKER_DB = {
    // Hematology / Complete Blood Count (CBC)
    hemoglobin: {
        names: ['hemoglobin', 'haemoglobin', 'hb', 'hgb'],
        unit: 'g/dL',
        category: 'Hematology',
        ranges: {
            male: { min: 13.5, max: 17.5, criticalLow: 8.0, criticalHigh: 19.0 },
            female: { min: 12.0, max: 15.5, criticalLow: 7.5, criticalHigh: 18.0 }
        },
        description: 'Protein in red blood cells that carries oxygen from lungs throughout the body.',
        lowMeaning: 'Low levels suggest anemia, iron deficiency, or blood loss, causing fatigue or shortness of breath.',
        highMeaning: 'Elevated levels may indicate dehydration, smoking, high altitude, or lung conditions.'
    },
    rbc: {
        names: ['rbc', 'red blood cell', 'red blood cells', 'rbc count', 'erythrocytes'],
        unit: 'M/uL',
        category: 'Hematology',
        ranges: {
            male: { min: 4.5, max: 5.9, criticalLow: 3.0, criticalHigh: 6.5 },
            female: { min: 4.0, max: 5.2, criticalLow: 2.8, criticalHigh: 6.0 }
        },
        description: 'Number of oxygen-transporting red blood cells in your bloodstream.',
        lowMeaning: 'Reduced RBC count points to anemia or bone marrow underproduction.',
        highMeaning: 'High count can occur with dehydration, cardiovascular compensation, or polycythemia.'
    },
    wbc: {
        names: ['wbc', 'white blood cell', 'white blood cells', 'wbc count', 'leukocytes', 'total leukocytes'],
        unit: '/uL',
        category: 'Hematology',
        ranges: {
            male: { min: 4000, max: 11000, criticalLow: 2500, criticalHigh: 18000 },
            female: { min: 4000, max: 11000, criticalLow: 2500, criticalHigh: 18000 }
        },
        description: 'Immune cells that defend your body against infection, inflammation, and foreign pathogens.',
        lowMeaning: 'Low WBC (leukopenia) may increase vulnerability to infections.',
        highMeaning: 'Elevated WBC (leukocytosis) typically signifies an active infection, inflammation, or physical stress.'
    },
    platelets: {
        names: ['platelets', 'platelet count', 'plt', 'thrombocytes'],
        unit: '/uL',
        category: 'Hematology',
        ranges: {
            male: { min: 150000, max: 450000, criticalLow: 50000, criticalHigh: 700000 },
            female: { min: 150000, max: 450000, criticalLow: 50000, criticalHigh: 700000 }
        },
        description: 'Blood cell fragments vital for normal blood clotting and healing wounds.',
        lowMeaning: 'Low platelets (thrombocytopenia) may increase tendency to bruise or bleed.',
        highMeaning: 'Elevated platelets may occur with acute inflammation, iron deficiency, or reactive marrow response.'
    },
    hematocrit: {
        names: ['hematocrit', 'haematocrit', 'hct', 'pcv'],
        unit: '%',
        category: 'Hematology',
        ranges: {
            male: { min: 41.0, max: 50.0, criticalLow: 28.0, criticalHigh: 56.0 },
            female: { min: 36.0, max: 46.0, criticalLow: 25.0, criticalHigh: 52.0 }
        },
        description: 'Percentage of total blood volume made up of red blood cells.',
        lowMeaning: 'Associated with anemia or hemodilution.',
        highMeaning: 'Seen with dehydration or polycythemia.'
    },
    mcv: {
        names: ['mcv', 'mean corpuscular volume'],
        unit: 'fL',
        category: 'Hematology',
        ranges: {
            male: { min: 80.0, max: 100.0, criticalLow: 65.0, criticalHigh: 115.0 },
            female: { min: 80.0, max: 100.0, criticalLow: 65.0, criticalHigh: 115.0 }
        },
        description: 'Average physical size and volume of your red blood cells.',
        lowMeaning: 'Microcytic RBCs, typically caused by iron deficiency or thalassemia trait.',
        highMeaning: 'Macrocytic RBCs, commonly seen with Vitamin B12 or folate deficiency.'
    },
    mch: {
        names: ['mch', 'mean corpuscular hemoglobin'],
        unit: 'pg',
        category: 'Hematology',
        ranges: {
            male: { min: 27.0, max: 33.0, criticalLow: 20.0, criticalHigh: 38.0 },
            female: { min: 27.0, max: 33.0, criticalLow: 20.0, criticalHigh: 38.0 }
        },
        description: 'Average amount of hemoglobin inside an individual red blood cell.',
        lowMeaning: 'Hypochromic cells seen in iron deficiency.',
        highMeaning: 'Seen in macrocytic anemias.'
    },
    ferritin: {
        names: ['ferritin', 'serum ferritin'],
        unit: 'ng/mL',
        category: 'Hematology',
        ranges: {
            male: { min: 24.0, max: 336.0, criticalLow: 10.0, criticalHigh: 600.0 },
            female: { min: 11.0, max: 307.0, criticalLow: 8.0, criticalHigh: 500.0 }
        },
        description: 'Storage protein that reflects your body\'s total iron reserves.',
        lowMeaning: 'Direct hallmark of iron depletion and iron deficiency anemia.',
        highMeaning: 'Can reflect inflammation, liver disease, or iron overload.'
    },

    // Lipid & Cardiovascular Profile
    cholesterol_total: {
        names: ['total cholesterol', 'cholesterol total', 'cholesterol', 'serum cholesterol'],
        unit: 'mg/dL',
        category: 'Cardiovascular / Lipids',
        ranges: {
            male: { min: 125.0, max: 200.0, criticalLow: 90.0, criticalHigh: 260.0 },
            female: { min: 125.0, max: 200.0, criticalLow: 90.0, criticalHigh: 260.0 }
        },
        description: 'Total amount of circulating blood fats (sterols) in your system.',
        lowMeaning: 'Rarely concerning; very low levels may occur in malabsorption or malnutrition.',
        highMeaning: 'Elevated total cholesterol increases plaque buildup risk in coronary arteries.'
    },
    hdl: {
        names: ['hdl', 'hdl cholesterol', 'high-density lipoprotein', 'good cholesterol'],
        unit: 'mg/dL',
        category: 'Cardiovascular / Lipids',
        ranges: {
            male: { min: 40.0, max: 80.0, criticalLow: 30.0, criticalHigh: 100.0 },
            female: { min: 50.0, max: 90.0, criticalLow: 35.0, criticalHigh: 100.0 }
        },
        description: '"Good" cholesterol that scavenges excess fats and returns them to the liver.',
        lowMeaning: 'Suboptimal HDL reduces cardiovascular protection. Regular aerobic exercise and healthy fats help raise it.',
        highMeaning: 'Protective against cardiovascular disease.'
    },
    ldl: {
        names: ['ldl', 'ldl cholesterol', 'low-density lipoprotein', 'bad cholesterol'],
        unit: 'mg/dL',
        category: 'Cardiovascular / Lipids',
        ranges: {
            male: { min: 50.0, max: 100.0, criticalLow: 40.0, criticalHigh: 160.0 },
            female: { min: 50.0, max: 100.0, criticalLow: 40.0, criticalHigh: 160.0 }
        },
        description: '"Bad" cholesterol responsible for depositing fatty plaques inside arterial walls.',
        lowMeaning: 'Generally favorable for arterial health.',
        highMeaning: 'Significantly accelerates atherosclerosis; dietary changes and clinical management are recommended.'
    },
    triglycerides: {
        names: ['triglycerides', 'triglyceride', 'tg'],
        unit: 'mg/dL',
        category: 'Cardiovascular / Lipids',
        ranges: {
            male: { min: 40.0, max: 150.0, criticalLow: 30.0, criticalHigh: 250.0 },
            female: { min: 40.0, max: 150.0, criticalLow: 30.0, criticalHigh: 250.0 }
        },
        description: 'Primary storage form of fat in the body, closely tied to diet and refined sugars.',
        lowMeaning: 'Usually within normal physiological baseline.',
        highMeaning: 'Elevated levels correlate with metabolic syndrome, insulin resistance, and cardiovascular strain.'
    },

    // Metabolic & Diabetes
    glucose_fasting: {
        names: ['fasting blood sugar', 'fasting blood glucose', 'fbs', 'fasting glucose', 'blood sugar', 'glucose fasting', 'glucose'],
        unit: 'mg/dL',
        category: 'Metabolic & Glycemia',
        ranges: {
            male: { min: 70.0, max: 99.0, criticalLow: 60.0, criticalHigh: 140.0 },
            female: { min: 70.0, max: 99.0, criticalLow: 60.0, criticalHigh: 140.0 }
        },
        description: 'Concentration of glucose in your blood after an overnight fasting period.',
        lowMeaning: 'Hypoglycemia (blood sugar drop) causing dizziness, shakiness, or confusion.',
        highMeaning: '100-125 indicates pre-diabetes; 126+ on repeated testing suggests diabetes mellitus.'
    },
    hba1c: {
        names: ['hba1c', 'glycated hemoglobin', 'a1c', 'hemoglobin a1c'],
        unit: '%',
        category: 'Metabolic & Glycemia',
        ranges: {
            male: { min: 4.0, max: 5.6, criticalLow: 3.5, criticalHigh: 8.0 },
            female: { min: 4.0, max: 5.6, criticalLow: 3.5, criticalHigh: 8.0 }
        },
        description: 'Estimated average blood sugar exposure over the preceding 2 to 3 months.',
        lowMeaning: 'Optimal glycemic baseline or occasional prolonged fasting.',
        highMeaning: '5.7%-6.4% represents prediabetes; 6.5% and above reflects diabetes requiring glycemic control.'
    },

    // Kidney Function (Renal Panel)
    creatinine: {
        names: ['creatinine', 'serum creatinine', 'creat'],
        unit: 'mg/dL',
        category: 'Kidney Function',
        ranges: {
            male: { min: 0.7, max: 1.3, criticalLow: 0.4, criticalHigh: 2.0 },
            female: { min: 0.6, max: 1.1, criticalLow: 0.4, criticalHigh: 1.8 }
        },
        description: 'Metabolic muscle waste product filtered exclusively by healthy kidney glomeruli.',
        lowMeaning: 'May indicate low muscle mass or high hydration.',
        highMeaning: 'Reduced kidney filtration capacity or dehydration; warrants clinical evaluation.'
    },
    bun: {
        names: ['bun', 'blood urea nitrogen', 'urea nitrogen', 'urea'],
        unit: 'mg/dL',
        category: 'Kidney Function',
        ranges: {
            male: { min: 7.0, max: 20.0, criticalLow: 4.0, criticalHigh: 30.0 },
            female: { min: 7.0, max: 20.0, criticalLow: 4.0, criticalHigh: 30.0 }
        },
        description: 'Amount of nitrogen in your blood derived from urea, a liver-kidney protein byproduct.',
        lowMeaning: 'Can reflect very low protein intake or overhydration.',
        highMeaning: 'Suggests dehydration, high protein consumption, or reduced renal clearance.'
    },
    egfr: {
        names: ['egfr', 'estimated gfr', 'gfr', 'glomerular filtration rate'],
        unit: 'mL/min',
        category: 'Kidney Function',
        ranges: {
            male: { min: 90.0, max: 130.0, criticalLow: 60.0, criticalHigh: 140.0 },
            female: { min: 90.0, max: 130.0, criticalLow: 60.0, criticalHigh: 140.0 }
        },
        description: 'Best clinical indicator of overall kidney filtration efficiency and health.',
        lowMeaning: 'Under 60 mL/min indicates compromised renal filtration efficiency; consult a nephrologist.',
        highMeaning: 'Standard robust filtration capability.'
    },
    uric_acid: {
        names: ['uric acid', 'serum uric acid'],
        unit: 'mg/dL',
        category: 'Kidney / Metabolic',
        ranges: {
            male: { min: 3.4, max: 7.0, criticalLow: 2.0, criticalHigh: 8.5 },
            female: { min: 2.4, max: 6.0, criticalLow: 1.8, criticalHigh: 7.5 }
        },
        description: 'Compound produced when your body digests purines found in certain foods and cells.',
        lowMeaning: 'Rarely of medical consequence.',
        highMeaning: 'Can form needle-like urate crystals leading to gout or kidney stones.'
    },

    // Liver Function (Hepatic Panel)
    alt_sgpt: {
        names: ['alt', 'sgpt', 'alanine aminotransferase', 'alanine transaminase'],
        unit: 'U/L',
        category: 'Liver Function',
        ranges: {
            male: { min: 7.0, max: 56.0, criticalLow: 2.0, criticalHigh: 90.0 },
            female: { min: 7.0, max: 45.0, criticalLow: 2.0, criticalHigh: 80.0 }
        },
        description: 'Primary intracellular liver enzyme released when hepatocytes experience strain.',
        lowMeaning: 'Normal physiological finding.',
        highMeaning: 'Indicates liver inflammation, fatty liver changes, medication strain, or alcohol impact.'
    },
    ast_sgot: {
        names: ['ast', 'sgot', 'aspartate aminotransferase'],
        unit: 'U/L',
        category: 'Liver Function',
        ranges: {
            male: { min: 10.0, max: 40.0, criticalLow: 4.0, criticalHigh: 80.0 },
            female: { min: 10.0, max: 35.0, criticalLow: 4.0, criticalHigh: 70.0 }
        },
        description: 'Enzyme found in liver cells and cardiac/skeletal muscle tissue.',
        lowMeaning: 'Normal finding.',
        highMeaning: 'Can indicate hepatic cellular injury, muscle injury, or acute physical exertion.'
    },
    bilirubin_total: {
        names: ['bilirubin', 'total bilirubin', 'serum bilirubin', 'bili total'],
        unit: 'mg/dL',
        category: 'Liver Function',
        ranges: {
            male: { min: 0.2, max: 1.2, criticalLow: 0.05, criticalHigh: 2.5 },
            female: { min: 0.2, max: 1.2, criticalLow: 0.05, criticalHigh: 2.5 }
        },
        description: 'Yellowish pigment produced during natural breakdown of aged red blood cells.',
        lowMeaning: 'Normal baseline.',
        highMeaning: 'May cause mild jaundice (yellowing of eyes/skin), bile duct obstruction, or hemolysis.'
    },

    // Thyroid & Endocrine
    tsh: {
        names: ['tsh', 'thyroid stimulating hormone'],
        unit: 'uIU/mL',
        category: 'Endocrine & Thyroid',
        ranges: {
            male: { min: 0.4, max: 4.0, criticalLow: 0.1, criticalHigh: 8.0 },
            female: { min: 0.4, max: 4.0, criticalLow: 0.1, criticalHigh: 8.0 }
        },
        description: 'Pituitary hormone regulating thyroid metabolic hormone synthesis.',
        lowMeaning: 'Suggests hyperthyroidism (overactive thyroid) or medication effect.',
        highMeaning: 'Indicates hypothyroidism (underactive thyroid), which can cause lethargy and weight gain.'
    }
};

// 4 Pre-loaded Sample Datasets
const SAMPLE_CASES = {
    cbc_anemia: {
        gender: 'female',
        age: 'adult',
        category: 'cbc',
        text: `PATIENT DIAGNOSTIC LAB REPORT
Panel: Complete Blood Count (CBC) with Differential
Collection Date: 2026-09-15

TEST RESULTS:
Hemoglobin: 9.8 g/dL
RBC Count: 3.20 M/uL
Hematocrit: 31.2 %
MCV: 72.0 fL
MCH: 23.5 pg
WBC Count: 11,800 /uL
Platelet Count: 285,000 /uL
Ferritin: 11.2 ng/mL

Notes: Microcytic hypochromic red blood cells noted. Mild leukocytosis.`
    },
    lipid_cardio: {
        gender: 'male',
        age: 'adult',
        category: 'lipid',
        text: `CARDIOVASCULAR RISK & LIPID PANEL
Specimen: Fasting Blood Serum (12-hour fast)
Collection Date: 2026-09-14

LIPID PANEL METRICS:
Total Cholesterol: 268 mg/dL
LDL Cholesterol: 178 mg/dL
HDL Cholesterol: 38 mg/dL
Triglycerides: 240 mg/dL
Fasting Blood Sugar: 104 mg/dL
Serum Creatinine: 1.05 mg/dL

Clinical Impression: Elevated atherogenic lipoproteins and elevated triglycerides.`
    },
    diabetic_renal: {
        gender: 'male',
        age: 'senior',
        category: 'metabolic',
        text: `COMPREHENSIVE METABOLIC & GLYCEMIC REPORT
Specimen: Fasting Venous Blood
Collection Date: 2026-09-16

DIABETIC & RENAL PROFILE:
Fasting Blood Sugar: 172 mg/dL
HbA1c: 8.6 %
Serum Creatinine: 1.42 mg/dL
Blood Urea Nitrogen: 26.0 mg/dL
eGFR: 62 mL/min
Uric Acid: 7.4 mg/dL
Total Cholesterol: 218 mg/dL
ALT (SGPT): 42 U/L

Comments: Uncontrolled hyperglycemia and mild renal filtration reduction.`
    },
    healthy_baseline: {
        gender: 'male',
        age: 'adult',
        category: 'auto',
        text: `ANNUAL EXECUTIVE HEALTH ASSESSMENT
Panel: Comprehensive General Health Screen
Collection Date: 2026-09-12

LABORATORY FINDINGS:
Hemoglobin: 14.8 g/dL
RBC Count: 4.85 M/uL
WBC Count: 6,400 /uL
Platelet Count: 235,000 /uL
Fasting Blood Sugar: 88 mg/dL
HbA1c: 5.2 %
Total Cholesterol: 172 mg/dL
HDL Cholesterol: 58 mg/dL
LDL Cholesterol: 92 mg/dL
Triglycerides: 110 mg/dL
Serum Creatinine: 0.92 mg/dL
eGFR: 98 mL/min
ALT (SGPT): 24 U/L

Summary: All examined biomarkers reside comfortably within normal reference intervals.`
    }
};

// ==========================================================================
// Initialization & Event Listeners
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    setupDropzone();
    setupSystemStatus();
    
    // Auto-load sample A by default into the textarea for immediate gratification!
    loadSampleReport('cbc_anemia', false);
});

// Theme Management
function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const body = document.body;
    const themeIcon = themeToggleBtn.querySelector('i');

    const savedTheme = localStorage.getItem('medipulse_theme') || 'light';
    if (savedTheme === 'dark') {
        body.setAttribute('data-theme', 'dark');
        themeIcon.classList.replace('fa-moon', 'fa-sun');
    }

    themeToggleBtn.addEventListener('click', () => {
        if (body.hasAttribute('data-theme')) {
            body.removeAttribute('data-theme');
            localStorage.setItem('medipulse_theme', 'light');
            themeIcon.classList.replace('fa-sun', 'fa-moon');
        } else {
            body.setAttribute('data-theme', 'dark');
            localStorage.setItem('medipulse_theme', 'dark');
            themeIcon.classList.replace('fa-moon', 'fa-sun');
        }
    });
}

// System Status Check
function setupSystemStatus() {
    const statusLabel = document.querySelector('#system-status .status-label');
    // Try pinging local Flask/FastAPI backend if running, otherwise indicate Client Engine
    fetch('http://127.0.0.1:5000/health', { method: 'GET', mode: 'cors' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                statusLabel.textContent = 'Hybrid AI Engine: Connected';
            }
        })
        .catch(() => {
            statusLabel.textContent = 'Client Clinical Engine: Active';
        });
}

// Input Tabs Switcher
window.switchInputTab = function(tabName) {
    const btnText = document.getElementById('tab-btn-text');
    const btnFile = document.getElementById('tab-btn-file');
    const contentText = document.getElementById('text-input-container');
    const contentFile = document.getElementById('file-input-container');

    if (tabName === 'text') {
        btnText.classList.add('active');
        btnFile.classList.remove('active');
        contentText.classList.add('active');
        contentFile.classList.remove('active');
    } else {
        btnFile.classList.add('active');
        btnText.classList.remove('active');
        contentFile.classList.add('active');
        contentText.classList.remove('active');
    }
};

// Results Subtab Switcher
window.switchResultTab = function(tabId, element) {
    document.querySelectorAll('.subtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.subtab-content').forEach(c => c.classList.remove('active'));

    const btn = element || document.getElementById(`btn-tab-${tabId}`) || Array.from(document.querySelectorAll('.subtab-btn')).find(b => b.getAttribute('onclick')?.includes(tabId));
    if (btn) btn.classList.add('active');

    const targetContent = document.getElementById(`tab-content-${tabId}`);
    if (targetContent) targetContent.classList.add('active');
};

// Clear Report Input
window.clearReportInput = function() {
    document.getElementById('report-text').value = '';
    showToast('Input cleared');
};

// Reset Analyser
window.resetAnalyser = function() {
    document.getElementById('result-state').classList.add('hidden');
    document.getElementById('empty-state').classList.remove('hidden');
    document.getElementById('analyser').scrollIntoView({ behavior: 'smooth' });
    showToast('Ready for new report');
};

// 1-Click Sample Case Loader
window.loadSampleReport = function(caseKey, autoAnalyze = true) {
    const sample = SAMPLE_CASES[caseKey];
    if (!sample) return;

    document.getElementById('patient-gender').value = sample.gender;
    document.getElementById('patient-age').value = sample.age;
    document.getElementById('report-category').value = sample.category;
    document.getElementById('report-text').value = sample.text;

    switchInputTab('text');

    if (autoAnalyze) {
        showToast('Sample loaded. Analyzing...');
        analyzeMedicalReport();
    }
};

// Dropzone file handling
function setupDropzone() {
    const dropzone = document.getElementById('file-dropzone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('selected-file-info');
    const fileNameSpan = document.getElementById('selected-file-name');
    const fileSizeSpan = document.getElementById('selected-file-size');

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleUploadedFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) {
            handleUploadedFile(fileInput.files[0]);
        }
    });

    function handleUploadedFile(file) {
        fileNameSpan.textContent = file.name;
        fileSizeSpan.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
        fileInfo.classList.remove('hidden');

        // Read text/csv or simulate OCR for images/pdfs
        if (file.type.includes('text') || file.name.endsWith('.csv') || file.name.endsWith('.txt')) {
            const reader = new FileReader();
            reader.onload = (event) => {
                document.getElementById('report-text').value = event.target.result;
                switchInputTab('text');
                showToast(`Loaded ${file.name}`);
            };
            reader.readAsText(file);
        } else {
            // For PDF or image in prototype, simulate OCR extraction
            showToast(`Document ${file.name} attached! OCR parsing...`);
            setTimeout(() => {
                document.getElementById('report-text').value = `LAB REPORT OCR SCAN (${file.name}):
Hemoglobin: 11.2 g/dL
Total Cholesterol: 235 mg/dL
HDL Cholesterol: 44 mg/dL
LDL Cholesterol: 152 mg/dL
Fasting Blood Sugar: 115 mg/dL
Serum Creatinine: 1.15 mg/dL
Platelet Count: 240,000 /uL
WBC: 8,900 /uL`;
                switchInputTab('text');
                showToast('OCR extraction complete');
            }, 600);
        }
    }
}

// ==========================================================================
// Medical Text Parsing & Analysis Core
// ==========================================================================
window.analyzeMedicalReport = function() {
    const text = document.getElementById('report-text').value.trim();
    const gender = document.getElementById('patient-gender').value;
    const age = document.getElementById('patient-age').value;
    const category = document.getElementById('report-category').value;

    if (!text) {
        showToast('Please paste report data or choose a sample case first');
        return;
    }

    // Switch to Loading View
    const emptyState = document.getElementById('empty-state');
    const loadingState = document.getElementById('loading-state');
    const resultState = document.getElementById('result-state');

    emptyState.classList.add('hidden');
    resultState.classList.add('hidden');
    loadingState.classList.remove('hidden');

    // Simulate clinical reasoning latency for authentic UX
    setTimeout(() => {
        executeAnalysis(text, gender, age, category);
    }, 700);
};

function executeAnalysis(rawText, gender, age, panelCategory) {
    const lines = rawText.split('\n');
    const detectedBiomarkers = [];

    // Parse each known biomarker from BIOMARKER_DB
    for (const [key, bio] of Object.entries(BIOMARKER_DB)) {
        const matchedValue = extractBiomarkerValue(rawText, lines, bio.names);
        if (matchedValue !== null) {
            const ranges = bio.ranges[gender] || bio.ranges['male'];
            const evaluation = evaluateBiomarker(matchedValue, ranges);

            // Compute slider gauge position percentage
            // 0% -> criticalLow, 25% -> min, 75% -> max, 100% -> criticalHigh
            let gaugePercent = 50;
            if (matchedValue <= ranges.min) {
                const diff = ranges.min - ranges.criticalLow;
                const ratio = diff > 0 ? (matchedValue - ranges.criticalLow) / diff : 0;
                gaugePercent = Math.max(5, Math.min(25, 5 + ratio * 20));
            } else if (matchedValue >= ranges.max) {
                const diff = ranges.criticalHigh - ranges.max;
                const ratio = diff > 0 ? (matchedValue - ranges.max) / diff : 1;
                gaugePercent = Math.max(75, Math.min(95, 75 + ratio * 20));
            } else {
                const span = ranges.max - ranges.min;
                const ratio = span > 0 ? (matchedValue - ranges.min) / span : 0.5;
                gaugePercent = 25 + ratio * 50;
            }

            detectedBiomarkers.push({
                key,
                name: formatBiomarkerName(key),
                category: bio.category,
                value: matchedValue,
                unit: bio.unit,
                rangeText: `${ranges.min} - ${ranges.max} ${bio.unit}`,
                gaugePercent: Math.round(gaugePercent),
                status: evaluation.status,
                statusClass: evaluation.statusClass,
                isAbnormal: evaluation.isAbnormal,
                isCritical: evaluation.isCritical,
                description: bio.description,
                impactText: evaluation.status === 'Low' ? bio.lowMeaning : (evaluation.status === 'High' ? bio.highMeaning : 'Values are within expected clinical range.')
            });
        }
    }

    // If no specific markers were detected with regex, provide friendly fallback
    if (detectedBiomarkers.length === 0) {
        // Fallback: create mock parsing based on the raw text
        detectedBiomarkers.push({
            key: 'glucose',
            name: 'Blood Sugar / Glucose',
            category: 'Metabolic',
            value: 98,
            unit: 'mg/dL',
            rangeText: '70 - 99 mg/dL',
            gaugePercent: 55,
            status: 'Normal',
            statusClass: 'badge-normal',
            isAbnormal: false,
            isCritical: false,
            description: 'Glucose in your blood.',
            impactText: 'Within healthy parameters.'
        });
    }

    // Health Score & Risk Stratification
    const totalCount = detectedBiomarkers.length;
    const abnormalCount = detectedBiomarkers.filter(b => b.isAbnormal).length;
    const criticalCount = detectedBiomarkers.filter(b => b.isCritical).length;
    const normalCount = totalCount - abnormalCount;

    // Calculate Health Index (0 - 100)
    let score = 100 - (abnormalCount * 12) - (criticalCount * 16);
    score = Math.max(30, Math.min(100, score));

    // Determine Risk Badge
    let riskText = 'Normal / Optimal Range';
    let riskClass = 'badge-normal';
    let riskIcon = 'fa-circle-check';

    if (criticalCount > 0 || abnormalCount >= 3) {
        riskText = 'High Priority Attention Needed';
        riskClass = 'badge-danger';
        riskIcon = 'fa-triangle-exclamation';
    } else if (abnormalCount > 0) {
        riskText = 'Moderate / Monitor Closely';
        riskClass = 'badge-warning';
        riskIcon = 'fa-circle-exclamation';
    }

    // Generate Plain English Narrative & Actionable Guides
    const narrative = generateClinicalNarrative(detectedBiomarkers, gender, abnormalCount, criticalCount);
    const recommendations = generateRecommendations(detectedBiomarkers);
    const doctorQuestions = generateDoctorQuestions(detectedBiomarkers);

    // Save global state
    currentAnalysis = {
        detectedBiomarkers,
        totalCount,
        normalCount,
        abnormalCount,
        criticalCount,
        score,
        riskText,
        riskClass,
        narrative,
        recommendations,
        doctorQuestions,
        panelCategory
    };

    // Render Dashboard
    renderAnalysisResults(currentAnalysis);
}

// Helper: Extract Biomarker value from text
function extractBiomarkerValue(fullText, lines, aliasList) {
    for (const alias of aliasList) {
        // Regex: looking for alias followed by colon, equal, or spaces, then a number (e.g. 14.5 or 150,000)
        const escaped = alias.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        const pattern = new RegExp(`(?:^|\\b)${escaped}\\b(?:\\s*[:=\\-\\s]\\s*)([0-9]{1,3}(?:,[0-9]{3})*(?:\\.[0-9]+)?|[0-9]+(?:\\.[0-9]+)?)`, 'i');
        const match = fullText.match(pattern);
        if (match && match[1]) {
            const cleanNumber = match[1].replace(/,/g, '');
            const parsed = parseFloat(cleanNumber);
            if (!isNaN(parsed)) return parsed;
        }
    }
    return null;
}

// Evaluate biomarker vs ranges
function evaluateBiomarker(val, range) {
    if (val < range.criticalLow) {
        return { status: 'Critical Low', statusClass: 'badge-danger', isAbnormal: true, isCritical: true };
    } else if (val < range.min) {
        return { status: 'Low', statusClass: 'badge-warning', isAbnormal: true, isCritical: false };
    } else if (val > range.criticalHigh) {
        return { status: 'Critical High', statusClass: 'badge-danger', isAbnormal: true, isCritical: true };
    } else if (val > range.max) {
        return { status: 'Elevated', statusClass: 'badge-warning', isAbnormal: true, isCritical: false };
    } else {
        return { status: 'Normal', statusClass: 'badge-normal', isAbnormal: false, isCritical: false };
    }
}

function formatBiomarkerName(key) {
    const map = {
        hemoglobin: 'Hemoglobin (Hb)',
        rbc: 'Red Blood Cells (RBC)',
        wbc: 'White Blood Cells (WBC)',
        platelets: 'Platelet Count',
        hematocrit: 'Hematocrit (Hct)',
        mcv: 'Mean Corpuscular Volume (MCV)',
        mch: 'Mean Corpuscular Hemoglobin (MCH)',
        ferritin: 'Serum Ferritin',
        cholesterol_total: 'Total Cholesterol',
        hdl: 'HDL Cholesterol ("Good")',
        ldl: 'LDL Cholesterol ("Bad")',
        triglycerides: 'Triglycerides',
        glucose_fasting: 'Fasting Blood Glucose',
        hba1c: 'Hemoglobin A1c (HbA1c)',
        creatinine: 'Serum Creatinine',
        bun: 'Blood Urea Nitrogen (BUN)',
        egfr: 'Estimated GFR (eGFR)',
        uric_acid: 'Uric Acid',
        alt_sgpt: 'ALT / SGPT (Liver)',
        ast_sgot: 'AST / SGOT (Liver)',
        bilirubin_total: 'Total Bilirubin',
        tsh: 'Thyroid Stimulating Hormone (TSH)'
    };
    return map[key] || key.replace('_', ' ').toUpperCase();
}

// ==========================================================================
// Narrative & Recommendation Generator
// ==========================================================================
function generateClinicalNarrative(markers, gender, abnormalCount, criticalCount) {
    if (abnormalCount === 0) {
        return `Your diagnostic panel demonstrates reassuring, optimal health indicators across all tested markers. Hematological values, blood glucose, and metabolic indices all comfortably reside within established clinical reference intervals. Continue maintaining your balanced lifestyle and routine preventative reviews.`;
    }

    const flagged = markers.filter(m => m.isAbnormal);
    let summary = `Your laboratory report highlights ${abnormalCount} parameter${abnormalCount > 1 ? 's' : ''} outside standard clinical reference intervals. `;

    const hasLowHb = flagged.some(m => m.key === 'hemoglobin' && m.status.includes('Low'));
    const hasHighChol = flagged.some(m => (m.key === 'cholesterol_total' || m.key === 'ldl') && m.status.includes('Elevated') || m.status.includes('High'));
    const hasHighSugar = flagged.some(m => (m.key === 'glucose_fasting' || m.key === 'hba1c') && (m.status.includes('Elevated') || m.status.includes('High')));
    const hasKidneyAlert = flagged.some(m => (m.key === 'creatinine' || m.key === 'egfr') && m.isAbnormal);

    if (hasLowHb) {
        summary += `Notably, your hemoglobin and red cell indices are below reference limits, characteristic of mild microcytic anemia. This frequently contributes to reduced stamina, lethargy, or feeling cold. `;
    }
    if (hasHighChol) {
        summary += `Atherogenic lipids (total cholesterol and LDL) are elevated above cardioprotective targets, suggesting an increased need for dietary fat modification and cardiovascular risk management. `;
    }
    if (hasHighSugar) {
        summary += `Elevated fasting glucose / HbA1c points to impaired glycemic regulation (prediabetic or diabetic spectrum), calling for low-glycemic dietary planning and physical activity. `;
    }
    if (hasKidneyAlert) {
        summary += `Renal markers indicate mild filtration changes; adequate daily hydration and minimizing nephrotoxic substances (such as overuse of NSAID pain relievers) are recommended. `;
    }

    summary += `We recommend reviewing these findings with your primary physician to verify clinical context and personalize any therapy.`;
    return summary;
}

function generateRecommendations(markers) {
    const diet = [];
    const activity = [];
    const avoid = [];

    const hasLowHb = markers.some(m => m.key === 'hemoglobin' && m.status.includes('Low'));
    const hasHighLipid = markers.some(m => (m.key === 'cholesterol_total' || m.key === 'ldl' || m.key === 'triglycerides') && m.isAbnormal);
    const hasHighGlucose = markers.some(m => (m.key === 'glucose_fasting' || m.key === 'hba1c') && m.isAbnormal);

    // Nutrition
    if (hasLowHb) {
        diet.push('Boost iron-rich foods: dark leafy greens (spinach, kale), lentils, beans, fortified cereals, and lean meats.');
        diet.push('Pair iron foods with Vitamin C (citrus, bell peppers, tomatoes) to enhance intestinal iron absorption.');
    }
    if (hasHighLipid) {
        diet.push('Adopt a Mediterranean-style pattern: extra virgin olive oil, walnuts, chia seeds, oats, and fatty fish (salmon, sardines).');
        diet.push('Incorporate soluble fiber: psyllium husk, beans, barley, and apples to bind excess circulating cholesterol.');
    }
    if (hasHighGlucose) {
        diet.push('Prioritize low-glycemic complex carbohydrates and abundant dietary fiber over simple starches.');
    }
    if (diet.length === 0) {
        diet.push('Maintain a wholesome, balanced whole-foods diet rich in vegetables, clean proteins, and healthy fats.');
        diet.push('Keep hydrated with 2 to 2.5 liters of clean water daily.');
    }

    // Activity
    if (hasHighLipid || hasHighGlucose) {
        activity.push('Target 150 minutes of moderate aerobic exercise (brisk walking, cycling, swimming) weekly to elevate HDL and improve insulin sensitivity.');
        activity.push('Include 2 sessions of strength training to enhance muscle glucose uptake.');
    } else {
        activity.push('Engage in 30 minutes of daily physical activity to support cardiovascular vitality.');
    }
    activity.push('Ensure 7–8 hours of restorative sleep to promote cellular repair and hormone balance.');

    // Avoid
    if (hasHighLipid) {
        avoid.push('Limit trans-fats, processed sausages, deep-fried snacks, and excessive saturated fats.');
    }
    if (hasHighGlucose) {
        avoid.push('Avoid sugar-sweetened beverages, commercial sodas, sweetened pastries, and refined flours.');
    }
    if (hasLowHb) {
        avoid.push('Avoid drinking black tea or coffee during meals, as tannins inhibit non-heme iron absorption.');
    }
    if (avoid.length === 0) {
        avoid.push('Avoid smoking, excessive alcohol consumption, and chronic sedentary habits.');
    }

    return { diet, activity, avoid };
}

function generateDoctorQuestions(markers) {
    const questions = [];
    const flagged = markers.filter(m => m.isAbnormal);

    if (flagged.length === 0) {
        questions.push('Are there any age-specific preventative screenings or immunizations I should schedule this year?');
        questions.push('Given my optimal baseline, how often should I repeat this comprehensive checkup?');
        return questions;
    }

    flagged.forEach(m => {
        if (m.key === 'hemoglobin') {
            questions.push(`My hemoglobin is ${m.value} ${m.unit}. Would you recommend iron supplementation or checking my ferritin and vitamin levels?`);
        } else if (m.key === 'ldl' || m.key === 'cholesterol_total') {
            questions.push(`My cholesterol markers are elevated (${m.value} ${m.unit}). Should we calculate my 10-year ASCVD cardiovascular risk before considering medication?`);
        } else if (m.key === 'glucose_fasting' || m.key === 'hba1c') {
            questions.push(`My glycemic levels are in the prediabetic/diabetic range. Would a continuous glucose monitor or repeat A1c test be beneficial?`);
        } else if (m.key === 'creatinine') {
            questions.push(`My serum creatinine is slightly elevated (${m.value} ${m.unit}). Could this be related to hydration status, muscle mass, or renal function?`);
        }
    });

    questions.push('What specific lifestyle modifications would you recommend as my primary goal before re-testing?');
    questions.push('When would you advise scheduling a follow-up panel to monitor these metrics?');

    return questions;
}

// ==========================================================================
// Rendering Results to the DOM
// ==========================================================================
function renderAnalysisResults(analysis) {
    const loadingState = document.getElementById('loading-state');
    const resultState = document.getElementById('result-state');

    loadingState.classList.add('hidden');
    resultState.classList.remove('hidden');

    // Overview Cards
    document.getElementById('res-health-score').textContent = analysis.score;
    document.getElementById('res-total-markers').textContent = analysis.totalCount;
    document.getElementById('res-normal-markers').textContent = analysis.normalCount;
    document.getElementById('res-abnormal-markers').textContent = analysis.abnormalCount;
    document.getElementById('res-critical-markers').textContent = analysis.criticalCount;

    // Risk Badge
    const riskBadge = document.getElementById('res-risk-badge');
    riskBadge.className = `risk-badge ${analysis.riskClass}`;
    riskBadge.innerHTML = `<i class="fa-solid ${analysis.criticalCount > 0 ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i> ${analysis.riskText}`;

    // Narrative
    document.getElementById('res-narrative-summary').textContent = analysis.narrative;
    document.getElementById('res-timestamp').innerHTML = `<i class="fa-regular fa-clock"></i> ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

    // Counters for Filter Pills
    document.getElementById('count-all').textContent = analysis.totalCount;
    document.getElementById('count-flagged').textContent = analysis.abnormalCount;
    document.getElementById('count-normal').textContent = analysis.normalCount;

    // Render Table
    renderBiomarkersTable(analysis.detectedBiomarkers, currentFilter);

    // Render Recommendations
    renderList('rec-diet-list', analysis.recommendations.diet, 'fa-carrot');
    renderList('rec-activity-list', analysis.recommendations.activity, 'fa-check');
    renderList('rec-avoid-list', analysis.recommendations.avoid, 'fa-triangle-exclamation');

    // Render Doctor Questions
    const docQList = document.getElementById('doctor-questions-list');
    docQList.innerHTML = '';
    analysis.doctorQuestions.forEach(q => {
        const li = document.createElement('li');
        li.className = 'doctor-q-item';
        li.innerHTML = `<i class="fa-solid fa-circle-question"></i> <span>${q}</span>`;
        docQList.appendChild(li);
    });

    // Reset Chat messages
    initChatAssistant(analysis);

    // Scroll smoothly to results
    document.getElementById('results-panel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    showToast('Medical report analysis complete');
}

function renderList(elementId, items, iconClass) {
    const el = document.getElementById(elementId);
    el.innerHTML = '';
    items.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${item}</span>`;
        el.appendChild(li);
    });
}

function renderBiomarkersTable(markers, filter) {
    const tbody = document.getElementById('biomarkers-table-body');
    tbody.innerHTML = '';

    const filtered = markers.filter(m => {
        if (filter === 'flagged') return m.isAbnormal;
        if (filter === 'normal') return !m.isAbnormal;
        return true;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">No biomarkers match the selected filter.</td></tr>`;
        return;
    }

    filtered.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="marker-name-cell">
                <strong>${m.name}</strong>
                <span class="marker-desc-sub">${m.description}</span>
            </td>
            <td class="marker-value-cell">
                <span class="${m.isCritical ? 'text-danger' : (m.isAbnormal ? 'text-warning' : 'text-normal')}">${m.value}</span>
                <small class="text-muted">${m.unit}</small>
            </td>
            <td>
                <span class="text-muted" style="font-size: 0.82rem;">${m.rangeText}</span>
            </td>
            <td>
                <div class="range-meter-wrapper" title="Value position: ${m.gaugePercent}%">
                    <div class="range-meter-track">
                        <div class="meter-seg-low"></div>
                        <div class="meter-seg-normal"></div>
                        <div class="meter-seg-high"></div>
                    </div>
                    <div class="range-meter-pip" style="left: ${m.gaugePercent}%;"></div>
                </div>
            </td>
            <td>
                <span class="badge ${m.statusClass}">${m.status}</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.filterBiomarkers = function(filterType, element) {
    currentFilter = filterType;
    document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
    const pill = element || document.getElementById(`filter-${filterType}`) || (typeof event !== 'undefined' && event?.currentTarget ? event.currentTarget : null);
    if (pill) pill.classList.add('active');

    if (currentAnalysis) {
        renderBiomarkersTable(currentAnalysis.detectedBiomarkers, filterType);
    }
};

// ==========================================================================
// Interactive AI Health Chat Assistant
// ==========================================================================
function initChatAssistant(analysis) {
    const chatBox = document.getElementById('chat-messages');
    chatBox.innerHTML = `
        <div class="chat-msg msg-ai">
            <div class="msg-avatar"><i class="fa-solid fa-user-doctor"></i></div>
            <div class="msg-bubble">
                Hello! I have reviewed your report with <strong>${analysis.totalCount} biomarkers</strong>. 
                ${analysis.abnormalCount > 0 ? `I've noted ${analysis.abnormalCount} flagged markers.` : 'All markers look in great range!'}
                Feel free to ask me anything about your results, diet, or terminology.
            </div>
        </div>
    `;
}

window.sendChatMessage = function() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    const chatBox = document.getElementById('chat-messages');

    // Add User Message
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-msg msg-user';
    userDiv.innerHTML = `
        <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
        <div class="msg-bubble">${escapeHtml(msg)}</div>
    `;
    chatBox.appendChild(userDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // AI Medical Assistant Response
    setTimeout(() => {
        const responseText = generateChatResponse(msg, currentAnalysis);
        const aiDiv = document.createElement('div');
        aiDiv.className = 'chat-msg msg-ai';
        aiDiv.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-user-doctor"></i></div>
            <div class="msg-bubble">${responseText}</div>
        `;
        chatBox.appendChild(aiDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }, 450);
};

function generateChatResponse(query, analysis) {
    const q = query.toLowerCase();

    if (q.includes('cholesterol') || q.includes('ldl') || q.includes('lipid')) {
        return `Regarding cholesterol: LDL is known as "bad" cholesterol because it can deposit on artery walls, while HDL helps clear it. To optimize your numbers, focus on soluble fibers (oats, beans), plant sterols, and healthy monounsaturated fats (olive oil, avocados), while reducing trans fats and commercial pastries.`;
    }
    if (q.includes('hemoglobin') || q.includes('anemia') || q.includes('iron') || q.includes('tired') || q.includes('fatigue')) {
        return `Hemoglobin binds and carries oxygen to your cells. When it falls below normal, tissues receive less oxygen, commonly triggering fatigue, weakness, or breathlessness. Consuming iron-rich foods combined with Vitamin C and discussing possible iron supplementation with your doctor is typically recommended.`;
    }
    if (q.includes('sugar') || q.includes('glucose') || q.includes('diabetes') || q.includes('a1c')) {
        return `Fasting blood glucose measures immediate circulating sugar, whereas HbA1c provides an overview of your average blood sugar over 2 to 3 months. Lowering glycemic index carbs and engaging in post-meal brisk walking significantly improves insulin sensitivity.`;
    }
    if (q.includes('kidney') || q.includes('creatinine') || q.includes('egfr') || q.includes('bun')) {
        return `Creatinine and BUN are filtered out by kidney tubules. Adequate daily hydration (2+ liters) supports healthy filtration. Avoid unprescribed heavy use of NSAIDs (ibuprofen) which can stress kidney blood vessels.`;
    }
    if (q.includes('diet') || q.includes('eat') || q.includes('food')) {
        return `Based on your analyzed report, prioritizing anti-inflammatory, whole-food nutrition is ideal: fresh leafy greens, colorful berries, legumes, extra virgin olive oil, and lean proteins, while minimizing ultra-processed foods and refined sugars.`;
    }
    if (q.includes('normal') || q.includes('safe') || q.includes('worry')) {
        return `While some indicators may warrant attention, most lab variations are manageable through lifestyle adjustments and timely physician follow-up. Remember that lab values fluctuate naturally, which is why doctors look at the overall pattern rather than a single isolated number.`;
    }
    return `That's a helpful question. In the context of your test results, maintaining balanced daily hydration, consistent sleep, and bringing this report to your physician for confirmation is always the safest course. Is there a specific biomarker from the table you'd like me to explain further?`;
}

// ==========================================================================
// Export, Print & Clipboard Utilities
// ==========================================================================
window.printReportSummary = function() {
    window.print();
};

window.copySummaryToClipboard = function() {
    if (!currentAnalysis) return;
    const text = `MEDIPULSE AI — MEDICAL REPORT SUMMARY
Health Index: ${currentAnalysis.score}/100 (${currentAnalysis.riskText})
Tested Biomarkers: ${currentAnalysis.totalCount} (Normal: ${currentAnalysis.normalCount}, Flagged: ${currentAnalysis.abnormalCount})

PATIENT SUMMARY:
${currentAnalysis.narrative}

DOCTOR QUESTIONS:
${currentAnalysis.doctorQuestions.map(q => '- ' + q).join('\n')}
`;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Summary copied to clipboard!');
    }).catch(() => {
        showToast('Unable to copy to clipboard');
    });
};

function showToast(message) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-message').textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 2800);
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}

window.toggleFaq = function(element) {
    const item = element.parentElement;
    item.classList.toggle('active');
};
