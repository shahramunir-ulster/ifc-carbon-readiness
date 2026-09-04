from __future__ import annotations

import altair as alt
import pandas as pd


def horizontal_bar_chart(
    data: pd.DataFrame,
    category: str,
    value: str,
    value_title: str,
    *,
    color: str = '#0f766e',
) -> alt.Chart:
    """Build a categorical chart without truncated axis labels."""
    row_count = max(len(data), 1)
    return (
        alt.Chart(data)
        .mark_bar(color=color, cornerRadiusEnd=3)
        .encode(
            y=alt.Y(
                f'{category}:N',
                sort='-x',
                title=None,
                axis=alt.Axis(labelLimit=600, labelPadding=8),
            ),
            x=alt.X(f'{value}:Q', title=value_title),
            tooltip=[
                alt.Tooltip(f'{category}:N', title='Category'),
                alt.Tooltip(f'{value}:Q', title=value_title, format=',.2f'),
            ],
        )
        .properties(height=max(220, min(row_count * 38, 700)))
    )
