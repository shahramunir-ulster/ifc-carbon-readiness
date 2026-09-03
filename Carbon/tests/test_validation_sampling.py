from scripts.run_snowdon_validation import choose_sample


def test_validation_sample_includes_every_contributing_material_first():
    rows = []
    for index, material in enumerate(('Concrete', 'Steel', 'Steel Deck')):
        rows.append({
            'model': 'Structural', 'global_id': str(index), 'ifc_class': 'IfcBeam',
            'material_normalised': material.lower(), 'matched_material_name': material,
            'embodied_carbon_kgco2e': 10 + index,
        })
    rows.extend({
        'model': 'Architectural', 'global_id': f'extra-{index}', 'ifc_class': 'IfcWall',
        'material_normalised': 'concrete', 'matched_material_name': 'Concrete',
        'embodied_carbon_kgco2e': 1,
    } for index in range(5))

    sample = choose_sample(rows, limit=3)

    assert {row['matched_material_name'] for row in sample} == {'Concrete', 'Steel', 'Steel Deck'}
