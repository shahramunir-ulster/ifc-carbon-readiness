from src.analytics import aggregate_by_material, top_carbon_elements


def test_material_chart_groups_by_controlled_factor_category():
    rows = [
        {'material_name': 'Steel Rusted', 'matched_material_name': 'Steel', 'factor_category': 'Steel', 'calculation_possible': True, 'embodied_carbon_kgco2e': 10},
        {'material_name': 'Steel Paint', 'matched_material_name': 'Steel', 'factor_category': 'Steel', 'calculation_possible': True, 'embodied_carbon_kgco2e': 20},
        {'material_name': 'Unknown', 'matched_material_name': '', 'factor_category': '', 'calculation_possible': False, 'embodied_carbon_kgco2e': 0},
    ]
    chart = aggregate_by_material(rows)
    assert chart.to_dict(orient='records') == [{'matched_material_name': 'Steel', 'embodied_carbon_kgco2e': 30}]


def test_top_carbon_elements_returns_highest_ten_calculated_rows():
    rows = [{
        'global_id': str(index), 'ifc_class': 'IfcBeam', 'element_name': f'Beam {index}',
        'storey': 'Level 1', 'matched_material_name': 'Steel',
        'calculation_possible': True, 'embodied_carbon_kgco2e': float(index),
    } for index in range(12)]
    hotspots = top_carbon_elements(rows)
    assert len(hotspots) == 10
    assert hotspots.iloc[0]['global_id'] == '11'
    assert hotspots.iloc[-1]['global_id'] == '2'
