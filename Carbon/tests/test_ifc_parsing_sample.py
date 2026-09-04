import pytest

import src.ifc_parser as ifc_parser

from src.ifc_parser import parse_ifc_file, validate_ifc_file


MINIMAL_IFC = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('','2026-08-15T23:47:39',(''),(''),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#21=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#22=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#23=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#24=IFCSIUNIT(*,.MASSUNIT.,.KILO.,.GRAM.);
#1=IFCUNITASSIGNMENT((#21,#22,#23,#24));
#2=IFCCARTESIANPOINT((0.,0.,0.));
#3=IFCDIRECTION((0.,0.,1.));
#4=IFCDIRECTION((1.,0.,0.));
#5=IFCAXIS2PLACEMENT3D(#2,#3,#4);
#6=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#5,$);
#7=IFCPROJECT('proj1',$,'DemoProject',$,$,'Demo Project',$,(#6),#1);
#8=IFCSITE('site1',$,'Site',$,$,$,$,$,$,$,$,$,$,$);
#9=IFCBUILDING('bld1',$,'Building',$,$,$,$,$,$,$,$,$);
#10=IFCBUILDINGSTOREY('lvl1',$,'Level 1',$,$,$,$,$,$,$);
#11=IFCRELAGGREGATES('rel1',$,$,$,#7,(#8));
#12=IFCRELAGGREGATES('rel2',$,$,$,#8,(#9));
#13=IFCRELAGGREGATES('rel3',$,$,$,#9,(#10));
#14=IFCMATERIAL('Concrete',$,$);
#15=IFCWALL('wall1',$,'External Wall',$,$,$,$,$,$);
#16=IFCRELASSOCIATESMATERIAL('mat1',$,$,$,(#15),#14);
#17=IFCQUANTITYVOLUME('NetVolume',$,$,12.5,$);
#18=IFCELEMENTQUANTITY('qto1',$,'Qto_Wall',$,$,(#17));
#19=IFCRELDEFINESBYPROPERTIES('def1',$,$,$,(#15),#18);
#20=IFCRELCONTAINEDINSPATIALSTRUCTURE('contain1',$,$,$,(#15),#10);
ENDSEC;
END-ISO-10303-21;
"""


def test_ifc_content_validation_accepts_a_valid_step_file(tmp_path):
    sample_path = tmp_path / 'valid.ifc'
    sample_path.write_text(MINIMAL_IFC, encoding='utf-8')
    result = validate_ifc_file(sample_path)
    assert result['valid'] is True
    assert 'IFC4' in result['reason']


def test_ifc_content_validation_rejects_plain_text_with_ifc_extension(tmp_path):
    sample_path = tmp_path / 'fake.ifc'
    sample_path.write_text('This is not an IFC file.', encoding='utf-8')
    result = validate_ifc_file(sample_path)
    assert result['valid'] is False
    assert 'STEP header' in result['reason']


def test_ifc_content_validation_rejects_missing_schema_or_terminator(tmp_path):
    missing_schema = tmp_path / 'missing_schema.ifc'
    missing_schema.write_text('ISO-10303-21;\nHEADER;\nDATA;\nEND-ISO-10303-21;', encoding='utf-8')
    assert validate_ifc_file(missing_schema)['valid'] is False

    missing_end = tmp_path / 'missing_end.ifc'
    missing_end.write_text("ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nDATA;", encoding='utf-8')
    assert validate_ifc_file(missing_end)['valid'] is False


def test_ifc_parser_extracts_material_quantity_and_storey(tmp_path):
    sample_path = tmp_path / 'minimal.ifc'
    sample_path.write_text(MINIMAL_IFC, encoding='utf-8')

    parsed = parse_ifc_file(sample_path)
    wall = parsed['elements'][0]

    assert wall['ifc_class'] == 'IfcWall'
    assert wall['material_name'] == 'Concrete'
    assert wall['quantity_value'] == 12.5
    assert wall['quantity_unit'] == 'm3'
    assert wall['quantities'][0]['raw_unit'] == 'm3'
    assert wall['quantities'][0]['conversion_factor'] == 1.0
    assert wall['quantities'][0]['quantity_set_name'] == 'Qto_Wall'
    assert wall['quantity_set_name'] == 'Qto_Wall'
    assert wall['storey'] == 'Level 1'
    assert parsed['total_ifc_elements'] == 1
    assert parsed['excluded_elements'] == 0
    assert 'model' not in parsed


def test_ifc_parser_retains_element_when_material_extraction_fails(tmp_path, monkeypatch):
    sample_path = tmp_path / 'material_error.ifc'
    sample_path.write_text(MINIMAL_IFC, encoding='utf-8')
    monkeypatch.setattr(ifc_parser, '_extract_material_names', lambda element: (_ for _ in ()).throw(RuntimeError('material boom')))

    parsed = parse_ifc_file(sample_path)
    wall = parsed['elements'][0]

    assert parsed['error_count'] == 1
    assert wall['material_name'] == ''
    assert wall['material_extraction_error'] == 'RuntimeError: material boom'
    assert wall['quantity_value'] == 12.5


def test_ifc_parser_retains_element_when_quantity_extraction_fails(tmp_path, monkeypatch):
    sample_path = tmp_path / 'quantity_error.ifc'
    sample_path.write_text(MINIMAL_IFC, encoding='utf-8')
    monkeypatch.setattr(ifc_parser, '_extract_quantities', lambda element, model: (_ for _ in ()).throw(RuntimeError('quantity boom')))

    parsed = parse_ifc_file(sample_path)
    wall = parsed['elements'][0]

    assert parsed['error_count'] == 1
    assert wall['material_name'] == 'Concrete'
    assert wall['quantity_extraction_error'] == 'RuntimeError: quantity boom'
    assert wall['quantities'] == []


def test_ifc_parser_converts_declared_volume_unit_to_cubic_metres(tmp_path):
    millimetre_model = MINIMAL_IFC.replace(
        'IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.)',
        'IFCSIUNIT(*,.VOLUMEUNIT.,.MILLI.,.CUBIC_METRE.)',
    ).replace('12.5,$);', '12500000000.,$);')
    sample_path = tmp_path / 'millimetres.ifc'
    sample_path.write_text(millimetre_model, encoding='utf-8')

    quantity = parse_ifc_file(sample_path)['elements'][0]['quantities'][0]
    assert quantity['raw_value'] == 12500000000.0
    assert quantity['conversion_factor'] == 1e-9
    assert quantity['value'] == 12.5


def test_ifc_wall_standard_case_is_eligible_via_inheritance(tmp_path):
    model_text = MINIMAL_IFC.replace('IFCWALL(', 'IFCWALLSTANDARDCASE(')
    sample_path = tmp_path / 'wall_standard_case.ifc'
    sample_path.write_text(model_text, encoding='utf-8')
    parsed = parse_ifc_file(sample_path)
    assert len(parsed['elements']) == 1
    assert parsed['elements'][0]['ifc_class'] == 'IfcWallStandardCase'
    assert parsed['scope_status_counts']['assessment_eligible'] == 1


def test_building_element_proxy_is_review_required_not_eligible(tmp_path):
    model_text = MINIMAL_IFC.replace('IFCWALL(', 'IFCBUILDINGELEMENTPROXY(')
    sample_path = tmp_path / 'proxy.ifc'
    sample_path.write_text(model_text, encoding='utf-8')
    parsed = parse_ifc_file(sample_path)
    assert parsed['elements'] == []
    assert parsed['review_required_elements'] == 1
    assert parsed['scope_report'][0]['scope_status'] == 'review_required'


def test_decomposed_parent_is_excluded_to_prevent_double_counting(tmp_path):
    child_and_relationship = """#31=IFCWALL('wall2',$,'Child Wall',$,$,$,$,$,$);
#32=IFCRELAGGREGATES('rel4',$,$,$,#15,(#31));"""
    model_text = MINIMAL_IFC.replace('ENDSEC;\nEND-ISO-10303-21;', child_and_relationship + '\nENDSEC;\nEND-ISO-10303-21;')
    sample_path = tmp_path / 'decomposed.ifc'
    sample_path.write_text(model_text, encoding='utf-8')
    parsed = parse_ifc_file(sample_path)
    assert parsed['total_ifc_elements'] == 2
    assert parsed['in_scope_elements'] == 1
    assert parsed['review_required_elements'] == 1
    parent_scope = next(row for row in parsed['scope_report'] if row['global_id'] == 'wall1')
    assert 'double counting' in parent_scope['scope_reason']


def test_ifc_parser_converts_cubic_feet_to_cubic_metres(tmp_path):
    foot_volume_unit = """#25=IFCDIMENSIONALEXPONENTS(3,0,0,0,0,0,0);
#26=IFCMEASUREWITHUNIT(IFCVOLUMEMEASURE(0.028316846592),#27);
#27=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#23=IFCCONVERSIONBASEDUNIT(#25,.VOLUMEUNIT.,'CUBIC FOOT',#26);"""
    model_text = MINIMAL_IFC.replace(
        '#23=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);', foot_volume_unit
    ).replace('12.5,$);', '645.1852,$);')
    sample_path = tmp_path / 'feet.ifc'
    sample_path.write_text(model_text, encoding='utf-8')
    quantity = parse_ifc_file(sample_path)['elements'][0]['quantities'][0]
    assert quantity['raw_value'] == 645.1852
    assert quantity['raw_unit'] == 'ft3'
    assert quantity['conversion_factor'] == 0.028316846592
    assert quantity['value'] == pytest.approx(18.2696103318)


def test_ifc_parser_converts_square_feet_to_square_metres(tmp_path):
    foot_area_unit = """#28=IFCDIMENSIONALEXPONENTS(2,0,0,0,0,0,0);
#29=IFCMEASUREWITHUNIT(IFCAREAMEASURE(0.09290304),#30);
#30=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#22=IFCCONVERSIONBASEDUNIT(#28,.AREAUNIT.,'SQUARE FOOT',#29);"""
    model_text = MINIMAL_IFC.replace(
        '#22=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);', foot_area_unit
    ).replace("IFCQUANTITYVOLUME('NetVolume',$,$,12.5,$)", "IFCQUANTITYAREA('NetArea',$,$,100.,$)")
    sample_path = tmp_path / 'square_feet.ifc'
    sample_path.write_text(model_text, encoding='utf-8')
    quantity = parse_ifc_file(sample_path)['elements'][0]['quantities'][0]
    assert quantity['raw_value'] == 100
    assert quantity['raw_unit'] == 'ft2'
    assert quantity['conversion_factor'] == 0.09290304
    assert quantity['value'] == pytest.approx(9.290304)
