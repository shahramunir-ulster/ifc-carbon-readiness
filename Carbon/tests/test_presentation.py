from src.presentation import carbon_display_tonnes, carbon_headline


def test_carbon_headline_never_claims_whole_model_total():
    assert carbon_headline(10, 10) == 'calculated A1-A3 carbon - assessment-eligible elements'
    assert carbon_headline(9, 10) == 'Partial calculated A1-A3 carbon - assessment-eligible elements'
    assert 'Total' not in carbon_headline(10, 10)


def test_carbon_display_uses_tonnes():
    assert carbon_display_tonnes(1085622.37) == '1,085.62 tCO2e'
