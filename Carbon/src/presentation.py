from __future__ import annotations


def carbon_headline(calculated_elements: int, eligible_elements: int) -> str:
    """Return a scope-safe carbon headline that never implies whole-model completeness."""
    prefix = '' if eligible_elements > 0 and calculated_elements >= eligible_elements else 'Partial '
    return f'{prefix}calculated A1-A3 carbon - assessment-eligible elements'


def carbon_display_tonnes(carbon_kgco2e: float) -> str:
    return f'{float(carbon_kgco2e) / 1000:,.2f} tCO2e'
