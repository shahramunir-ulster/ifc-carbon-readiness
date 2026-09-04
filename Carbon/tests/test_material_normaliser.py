from src.material_normaliser import is_placeholder_material_name, normalise_material_name


def test_material_normaliser_basic_variants():
    assert normalise_material_name('Concrete C30') == 'concrete'
    assert normalise_material_name(' CONC ') == 'concrete'
    assert normalise_material_name('Cast-in-place concrete') == 'concrete'
    assert normalise_material_name('Steel - structural') == 'steel'
    assert normalise_material_name('Plaster board') == 'plasterboard'


def test_material_normaliser_handles_unknowns():
    assert normalise_material_name('Custom composite') == 'custom composite'


def test_snowdon_materials_are_handled_conservatively():
    assert normalise_material_name('Gypsum Wall Board') == 'plasterboard'
    assert normalise_material_name('CMU, Split Face') == 'concrete masonry unit'
    assert normalise_material_name('Concrete Masonry Units') == 'concrete masonry unit'
    assert normalise_material_name('Metal Deck') == 'steel deck'
    assert normalise_material_name('Rebar, ASTM A615, Grade 60') == 'reinforcement steel'
    assert normalise_material_name('Concrete Masonry Units') != 'concrete'


def test_placeholder_materials_are_invalid():
    for value in ('<Unnamed>', 'Default', 'Default Wall'):
        assert is_placeholder_material_name(value)
        assert normalise_material_name(value) == ''


def test_material_normaliser_handles_real_world_and_multilingual_names():
    assert normalise_material_name('Metal - Steel - 345 MPa') == 'steel'
    assert normalise_material_name('CL Concrete_ panels') == 'concrete'
    assert normalise_material_name('Stahlbeton 65690') == 'concrete'
    assert normalise_material_name('Holz') == 'timber'
    assert normalise_material_name('玻璃') == 'glass'
    assert normalise_material_name('Aluminum') == 'aluminium'
    assert normalise_material_name('Metal Stud Layer') == 'steel'
