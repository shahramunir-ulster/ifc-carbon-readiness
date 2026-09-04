from __future__ import annotations

from typing import Any, Dict, List

from src.material_normaliser import is_placeholder_material_name
from src.utils import is_positive_finite_number


def build_processing_error_record(element: Dict[str, Any], error: Exception) -> Dict[str, Any]:
    """Retain element identity and a bounded diagnostic when processing fails."""
    error_detail = f'{type(error).__name__}: {error}'[:1000]
    quantities = element.get('quantities') or []
    raw_quantity = next(
        (quantity for quantity in quantities if quantity.get('raw_value') is not None),
        quantities[0] if quantities else {},
    )
    existing_extraction_error = str(element.get('extraction_error') or '').strip()
    return {
        **element,
        'global_id': element.get('global_id', ''),
        'ifc_class': element.get('ifc_class', 'Unknown'),
        'element_name': element.get('element_name', ''),
        'storey': element.get('storey', ''),
        'material_name': element.get('material_name', ''),
        'material_normalised': '',
        'material_match_status': 'error',
        'matched_material_name': '',
        'matching_method': 'processing_error',
        'matching_confidence': 'none',
        'carbon_factor': None,
        'carbon_factor_unit': '',
        'density_kg_per_m3': None,
        'density_source': '',
        'life_cycle_stage': '',
        'carbon_factor_source': '',
        'carbon_factor_source_type': '',
        'carbon_factor_is_demo': False,
        'material_id': '',
        'factor_category': '',
        'factor_notes': '',
        'factor_is_proxy': False,
        'quantity_name': raw_quantity.get('name', element.get('quantity_name', '')),
        'quantity_type': raw_quantity.get('type', element.get('quantity_type', '')),
        'raw_quantity_value': raw_quantity.get('raw_value', element.get('quantity_value')),
        'raw_quantity_unit': raw_quantity.get('raw_unit', element.get('quantity_unit', '')),
        'unit_conversion_factor': raw_quantity.get('conversion_factor'),
        'unit_source': raw_quantity.get('unit_source', ''),
        'quantity_selection_method': 'processing_error',
        'quantity_set_name': raw_quantity.get('quantity_set_name', element.get('quantity_set_name', '')),
        'calculated_mass_kg': None,
        'unit_compatible': None,
        'calculation_possible': False,
        'embodied_carbon_kgco2e': 0.0,
        'calculation_reason': error_detail,
        'calculation_failure_code': 'processing_error',
        'readiness_status': 'processing error',
        'issues': ['processing error'],
        'extraction_error': existing_extraction_error,
        'processing_error': error_detail,
        'recommended_action': 'Inspect this element and the recorded processing error, then retry.',
    }


