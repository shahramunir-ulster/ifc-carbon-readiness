from pathlib import Path


def test_dashboard_avoids_narrow_six_card_rows_and_metric_ellipsis():
    source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
    assert 'st.columns(6)' not in source
    assert 'carbon_metric_top = st.columns(3)' in source
    assert 'carbon_metric_bottom = st.columns(3)' in source
    assert 'white-space: normal !important' in source
    assert 'text-overflow: clip !important' in source


def test_dashboard_uses_full_label_charts_instead_of_default_bar_chart():
    source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
    assert 'st.bar_chart' not in source
    assert "horizontal_bar_chart(issue_df, 'issue', 'count'" in source
