from io import StringIO

import pytest

from src.carbon_factors import load_carbon_factor_csv, match_material_to_factor
from src.demo_data import build_demo_factor_database


def test_factor_csv_loads_valid_a1_a3_data():
    csv_data = StringIO(
        'material_name,carbon_factor,unit,life_cycle_stage,source,density_kg_per_m3\n'
        'Concrete,250,kgCO2e/m3,A1-A3,Verified EPD,\n'
    )
    df = load_carbon_factor_csv(csv_data)
    assert df.iloc[0]['carbon_factor'] == 250
    assert df.iloc[0]['life_cycle_stage'] == 'A1-A3'


@pytest.mark.parametrize('row', [
    'Concrete,-1,kgCO2e/m3,A1-A3,EPD',
    'Concrete,nan,kgCO2e/m3,A1-A3,EPD',
    'Concrete,1,kgCO2e/m3,A1-A5,EPD',
    'Concrete,1,unknown,A1-A3,EPD',
])
def test_factor_csv_rejects_invalid_rows(row):
    csv_data = StringIO('material_name,carbon_factor,unit,life_cycle_stage,source\n' + row + '\n')
    with pytest.raises(ValueError, match='Invalid factor CSV'):
        load_carbon_factor_csv(csv_data)


def test_factor_csv_requires_lifecycle_stage():
    csv_data = StringIO('material_name,carbon_factor,unit,source\nConcrete,1,kgCO2e/m3,EPD\n')
    with pytest.raises(ValueError, match='life_cycle_stage'):
        load_carbon_factor_csv(csv_data)


def test_factor_csv_rejects_ambiguous_duplicate_materials():
    csv_data = StringIO(
        'material_name,carbon_factor,unit,life_cycle_stage,source\n'
        'Concrete C30,1,kgCO2e/m3,A1-A3,EPD one\n'
        'Concrete,2,kgCO2e/m3,A1-A3,EPD two\n'
    )
    with pytest.raises(ValueError, match='duplicate normalised'):
        load_carbon_factor_csv(csv_data)


def test_matching_concrete_exact_and_preserves_provenance():
    factors = build_demo_factor_database().to_dict(orient='records')
    result = match_material_to_factor('Concrete C30', factors)
    assert result['matched'] is True
    assert result['matched_material_name'] == 'Concrete'
    assert result['life_cycle_stage'] == 'A1-A3'
    assert result['carbon_factor_source']


def test_matching_rejects_multiple_materials_without_layer_quantities():
    factors = build_demo_factor_database().to_dict(orient='records')
    result = match_material_to_factor('Concrete; Insulation', factors)
    assert result['matched'] is False
    assert result['matching_method'] == 'multiple_materials'


def test_matching_rejects_placeholder_material():
    result = match_material_to_factor('Default Wall', build_demo_factor_database().to_dict(orient='records'))
    assert result['matched'] is False
    assert result['matching_method'] == 'invalid_placeholder'


def test_density_requires_a_source():
    csv_data = StringIO(
        'material_name,carbon_factor,unit,density_kg_per_m3,life_cycle_stage,source\n'
        'Concrete,0.1,kgCO2e/kg,2300,A1-A3,EPD\n'
    )
    with pytest.raises(ValueError, match='density_source'):
        load_carbon_factor_csv(csv_data)


def test_factor_csv_rejects_placeholder_material_row():
    csv_data = StringIO(
        'material_name,carbon_factor,unit,life_cycle_stage,source\n'
        'Default,1,kgCO2e/kg,A1-A3,EPD\n'
    )
    with pytest.raises(ValueError, match='placeholder'):
        load_carbon_factor_csv(csv_data)


def test_uploaded_factor_csv_rejects_demo_values():
    csv_data = StringIO(
        'material_name,carbon_factor,unit,life_cycle_stage,source,is_demo_value\n'
        'Concrete,1,kgCO2e/m3,A1-A3,Placeholder,true\n'
    )
    with pytest.raises(ValueError, match='demo/placeholder factors'):
        load_carbon_factor_csv(csv_data)


def test_match_propagates_factor_identity_category_notes_and_proxy_flag():
    factors = [{
        'material_id': 'C-01', 'material_name': 'Concrete',
        'normalised_name': 'concrete', 'category': 'Concrete',
        'carbon_factor': 0.1, 'unit': 'kgCO2e/kg',
        'density_kg_per_m3': 2300, 'density_source': 'density source',
        'life_cycle_stage': 'A1-A3', 'source': 'factor source',
        'source_type': 'controlled', 'notes': 'Generic proxy for unspecified mixes.',
    }]
    result = match_material_to_factor('Concrete, Precast Smooth, Light Grey', factors)
    assert result['matched'] is True
    assert result['material_id'] == 'C-01'
    assert result['factor_category'] == 'Concrete'
    assert result['factor_notes'] == 'Generic proxy for unspecified mixes.'
    assert result['factor_is_proxy'] is True
