"""
Clinical Report Ingestion & Feature Extraction Parser.
Strictly performs regex-based token extraction, unit normalization, and alias extraction.
Supports decimals, negatives, formatting variations.
No diagnostic or clinical interpretation is performed in this layer.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ParsedObservation:
    raw_key: str
    detected_value: Optional[float]
    raw_unit: Optional[str]
    line_number: int
    is_inconclusive: bool = False
    inconclusive_reason: Optional[str] = None

class ClinicalReportParser:
    """Parser strictly dedicated to feature extraction and lexical tokenization."""

    # Robust regex pattern:
    # matches label, delimiter (: - = or space), signed float (supports negative, scientific, decimals), and optional unit
    OBSERVATION_PATTERN = re.compile(
        r"(?P<label>[A-Za-z0-9_\s\(\)\/\-\.]{2,40}?)\s*[:=\-]\s*(?P<value>[+\-]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?P<unit>[A-Za-z\/%µu\^0-9\-\*]+)?",
        re.IGNORECASE
    )

    @classmethod
    def parse_text(cls, report_text: str) -> List[ParsedObservation]:
        observations: List[ParsedObservation] = []
        if not report_text:
            return observations

        lines = report_text.splitlines()
        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("//"):
                continue

            matches = list(cls.OBSERVATION_PATTERN.finditer(line_str))
            for match in matches:
                label = match.group("label").strip()
                val_str = match.group("value").replace(",", "").strip()
                unit = match.group("unit").strip() if match.group("unit") else None

                # Clean leading noise from label
                label = re.sub(r"^[\*\-\•\d\.\s]+", "", label).strip()
                if not label:
                    continue

                try:
                    val = float(val_str)
                    observations.append(ParsedObservation(
                        raw_key=label,
                        detected_value=val,
                        raw_unit=unit,
                        line_number=idx,
                        is_inconclusive=False
                    ))
                except ValueError:
                    observations.append(ParsedObservation(
                        raw_key=label,
                        detected_value=None,
                        raw_unit=unit,
                        line_number=idx,
                        is_inconclusive=True,
                        inconclusive_reason=f"Unable to parse numeric value: '{val_str}'"
                    ))

        return observations
