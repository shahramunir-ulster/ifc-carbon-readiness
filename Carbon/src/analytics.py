from __future__ import annotations

from typing import Dict, List

import pandas as pd


def aggregate_by_material(elements: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(elements)
    if df.empty:
        return pd.DataFrame(columns=['matched_material_name', 'embodied_carbon_kgco2e'])
    if 'calculation_possible' in df.columns:
        df = df[df['calculation_possible'].fillna(False).astype(bool)].copy()
    if df.empty:
        return pd.DataFrame(columns=['matched_material_name', 'embodied_carbon_kgco2e'])
    labels = df.get('factor_category', pd.Series('', index=df.index)).fillna('').astype(str).str.strip()
    matched = df.get('matched_material_name', pd.Series('', index=df.index)).fillna('').astype(str).str.strip()
    original = df.get('material_name', pd.Series('', index=df.index)).fillna('').astype(str).str.strip()
    matched = matched.where(matched.ne(''), original)
    df['matched_material_name'] = labels.where(labels.ne(''), matched).replace('', 'Unclassified factor')
    out = df.groupby('matched_material_name', dropna=False)['embodied_carbon_kgco2e'].sum().reset_index()
    out = out.sort_values('embodied_carbon_kgco2e', ascending=True)
    return out.reset_index(drop=True)


def top_carbon_elements(elements: List[Dict], limit: int = 10) -> pd.DataFrame:
    columns = [
        'global_id', 'ifc_class', 'element_name', 'storey',
        'matched_material_name', 'embodied_carbon_kgco2e',
    ]
    df = pd.DataFrame(elements)
    if df.empty or 'calculation_possible' not in df.columns:
        return pd.DataFrame(columns=columns)
    calculated = df[df['calculation_possible'].fillna(False).astype(bool)].copy()
    for column in columns:
        if column not in calculated.columns:
            calculated[column] = ''
    return (
        calculated[columns]
        .sort_values('embodied_carbon_kgco2e', ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def aggregate_by_type(elements: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(elements)
    if df.empty:
        return pd.DataFrame(columns=['ifc_class', 'embodied_carbon_kgco2e'])
    out = df.groupby('ifc_class', dropna=False)['embodied_carbon_kgco2e'].sum().reset_index()
    out = out.sort_values('embodied_carbon_kgco2e', ascending=True)
    return out.reset_index(drop=True)


def aggregate_by_storey(elements: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(elements)
    if df.empty:
        return pd.DataFrame(columns=['storey', 'embodied_carbon_kgco2e'])
    out = df.groupby('storey', dropna=False)['embodied_carbon_kgco2e'].sum().reset_index()
    out = out.sort_values('embodied_carbon_kgco2e', ascending=True)
    return out.reset_index(drop=True)


def issue_breakdown(elements: List[Dict]) -> pd.DataFrame:
    rows = []
    for element in elements:
        for issue in element.get('issues', []):
            rows.append({'issue': issue})
    if not rows:
        return pd.DataFrame(columns=['issue', 'count'])
    out = pd.DataFrame(rows)
    counts = out['issue'].value_counts().reset_index()
    counts.columns = ['issue', 'count']
    return counts.reset_index(drop=True)
