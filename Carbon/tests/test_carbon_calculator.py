import math

import pytest

from src.carbon_calculator import calculate_embodied_carbon, select_quantity_for_factor


def test_calculate_embodied_carbon_success():
    result = calculate_embodied_carbon(quantity_value=10, quantity_unit='m3', carbon_factor=0.12, carbon_factor_unit='kgCO2e/m3')
    assert result['calculation_possible'] is True
    assert result['embodied_carbon_kgco2e'] == 1.2


def test_calculate_embodied_carbon_rejects_incompatible_units():
    result = calculate_embodied_carbon(quantity_value=10, quantity_unit='m3', carbon_factor=0.12, carbon_factor_unit='kgCO2e/kg')
    assert result['calculation_possible'] is False
    assert result['failure_code'] == 'missing_or_invalid_density'


def test_calculate_embodied_carbon_converts_volume_using_density():
    result = calculate_embodied_carbon(
        quantity_value=2,
        quantity_unit='m3',
        carbon_factor=0.1,
        carbon_factor_unit='kgCO2e/kg',
        density_kg_per_m3=500,
    )

    assert result['calculation_possible'] is True
    assert result['embodied_carbon_kgco2e'] == 100
    assert result['calculated_mass_kg'] == 1000


@pytest.mark.parametrize('quantity', [0, -2, math.nan, math.inf])
def test_calculation_rejects_invalid_quantities(quantity):
    result = calculate_embodied_carbon(quantity, 'm3', 1, 'kgCO2e/m3')
    assert result['calculation_possible'] is False
    assert result['failure_code'] == 'invalid_quantity'


def test_quantity_selection_is_factor_aware():
    quantities = [
        {'name': 'Volume', 'value': 2, 'unit': 'm3'},
        {'name': 'Mass', 'value': 100, 'unit': 'kg'},
    ]
    selected = select_quantity_for_factor(quantities, 'kgCO2e/kg')
    assert selected['name'] == 'Mass'
    assert selected['selection_method'] == 'direct_factor_unit_match_net_preferred'


def test_net_volume_is_preferred_over_gross_volume():
    quantities = [
        {'name': 'GrossVolume', 'value': 12, 'unit': 'm3'},
        {'name': 'NetVolume', 'value': 10, 'unit': 'm3'},
    ]
    selected = select_quantity_for_factor(quantities, 'kgCO2e/m3')
    assert selected['name'] == 'NetVolume'
    assert selected['value'] == 10


def test_unresolved_compatible_quantity_precedes_valid_incompatible_quantity():
    quantities = [
        {'name': 'Length', 'type': 'IfcQuantityLength', 'value': 10, 'unit': 'm'},
        {'name': 'NetVolume', 'type': 'IfcQuantityVolume', 'value': None, 'unit': '', 'raw_value': 100},
    ]

    selected = select_quantity_for_factor(quantities, 'kgCO2e/kg', density_kg_per_m3=500)

    assert selected['name'] == 'NetVolume'
    assert selected['selection_method'] == 'quantity_present_unit_unresolved'


def test_valid_gross_volume_falls_back_from_invalid_net_volume():
    quantities = [
        {'name': 'NetVolume', 'value': 0, 'unit': 'm3'},
        {'name': 'GrossVolume', 'value': 10, 'unit': 'm3'},
    ]
    selected = select_quantity_for_factor(quantities, 'kgCO2e/m3')
    assert selected['name'] == 'GrossVolume'
    assert selected['value'] == 10


def test_invalid_quantity_is_preserved_when_no_valid_fallback_exists():
    selected = select_quantity_for_factor(
        [{'name': 'NetVolume', 'value': 0, 'unit': 'm3'}], 'kgCO2e/m3'
    )
    assert selected['value'] == 0
    assert selected['selection_method'] == 'invalid_compatible_quantity_for_diagnosis'
    result = calculate_embodied_carbon(selected['value'], selected['unit'], 1, 'kgCO2e/m3')
    assert result['failure_code'] == 'invalid_quantity'


def test_direct_mass_calculation_branch():
    result = calculate_embodied_carbon(100, 'kg', 1.5, 'kgCO2e/kg')
    assert result['calculation_possible'] is True
    assert result['calculated_mass_kg'] == 100
    assert result['embodied_carbon_kgco2e'] == 150


def test_direct_area_calculation_branch():
    result = calculate_embodied_carbon(20, 'm2', 4, 'kgCO2e/m2')
    assert result['calculation_possible'] is True
    assert result['embodied_carbon_kgco2e'] == 80


def test_direct_item_calculation_branch():
    result = calculate_embodied_carbon(3, 'item', 25, 'kgCO2e/item')
    assert result['calculation_possible'] is True
    assert result['embodied_carbon_kgco2e'] == 75
