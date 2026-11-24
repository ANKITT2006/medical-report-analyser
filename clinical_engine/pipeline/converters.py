"""
Allowlisted Unit Conversion Registry & Safe Execution Engine.
Strictly prohibits eval() / exec() dynamic execution.
"""

from typing import Optional, Dict, Any
from clinical_engine.domain.schemas import ConversionAudit

class UnitConversionRegistry:
    """Allowlisted mathematical conversion routines for laboratory units."""

    @staticmethod
    def linear_scale(value: float, factor: float) -> float:
        if factor is None or factor <= 0:
            raise ValueError(f"Invalid linear conversion factor: {factor}")
        return round(value * factor, 4)

    @staticmethod
    def hba1c_ifcc_to_ngsp(value: float, factor: Optional[float] = None) -> float:
        """
        Converts IFCC HbA1c (mmol/mol) to NGSP (%).
        Formula: NGSP % = (0.09148 * IFCC) + 2.152
        Master DCCT / IFCC equation standardized worldwide.
        """
        if value < 0:
            raise ValueError(f"Negative HbA1c value ({value}) is physiologically impossible.")
        return round((0.09148 * value) + 2.152, 2)


ALLOWED_CONVERSION_HANDLERS = {
    "LINEAR_SCALE": UnitConversionRegistry.linear_scale,
    "HBA1C_IFCC_TO_NGSP": UnitConversionRegistry.hba1c_ifcc_to_ngsp
}


def convert_laboratory_value(
    detected_value: float,
    incoming_unit: str,
    standard_unit: str,
    conversion_type: str,
    handler_name: str,
    factor: Optional[float],
    formula_str: str
) -> Dict[str, Any]:
    """
    Safely executes an allowlisted unit conversion routine.
    Returns dictionary with converted_value and full audit trail.
    """
    if incoming_unit.strip().lower() == standard_unit.strip().lower():
        return {
            "converted_value": detected_value,
            "standard_unit": standard_unit,
            "conversion_applied": False,
            "audit": None
        }

    if handler_name not in ALLOWED_CONVERSION_HANDLERS:
        raise ValueError(f"Unauthorized or unknown conversion handler: '{handler_name}'. Rejected by security allowlist.")

    handler_fn = ALLOWED_CONVERSION_HANDLERS[handler_name]

    if handler_name == "LINEAR_SCALE":
        if factor is None:
            raise ValueError(f"Linear conversion requires valid positive factor for {incoming_unit} -> {standard_unit}")
        converted = handler_fn(detected_value, factor)
    elif handler_name == "HBA1C_IFCC_TO_NGSP":
        converted = handler_fn(detected_value)
    else:
        raise ValueError(f"Handler '{handler_name}' registered but execution pathway undefined.")

    audit = ConversionAudit(
        original_value=detected_value,
        original_unit=incoming_unit,
        converted_value=converted,
        standard_unit=standard_unit,
        conversion_type=conversion_type,
        formula_used=formula_str,
        handler_executed=handler_name
    )

    audit_dict = audit.model_dump() if hasattr(audit, "model_dump") else (audit.dict() if hasattr(audit, "dict") else audit.__dict__)

    return {
        "converted_value": converted,
        "standard_unit": standard_unit,
        "conversion_applied": True,
        "audit": audit_dict
    }

