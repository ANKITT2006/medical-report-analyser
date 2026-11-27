# MEDIPULSE AI — STEP 3.4.3 DEPENDENCY INSTALLATION REPORT
## RAPIDOCR & ONNX RUNTIME DEPENDENCY INSTALLATION

**Date**: 2026-11-27  
**Project**: MediPulse AI — Medical Report Analyzer  
**Project Root**: `C:\Users\Ankit's_YOGA\Desktop\report_analyser\medical-report-analyser\`  
**Phase**: Phase 3 — Data Ingestion & Unit Normalization Pipeline  
**Subphase**: 3.4.3 — `rapidocr` & `onnxruntime` Dependency Installation & Verification  

---

## 1. ENVIRONMENT & PREFLIGHT INSPECTION

- **Active Python Interpreter**: `C:\Users\Ankit's_YOGA\AppData\Local\Programs\Python\Python313\python.exe` (`3.13.7`, 64-bit AMD64)
- **Pre-Install Package State**:
  - `rapidocr`: Not installed
  - `onnxruntime`: Not installed
  - `opencv-python` / `opencv-python-headless` / `opencv-contrib-python`: Not installed
  - `numpy`: `2.4.2`
  - `Pillow`: `13.0.0`
  - Pre-install `python -m pip check`: `No broken requirements found.` (Exit code `0`)
- **Preflight Dry-Run (`python -m pip install --dry-run rapidocr==3.10.0 onnxruntime==1.32.0`)**:
  - Confirmed zero upgrades or downgrades to existing core packages (`numpy`, `Pillow`, `PyYAML`, `requests`, `protobuf`, `packaging`).
  - Confirmed only `opencv-python-headless` would be installed (no conflicting `opencv-python`).

---

## 2. INSTALLATION SUMMARY

Executed:
```powershell
& "C:\Users\Ankit's_YOGA\AppData\Local\Programs\Python\Python313\python.exe" -m pip install rapidocr==3.10.0 onnxruntime==1.32.0
```

### Direct & Transitive Packages Installed
| Package | Version | Role / Status |
| :--- | :--- | :--- |
| `rapidocr` | `3.10.0` | Direct target package (newly installed) |
| `onnxruntime` | `1.32.0` | Direct target package (newly installed) |
| `opencv-python-headless` | `5.1.0.95` | Mandatory transitive dependency (newly installed; no `opencv-python` conflict) |
| `Shapely` | `2.2.0` | Mandatory transitive dependency (newly installed) |
| `pyclipper` | `1.4.0` | Mandatory transitive dependency (newly installed) |
| `omegaconf` | `2.4.0` | Mandatory transitive dependency (newly installed) |
| `colorlog` | `6.12.0` | Mandatory transitive dependency (newly installed) |
| `flatbuffers` | `25.12.19` | Mandatory transitive dependency (newly installed) |

### Core Package Stability (Before vs. After)
| Package | Version Before | Version After | Status |
| :--- | :--- | :--- | :--- |
| `numpy` | `2.4.2` | `2.4.2` | Unchanged |
| `Pillow` | `13.0.0` | `13.0.0` | Unchanged |
| `opencv-python` | Not installed | Not installed | Clean (only `opencv-python-headless 5.1.0.95` present) |

- **Dependency Manifest Status**: No Python dependency manifest (`requirements.txt` / `pyproject.toml`) exists in the repository (only `package.json` for Vite). Per instructions, no duplicate/conflicting manifest was created; maintaining a pinned Python `requirements.txt` remains a known repository limitation.

---

## 3. VERIFICATION RESULTS

1. **Imports & Versions**:
   - `rapidocr`: `3.10.0`
   - `onnxruntime`: `1.32.0`
   - `opencv-python-headless`: `5.1.0.95`
2. **ONNX Runtime Execution Providers**:
   - `ort.get_available_providers()`: `['AzureExecutionProvider', 'CPUExecutionProvider']` (`CPUExecutionProvider` confirmed present).
3. **Bundled Local Models (`rapidocr/models/`)**:
   - `PP-OCRv6_det_small.onnx`
   - `ch_ppocr_mobile_v2.0_cls_mobile.onnx`
   - `PP-OCRv6_rec_small.onnx`
   - Verified valid locally inside the network-isolated sandbox (zero external downloads or external OCR services used).
4. **OCR Initialization & Smoke Test**:
   - `RapidOCR()` initialized cleanly (`RapidOCR` using `onnxruntime`).
   - Rendered an in-memory 700x120 RGB Pillow image containing `"MEDICAL DOCUMENT OCR TEST"` and ran `engine(np.array(img))`:
     - **Recognized Text (`txts`)**: `('MEDICAL DOCUMENT OCR TEST',)`
     - **Confidence Score (`scores`)**: `(0.98017,)`
5. **`python -m pip check`**:
   - **Output**: `No broken requirements found.`
   - **Exit Code**: `0`

---

## 4. CONFLICTS & RESTRICTIONS COMPLIANCE

- **Conflicts / Unresolved Issues**: None (`0` broken requirements; `numpy` and `Pillow` unchanged; no `opencv-python` collision).
- **Restrictions Honored**:
  - No PyTorch OCR engines, PaddleOCR, OpenVINO, or Tesseract installed.
  - No external OCR models downloaded.
  - No application source code, tests, PDF extraction, frontend, or backend files modified.
  - OCR extractor implementation has **not** begun.
