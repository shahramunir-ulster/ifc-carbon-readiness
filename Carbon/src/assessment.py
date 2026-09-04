from __future__ import annotations

import pandas as pd

from src.carbon_calculator import calculate_embodied_carbon, select_quantity_for_factor
from src.carbon_factors import match_material_to_factor
from src.data_readiness import assign_readiness_status
from src.ifc_parser import SUPPORTED_ELEMENT_CLASSES
from src.material_normaliser import normalise_material_name
from src.utils import safe_float


def process_element_record(element: dict, factor_dataframe: pd.DataFrame) -> dict:
    """Apply the same matching, quantity selection, calculation, and readiness logic used by the UI."""
    material_name = str(element.get('material_name') or '').strip()
    normalised = normalise_material_name(material_name)
    factor_match = match_material_to_factor(
        material_name, factor_dataframe.to_dict(orient='records')
    ) if material_name else {
        'matched': False, 'matching_method': 'missing_material',
        'matching_confidence': 'none', 'matched_material_name': '',
        'carbon_factor': None, 'carbon_factor_unit': '', 'reason': 'Material missing',
        'carbon_factor_source': '', 'carbon_factor_is_demo': False,
    }
    multiple_material_review_required = bool(
        element.get('multiple_materials')
        or factor_match.get('matching_method') == 'multiple_materials'
    )
    if multiple_material_review_required:
        normalised = 'multiple materials'

    carbon_factor = factor_match.get('carbon_factor')
    carbon_factor_unit = str(factor_match.get('carbon_factor_unit') or '').strip()
    density_kg_per_m3 = factor_match.get('density_kg_per_m3')
    quantities = element.get('quantities') or [{
        'name': element.get('quantity_name', ''),
        'quantity_set_name': element.get('quantity_set_name', ''),
        'value': safe_float(element.get('quantity_value')),
        'unit': element.get('quantity_unit', ''),
        'type': '',
        'raw_value': safe_float(element.get('quantity_value')),
        'raw_unit': element.get('quantity_unit', ''),
        'conversion_factor': 1.0,
        'unit_source': 'provided',
    }]
    selected = select_quantity_for_factor(quantities, carbon_factor_unit, density_kg_per_m3)
    quantity_value = safe_float(selected.get('value'))
    quantity_unit = str(selected.get('unit') or '').strip()
    calculation = calculate_embodied_carbon(
        quantity_value, quantity_unit, carbon_factor, carbon_factor_unit, density_kg_per_m3
    )
    if selected.get('selection_method') == 'quantity_present_unit_unresolved':
        calculation = {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'Quantity exists, but its IFC unit could not be resolved for SI conversion',
            'failure_code': 'unresolved_quantity_unit',
        }

    scope_status = element.get('scope_status')
    if (scope_status and scope_status != 'assessment_eligible') or (
        not scope_status and element.get('ifc_class') not in SUPPORTED_ELEMENT_CLASSES
    ):
        calculation = {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'Unsupported or unclear IFC element classification',
            'failure_code': 'outside_assessment_scope',
        }

    extraction_failed = bool(
        element.get('material_extraction_error') or element.get('quantity_extraction_error')
    )
    if extraction_failed:
        calculation = {
            'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0,
            'reason': 'IFC material or quantity extraction failed for this element',
            'failure_code': 'extraction_error',
        }
    if extraction_failed:
        match_status = 'error'
    elif multiple_material_review_required:
        match_status = 'multiple_materials_review_required'
    elif not material_name:
        match_status = 'missing'
    elif factor_match.get('matching_method') == 'invalid_placeholder':
        match_status = 'invalid'
    elif factor_match.get('matched'):
        match_status = 'matched'
    else:
        match_status = 'unmatched'

    element.update({
        'material_normalised': normalised,
        'multiple_materials': multiple_material_review_required,
        'material_match_status': match_status,
        'matched_material_name': factor_match.get('matched_material_name', ''),
        'carbon_factor': carbon_factor,
        'carbon_factor_unit': carbon_factor_unit,
        'density_kg_per_m3': density_kg_per_m3,
        'density_source': factor_match.get('density_source', ''),
        'carbon_factor_source': factor_match.get('carbon_factor_source', ''),
        'carbon_factor_is_demo': factor_match.get('carbon_factor_is_demo', False),
        'material_id': factor_match.get('material_id', ''),
        'factor_category': factor_match.get('factor_category', ''),
        'factor_notes': factor_match.get('factor_notes', ''),
        'factor_is_proxy': factor_match.get('factor_is_proxy', False),
        'matching_method': factor_match.get('matching_method', 'none'),
        'matching_confidence': factor_match.get('matching_confidence', 'none'),
        'life_cycle_stage': factor_match.get('life_cycle_stage', ''),
        'carbon_factor_source_type': factor_match.get('carbon_factor_source_type', ''),
        'quantity_name': selected.get('name', ''),
        'quantity_type': selected.get('type', ''),
        'quantity_set_name': selected.get('quantity_set_name', ''),
        'quantity_value': quantity_value,
        'quantity_unit': quantity_unit,
        'raw_quantity_value': selected.get('raw_value'),
        'raw_quantity_unit': selected.get('raw_unit', ''),
        'unit_conversion_factor': selected.get('conversion_factor'),
        'unit_source': selected.get('unit_source', ''),
        'quantity_selection_method': selected.get('selection_method', ''),
        'quantity_supported': bool(
            selected.get('selection_method') == 'quantity_present_unit_unresolved'
            or quantity_unit in {'m3', 'm2', 'kg', 'item'}
        ),
        'unit_compatible': calculation.get('failure_code') != 'incompatible_units',
        'calculation_possible': bool(calculation.get('calculation_possible', False)),
        'embodied_carbon_kgco2e': float(calculation.get('embodied_carbon_kgco2e', 0.0) or 0.0),
        'calculated_mass_kg': calculation.get('calculated_mass_kg'),
        'calculation_reason': calculation.get('reason', ''),
        'calculation_failure_code': calculation.get('failure_code', ''),
        'reason': factor_match.get('reason', ''),
    })

    if extraction_failed:
        element['recommended_action'] = 'Inspect the recorded IFC extraction error and retry the assessment.'
    elif multiple_material_review_required:
        element['recommended_action'] = 'Allocate quantities by material layer before carbon calculation.'
    elif not material_name:
        element['recommended_action'] = 'Add material name in BIM model.'
    elif factor_match.get('matching_method') == 'invalid_placeholder':
        element['recommended_action'] = 'Replace the placeholder with a specific, verified material assignment in the BIM model.'
    elif not factor_match.get('matched'):
        element['recommended_action'] = 'Add or verify a carbon-factor mapping for this material.'
    elif calculation.get('failure_code') == 'missing_quantity':
        element['recommended_action'] = 'Export or add an appropriate IFC base quantity for this element.'
    elif calculation.get('failure_code') == 'invalid_quantity':
        element['recommended_action'] = 'Correct the zero, negative, or invalid BIM quantity and re-export the IFC model.'
    elif calculation.get('failure_code') == 'unresolved_quantity_unit':
        element['recommended_action'] = 'Define or repair the IFC project or quantity unit and re-export the model.'
    elif calculation.get('failure_code') == 'missing_or_invalid_density':
        element['recommended_action'] = 'Provide a verified density with source, or provide a mass quantity.'
    elif calculation.get('failure_code') == 'incompatible_units':
        element['recommended_action'] = 'Provide a quantity compatible with the selected carbon-factor unit.'
    elif not calculation.get('calculation_possible', False):
        element['recommended_action'] = 'Review the calculation diagnostic and update the IFC or factor data.'
    else:
        element['recommended_action'] = 'Use this result as a preliminary estimate only.'
    return assign_readiness_status(element)
