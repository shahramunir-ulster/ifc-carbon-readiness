import pandas as pd

from src.assessment import process_element_record


def test_process_element_assigns_distinct_multiple_material_status():
    element = {
        'global_id': 'layered-wall',
        'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible',
        'material_name': 'Concrete; Insulation; Plasterboard',
        'multiple_materials': True,
        'quantities': [{
            'name': 'NetVolume', 'value': 2.0, 'unit': 'm3',
            'raw_value': 2.0, 'raw_unit': 'm3', 'conversion_factor': 1.0,
            'unit_source': 'project',
        }],
    }
    factors = pd.DataFrame([{
        'material_name': 'Concrete', 'normalised_name': 'concrete',
        'carbon_factor': 0.1, 'unit': 'kgco2e/kg',
        'density_kg_per_m3': 2300, 'density_source': 'test density',
        'life_cycle_stage': 'A1-A3', 'source': 'test factor',
    }])

    result = process_element_record(element, factors)

    assert result['material_match_status'] == 'multiple_materials_review_required'
    assert result['readiness_status'] == 'multiple materials require review'
    assert result['calculation_possible'] is False
    assert result['recommended_action'] == 'Allocate quantities by material layer before carbon calculation.'
    assert result['material_normalised'] == 'multiple materials'


def test_matching_method_alone_triggers_multiple_material_recommended_action(monkeypatch):
    element = {
        'global_id': 'defensive-layered-wall', 'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible', 'material_name': 'Layer A; Layer B',
        'multiple_materials': False,
        'quantities': [{'name': 'NetVolume', 'value': 2.0, 'unit': 'm3'}],
    }
    factors = pd.DataFrame([{'material_name': 'Concrete'}])

    result = process_element_record(element, factors)

    assert result['matching_method'] == 'multiple_materials'
    assert result['material_match_status'] == 'multiple_materials_review_required'
    assert result['recommended_action'] == 'Allocate quantities by material layer before carbon calculation.'
    assert result['readiness_status'] == 'multiple materials require review'
    assert result['multiple_materials'] is True


def test_unresolved_unit_preserves_raw_quantity_and_reports_unit_problem():
    element = {
        'global_id': 'unresolved-unit', 'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible', 'material_name': 'Concrete',
        'multiple_materials': False,
        'quantities': [{
            'quantity_set_name': 'BaseQuantities', 'name': 'NetVolume',
            'value': None, 'unit': '', 'raw_value': 100.0, 'raw_unit': '',
            'conversion_factor': None, 'unit_source': 'missing',
        }],
    }
    factors = pd.DataFrame([{
        'material_name': 'Concrete', 'normalised_name': 'concrete',
        'carbon_factor': 0.1, 'unit': 'kgco2e/kg',
        'density_kg_per_m3': 2300, 'density_source': 'test density',
        'life_cycle_stage': 'A1-A3', 'source': 'test factor',
    }])

    result = process_element_record(element, factors)

    assert result['raw_quantity_value'] == 100.0
    assert result['quantity_value'] is None
    assert result['quantity_set_name'] == 'BaseQuantities'
    assert result['quantity_selection_method'] == 'quantity_present_unit_unresolved'
    assert 'missing quantity' not in result['issues']
    assert 'unresolved quantity unit' in result['issues']
    assert 'unsupported quantity type' not in result['issues']
    assert result['readiness_status'] == 'missing or unresolved unit'


def test_missing_quantity_is_not_reported_as_unsupported_type():
    element = {
        'global_id': 'missing-quantity', 'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible', 'material_name': 'Concrete',
        'multiple_materials': False, 'quantities': [],
    }

    factors = pd.DataFrame([{
        'material_name': 'Concrete', 'normalised_name': 'concrete',
        'carbon_factor': 0.1, 'unit': 'kgco2e/m3',
        'life_cycle_stage': 'A1-A3', 'source': 'test factor',
    }])

    result = process_element_record(element, factors)

    assert 'missing quantity' in result['issues']
    assert 'missing unit' in result['issues']
    assert 'unsupported quantity type' not in result['issues']
    assert result['readiness_status'] == 'missing quantity'
    assert result['recommended_action'] == 'Export or add an appropriate IFC base quantity for this element.'


def test_extraction_error_path_returns_diagnostic_instead_of_crashing():
    element = {
        'global_id': 'material-error', 'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible', 'material_name': '',
        'material_extraction_error': 'RuntimeError: material boom',
        'multiple_materials': False,
        'quantities': [{
            'name': 'NetVolume', 'type': 'IfcQuantityVolume',
            'value': 1.0, 'unit': 'm3', 'raw_value': 35.3147,
            'raw_unit': 'ft3', 'conversion_factor': 0.028316846592,
        }],
    }

    result = process_element_record(element, pd.DataFrame())

    assert result['material_match_status'] == 'error'
    assert result['calculation_possible'] is False
    assert result['embodied_carbon_kgco2e'] == 0.0
    assert result['readiness_status'] == 'material extraction failed'
    assert result['recommended_action'] == 'Inspect the recorded IFC extraction error and retry the assessment.'
    assert result['issues'] == ['material extraction failed']


def test_quantity_extraction_failure_does_not_claim_quantity_is_missing():
    element = {
        'global_id': 'quantity-error', 'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible', 'material_name': 'Concrete',
        'quantity_extraction_error': 'RuntimeError: quantity boom',
        'multiple_materials': False, 'quantities': [],
    }

    result = process_element_record(element, pd.DataFrame())

    assert result['readiness_status'] == 'quantity extraction failed'
    assert result['issues'] == ['quantity extraction failed']
    assert 'missing quantity' not in result['issues']
    assert 'missing unit' not in result['issues']
    assert 'unsupported quantity type' not in result['issues']


def test_unresolved_unit_gets_unit_specific_recommendation():
    element = {
        'global_id': 'unresolved-recommendation', 'ifc_class': 'IfcWall',
        'scope_status': 'assessment_eligible', 'material_name': 'Concrete',
        'quantities': [{
            'name': 'NetVolume', 'value': None, 'unit': '', 'raw_value': 100.0,
            'raw_unit': '', 'conversion_factor': None, 'unit_source': 'missing',
        }],
    }
    factors = pd.DataFrame([{
        'material_name': 'Concrete', 'normalised_name': 'concrete',
        'carbon_factor': 0.1, 'unit': 'kgco2e/kg', 'density_kg_per_m3': 2300,
        'density_source': 'test density', 'life_cycle_stage': 'A1-A3', 'source': 'test factor',
    }])

    result = process_element_record(element, factors)

    assert result['recommended_action'] == 'Define or repair the IFC project or quantity unit and re-export the model.'
