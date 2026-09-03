from src.data_readiness import assign_readiness_status, build_processing_error_record, compute_readiness_metrics


def test_assign_readiness_status_handles_missing_material():
    element = {
        'ifc_class': 'IfcWall',
        'material_name': '',
        'quantity_value': 10,
        'quantity_unit': 'm3',
        'material_match_status': 'missing',
        'quantity_supported': True,
        'unit_compatible': True,
        'issues': [],
        'calculation_possible': False,
    }
    updated = assign_readiness_status(element)
    assert 'missing material' in updated['issues']
    assert updated['readiness_status'] == 'missing material'


def test_compute_readiness_metrics():
    elements = [
        {'calculation_possible': True, 'material_name': 'Concrete', 'quantity_value': 1, 'quantity_unit': 'm3', 'material_match_status': 'matched', 'issues': [], 'unit_compatible': True},
        {'calculation_possible': False, 'material_name': '', 'quantity_value': None, 'quantity_unit': '', 'material_match_status': 'missing', 'issues': ['missing material', 'missing quantity', 'missing unit'], 'unit_compatible': True},
    ]
    metrics = compute_readiness_metrics(elements)
    assert metrics['total_elements'] == 2
    assert metrics['calculated_elements'] == 1
    assert metrics['missing_or_incomplete'] == 1


def test_multiple_materials_are_not_counted_as_unmatched_factors():
    element = {
        'calculation_possible': False,
        'material_name': 'Concrete; Insulation; Plasterboard',
        'multiple_materials': True,
        'material_match_status': 'multiple_materials_review_required',
        'quantity_value': 2,
        'quantity_unit': 'm3',
        'unit_compatible': True,
        'issues': ['multiple materials require review'],
    }
    metrics = compute_readiness_metrics([element])
    assert metrics['unmatched_materials'] == 0
    assert metrics['multiple_material_elements'] == 1
    assert metrics['material_completeness'] == 100


def test_factor_coverage_and_attempt_success_use_distinct_denominators():
    base = {
        'calculation_possible': False, 'material_name': 'Material',
        'quantity_value': 1, 'quantity_unit': 'm3', 'unit_compatible': True,
        'issues': [],
    }
    elements = [
        {**base, 'material_match_status': 'matched'} for _ in range(2)
    ] + [
        {**base, 'material_match_status': 'unmatched'},
        {**base, 'material_match_status': 'multiple_materials_review_required', 'multiple_materials': True},
        {**base, 'material_name': '', 'material_match_status': 'missing'},
    ]

    metrics = compute_readiness_metrics(elements)

    assert metrics['factor_coverage_rate'] == 40.0
    assert metrics['carbon_match_rate'] == 40.0
    assert metrics['factor_match_attempts'] == 3
    assert metrics['factor_match_success_rate'] == 2 / 3 * 100


def test_zero_quantity_is_invalid_and_not_complete():
    element = {
        'ifc_class': 'IfcWall', 'material_name': 'Concrete', 'quantity_value': 0,
        'quantity_unit': 'm3', 'material_match_status': 'matched',
        'quantity_supported': True, 'unit_compatible': True, 'issues': [],
        'calculation_possible': False,
    }
    updated = assign_readiness_status(element)
    metrics = compute_readiness_metrics([updated])
    assert updated['readiness_status'] == 'invalid quantity'
    assert metrics['quantity_completeness'] == 0


def test_placeholder_material_is_not_counted_as_complete():
    element = {
        'calculation_possible': False, 'material_name': '<Unnamed>',
        'material_match_status': 'invalid', 'quantity_value': 1,
        'quantity_unit': 'm3', 'unit_compatible': True,
        'issues': ['invalid placeholder material'],
    }
    metrics = compute_readiness_metrics([element])
    assert metrics['material_completeness'] == 0
    assert metrics['carbon_match_rate'] == 0


def test_processing_error_record_preserves_identity_and_diagnostic():
    source = {
        'global_id': 'ABC123', 'ifc_class': 'IfcWall', 'element_name': 'Wall 01',
        'storey': 'Level 2', 'material_name': 'Concrete',
        'quantity_name': 'NetVolume', 'quantity_value': 10, 'quantity_unit': 'm3',
    }
    record = build_processing_error_record(source, ValueError('bad quantity payload'))
    assert record['global_id'] == 'ABC123'
    assert record['material_name'] == 'Concrete'
    assert record['extraction_error'] == ''
    assert record['processing_error'] == 'ValueError: bad quantity payload'
    assert record['calculation_reason'] == record['processing_error']
    assert record['readiness_status'] == 'processing error'
    assert record['calculation_possible'] is False


def test_processing_error_record_preserves_original_ifc_raw_quantity():
    source = {
        'global_id': 'RAW1', 'ifc_class': 'IfcWall', 'quantity_value': 1.0,
        'quantity_unit': 'm3', 'quantities': [{
            'quantity_set_name': 'BaseQuantities', 'name': 'NetVolume',
            'type': 'IfcQuantityVolume', 'value': 1.0, 'unit': 'm3',
            'raw_value': 35.3147, 'raw_unit': 'ft3',
            'conversion_factor': 0.028316846592, 'unit_source': 'project',
        }],
    }
    record = build_processing_error_record(source, RuntimeError('later failure'))
    assert record['raw_quantity_value'] == 35.3147
    assert record['raw_quantity_unit'] == 'ft3'
    assert record['unit_conversion_factor'] == 0.028316846592
    assert record['quantity_set_name'] == 'BaseQuantities'


def test_extraction_failure_takes_priority_over_multiple_material_review():
    element = {
        'calculation_possible': False, 'material_name': 'A; B',
        'material_match_status': 'multiple_materials_review_required',
        'multiple_materials': True, 'quantity_extraction_error': 'RuntimeError: boom',
        'quantity_value': None, 'quantity_unit': '', 'quantity_supported': False,
        'unit_compatible': True, 'issues': [],
    }
    result = assign_readiness_status(element)
    assert result['readiness_status'] == 'quantity extraction failed'
