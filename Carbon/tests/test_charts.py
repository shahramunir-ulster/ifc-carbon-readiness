import pandas as pd

from src.charts import horizontal_bar_chart


def test_horizontal_chart_preserves_long_category_labels():
    chart = horizontal_bar_chart(
        pd.DataFrame([{'issue': 'incompatible quantity and carbon-factor units', 'count': 3}]),
        'issue', 'count', 'Issue occurrences',
    ).to_dict()

    assert chart['encoding']['y']['axis']['labelLimit'] == 600
    assert chart['encoding']['y']['sort'] == '-x'
    assert chart['encoding']['y']['title'] is None
