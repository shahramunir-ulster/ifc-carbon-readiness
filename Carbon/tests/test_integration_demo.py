from src.demo_data import build_demo_element_rows, build_demo_factor_database
from src.material_normaliser import normalise_material_name
from src.carbon_factors import match_material_to_factor


def test_demo_data_workflow():
    elements = build_demo_element_rows()
    factors = build_demo_factor_database().to_dict(orient='records')
    assert len(elements) >= 8
    assert match_material_to_factor('Concrete C30', factors)['matched'] is True
    assert normalise_material_name('Steel - structural') == 'steel'
