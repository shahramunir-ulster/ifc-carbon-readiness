import pandas as pd

from src.analytics import aggregate_by_material, issue_breakdown


def test_aggregate_by_material():
    elements = [
        {'material_name': 'Concrete', 'embodied_carbon_kgco2e': 10.0},
        {'material_name': 'Concrete', 'embodied_carbon_kgco2e': 5.0},
        {'material_name': 'Steel', 'embodied_carbon_kgco2e': 20.0},
    ]
    df = aggregate_by_material(elements)
    assert df['matched_material_name'].tolist() == ['Concrete', 'Steel']
    assert df['embodied_carbon_kgco2e'].sum() == 35.0


def test_issue_breakdown():
    elements = [
        {'issues': ['missing material', 'missing quantity']},
        {'issues': ['missing material']},
    ]
    df = issue_breakdown(elements)
    assert 'missing material' in df['issue'].values
    assert df['count'].sum() == 3
