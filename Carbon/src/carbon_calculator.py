from __future__ import annotations

from src.utils import is_positive_finite_number, normalise_unit


def select_quantity_for_factor(quantities: list[dict], carbon_factor_unit: str, density_kg_per_m3: float | None = None) -> dict:
    """Select the quantity that can actually be used with the matched factor."""
    available = [q for q in quantities if q.get('value') is not None]

    def preference(quantity: dict) -> tuple[int, str]:
        name = ''.join(character for character in str(quantity.get('name') or '').lower() if character.isalnum())
        if name.startswith('net'):
            return 0, name
        if name.startswith('gross'):
            return 1, name
        return 2, name

    available = sorted(available, key=preference)
    valid_available = [q for q in available if is_positive_finite_number(q.get('value'))]
    factor_unit = normalise_unit(carbon_factor_unit)
    direct_unit = {
        'kgco2e/kg': 'kg',
        'kgco2e/m3': 'm3',
        'kgco2e/m2': 'm2',
        'kgco2e/item': 'item',
    }.get(factor_unit)

    def inferred_unit(quantity: dict) -> str:
        quantity_type = str(quantity.get('type') or '').lower()
        quantity_name = str(quantity.get('name') or '').lower()
        for marker, unit in (
            ('volume', 'm3'), ('area', 'm2'), ('weight', 'kg'),
            ('mass', 'kg'), ('count', 'item'), ('length', 'm'),
        ):
            if marker in quantity_type or marker in quantity_name:
                return unit
        return ''

    unresolved = sorted(
        [q for q in quantities if q.get('value') is None and q.get('raw_value') is not None],
        key=preference,
    )

    def unresolved_is_compatible(quantity: dict) -> bool:
        unit = inferred_unit(quantity)
        return unit == direct_unit or (factor_unit == 'kgco2e/kg' and unit == 'm3')

    for quantity in valid_available:
        if normalise_unit(quantity.get('unit')) == direct_unit:
            return {**quantity, 'selection_method': 'direct_factor_unit_match_net_preferred'}
    if factor_unit == 'kgco2e/kg':
        for quantity in valid_available:
            if normalise_unit(quantity.get('unit')) == 'm3':
                method = 'volume_to_mass_using_factor_density' if is_positive_finite_number(density_kg_per_m3) else 'volume_requires_factor_density'
                return {**quantity, 'selection_method': method}
    for quantity in unresolved:
        if unresolved_is_compatible(quantity):
            return {**quantity, 'selection_method': 'quantity_present_unit_unresolved'}
    if valid_available:
        return {**valid_available[0], 'selection_method': 'no_compatible_valid_quantity'}

    # Preserve an invalid value when no valid alternative exists so readiness
    # reporting can diagnose it as invalid rather than incorrectly calling it missing.
    for quantity in available:
        if normalise_unit(quantity.get('unit')) == direct_unit:
            return {**quantity, 'selection_method': 'invalid_compatible_quantity_for_diagnosis'}
    if factor_unit == 'kgco2e/kg':
        for quantity in available:
            if normalise_unit(quantity.get('unit')) == 'm3':
                return {**quantity, 'selection_method': 'invalid_volume_quantity_for_diagnosis'}
    if available:
        return {**available[0], 'selection_method': 'invalid_quantity_for_diagnosis'}

    if unresolved:
        return {**unresolved[0], 'selection_method': 'quantity_present_unit_unresolved'}
    return {
        'name': '', 'value': None, 'unit': '', 'type': '',
        'raw_value': None, 'raw_unit': '', 'conversion_factor': None,
        'unit_source': '', 'selection_method': 'no_usable_quantity',
    }


def calculate_embodied_carbon(quantity_value: float, quantity_unit: str, carbon_factor: float, carbon_factor_unit: str, density_kg_per_m3: float | None = None):
    q_unit = normalise_unit(quantity_unit)
    c_unit = normalise_unit(carbon_factor_unit)

    if quantity_value is None:
        return {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'Missing quantity',
            'failure_code': 'missing_quantity',
        }
    if not is_positive_finite_number(quantity_value):
        return {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'Quantity must be numeric, finite, and greater than zero',
            'failure_code': 'invalid_quantity',
        }
    if carbon_factor is None:
        return {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'Missing carbon factor',
            'failure_code': 'missing_carbon_factor',
        }
    if not is_positive_finite_number(carbon_factor):
        return {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'Carbon factor must be numeric, finite, and greater than zero',
            'failure_code': 'invalid_carbon_factor',
        }

    if q_unit == 'm3' and c_unit == 'kgco2e/m3':
        return {
            'calculation_possible': True,
            'embodied_carbon_kgco2e': float(quantity_value) * float(carbon_factor),
            'calculated_mass_kg': None,
            'reason': 'Volume quantity matched to kgCO2e/m3 factor',
            'failure_code': '',
        }

    density_is_valid = is_positive_finite_number(density_kg_per_m3)

    if q_unit == 'm3' and c_unit == 'kgco2e/kg' and density_is_valid:
        return {
            'calculation_possible': True,
            'embodied_carbon_kgco2e': float(quantity_value) * float(density_kg_per_m3) * float(carbon_factor),
            'calculated_mass_kg': float(quantity_value) * float(density_kg_per_m3),
            'reason': 'Volume converted to mass using material density and matched to kgCO2e/kg factor',
            'failure_code': '',
        }

    if q_unit == 'm2' and c_unit == 'kgco2e/m2':
        return {
            'calculation_possible': True,
            'embodied_carbon_kgco2e': float(quantity_value) * float(carbon_factor),
            'calculated_mass_kg': None,
            'reason': 'Area quantity matched to kgCO2e/m2 factor',
            'failure_code': '',
        }

    if q_unit == 'kg' and c_unit == 'kgco2e/kg':
        return {
            'calculation_possible': True,
            'embodied_carbon_kgco2e': float(quantity_value) * float(carbon_factor),
            'calculated_mass_kg': float(quantity_value),
            'reason': 'Mass quantity matched to kgCO2e/kg factor',
            'failure_code': '',
        }

    if q_unit in {'item', 'count'} and c_unit == 'kgco2e/item':
        return {
            'calculation_possible': True,
            'embodied_carbon_kgco2e': float(quantity_value) * float(carbon_factor),
            'calculated_mass_kg': None,
            'reason': 'Count quantity matched to kgCO2e/item factor',
            'failure_code': '',
        }

    if q_unit == 'm3' and c_unit == 'kgco2e/kg' and not density_is_valid:
        return {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'A positive finite density is required to convert volume to mass',
            'failure_code': 'missing_or_invalid_density',
        }

    return {
        'calculation_possible': False,
        'embodied_carbon_kgco2e': 0.0,
        'reason': f'Incompatible quantity and carbon-factor units: {q_unit} with {c_unit}',
        'failure_code': 'incompatible_units',
    }