def assign_readiness_status(element: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = list(element.get('issues', []) or [])
    if not issues:
        issues = []

    material_extraction_failed = bool(element.get('material_extraction_error'))
    quantity_extraction_failed = bool(element.get('quantity_extraction_error'))

    if element.get('ifc_class') in {'IfcBuildingElementProxy', 'IfcElement'} and not element.get('element_name'):
        issues.append('unclear classification')

    if material_extraction_failed:
        issues.append('material extraction failed')
    else:
        if not element.get('material_name'):
            issues.append('missing material')
        if element.get('material_match_status') == 'invalid':
            issues.append('invalid placeholder material')

    if quantity_extraction_failed:
        issues.append('quantity extraction failed')
    else:
        quantity_exists = (
            element.get('quantity_value') is not None
            or element.get('raw_quantity_value') is not None
        )
        if element.get('quantity_value') is None:
            if is_positive_finite_number(element.get('raw_quantity_value')):
                issues.append('unresolved quantity unit')
            else:
                issues.append('missing quantity')
        elif not is_positive_finite_number(element.get('quantity_value')):
            issues.append('invalid quantity')
        if not element.get('quantity_unit'):
            issues.append('missing unit')
        if (
            quantity_exists
            and element.get('quantity_supported') is False
            and element.get('calculation_failure_code') != 'unresolved_quantity_unit'
        ):
            issues.append('unsupported quantity type')
    if element.get('processing_error'):
        issues.append('processing error')
    if not element.get('material_match_status') or element.get('material_match_status') == 'unmatched':
        issues.append('unmatched material')
    if element.get('unit_compatible') is False:
        issues.append('incompatible quantity and carbon-factor units')
    failure_code = element.get('calculation_failure_code')
    if failure_code == 'invalid_carbon_factor':
        issues.append('invalid carbon factor')
    elif failure_code == 'missing_or_invalid_density':
        issues.append('missing or invalid density')
    if (
        element.get('multiple_materials')
        or element.get('material_match_status') == 'multiple_materials_review_required'
    ):
        issues.append('multiple materials require review')
    if element.get('ifc_class') in {'IfcElement'}:
        issues.append('unclear classification')

    unique_issues = []
    seen = set()
    for issue in issues:
        key = str(issue).strip().lower()
        if key and key not in seen:
            unique_issues.append(key)
            seen.add(key)

    calculation_possible = bool(element.get('calculation_possible'))
    primary_status = 'ready / carbon calculated' if calculation_possible else 'missing data'

    if 'processing error' in unique_issues:
        primary_status = 'processing error'
    elif 'material extraction failed' in unique_issues:
        primary_status = 'material extraction failed'
    elif 'quantity extraction failed' in unique_issues:
        primary_status = 'quantity extraction failed'
    elif 'multiple materials require review' in unique_issues:
        primary_status = 'multiple materials require review'
    elif 'missing material' in unique_issues:
        primary_status = 'missing material'
    elif 'invalid placeholder material' in unique_issues:
        primary_status = 'invalid placeholder material'
    elif 'missing quantity' in unique_issues:
        primary_status = 'missing quantity'
    elif 'invalid quantity' in unique_issues:
        primary_status = 'invalid quantity'
    elif 'unresolved quantity unit' in unique_issues or 'missing unit' in unique_issues:
        primary_status = 'missing or unresolved unit'
    elif 'unmatched material' in unique_issues:
        primary_status = 'no matching carbon factor'
    elif 'unsupported quantity type' in unique_issues:
        primary_status = 'unsupported quantity type'
    elif 'incompatible quantity and carbon-factor units' in unique_issues:
        primary_status = 'incompatible quantity and carbon-factor units'
    elif 'invalid carbon factor' in unique_issues:
        primary_status = 'invalid carbon factor'
    elif 'missing or invalid density' in unique_issues:
        primary_status = 'missing or invalid density'
    elif 'unclear classification' in unique_issues:
        primary_status = 'unclear classification'
    elif 'not applicable' in unique_issues:
        primary_status = 'not applicable / excluded element'

    recommended_action = element.get('recommended_action', 'Review element data and update the IFC model.')
    element['issues'] = unique_issues
    element['readiness_status'] = primary_status
    element['recommended_action'] = recommended_action
    return element


def compute_readiness_metrics(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(elements)
    if total == 0:
        return {
            'total_elements': 0,
            'calculated_elements': 0,
            'calculation_success_rate': 0.0,
            'material_completeness': 0.0,
            'quantity_completeness': 0.0,
            'unit_completeness': 0.0,
            'factor_coverage_rate': 0.0,
            'factor_match_attempts': 0,
            'factor_match_success_rate': 0.0,
            'carbon_match_rate': 0.0,
            'ready_score': 0.0,
            'missing_or_incomplete': 0,
            'unmatched_materials': 0,
            'multiple_material_elements': 0,
            'incompatible_units': 0,
            'unclear_classification': 0,
        }

    calculated = sum(1 for e in elements if e.get('calculation_possible'))
    materials_present = sum(
        1 for e in elements
        if e.get('material_name')
        and e.get('material_match_status') != 'invalid'
        and not is_placeholder_material_name(e.get('material_name'))
    )
    quantities_present = sum(1 for e in elements if is_positive_finite_number(e.get('quantity_value')))
    units_present = sum(1 for e in elements if e.get('quantity_unit'))
    factor_matches = sum(1 for e in elements if e.get('material_match_status') == 'matched')
    factor_match_attempts = sum(
        1 for e in elements if e.get('material_match_status') in {'matched', 'unmatched'}
    )
    missing_or_incomplete = sum(1 for e in elements if not e.get('calculation_possible'))
    unmatched_materials = sum(1 for e in elements if e.get('material_match_status') == 'unmatched')
    multiple_material_elements = sum(
        1 for e in elements
        if e.get('material_match_status') == 'multiple_materials_review_required'
        or e.get('multiple_materials')
    )
    incompatible_units = sum(
        1 for e in elements
        if e.get('calculation_failure_code') == 'incompatible_units'
        or 'incompatible quantity and carbon-factor units' in e.get('issues', [])
    )
    unclear_classification = sum(1 for e in elements if 'unclear classification' in e.get('issues', []))
    factor_coverage_rate = (factor_matches / total) * 100
    factor_match_success_rate = (
        (factor_matches / factor_match_attempts) * 100 if factor_match_attempts else 0.0
    )

    readiness_score = (
        (materials_present / total) * 100 +
        (quantities_present / total) * 100 +
        (units_present / total) * 100 +
        (factor_matches / total) * 100 +
        (calculated / total) * 100
    ) / 5

    return {
        'total_elements': total,
        'calculated_elements': calculated,
        'calculation_success_rate': (calculated / total) * 100,
        'material_completeness': (materials_present / total) * 100,
        'quantity_completeness': (quantities_present / total) * 100,
        'unit_completeness': (units_present / total) * 100,
        'factor_coverage_rate': factor_coverage_rate,
        'factor_match_attempts': factor_match_attempts,
        'factor_match_success_rate': factor_match_success_rate,
        # Backwards-compatible alias. This is coverage across all eligible elements,
        # not success among the subset where factor matching can be attempted.
        'carbon_match_rate': factor_coverage_rate,
        'ready_score': readiness_score,
        'missing_or_incomplete': missing_or_incomplete,
        'unmatched_materials': unmatched_materials,
        'multiple_material_elements': multiple_material_elements,
        'incompatible_units': incompatible_units,
        'unclear_classification': unclear_classification,
    }
