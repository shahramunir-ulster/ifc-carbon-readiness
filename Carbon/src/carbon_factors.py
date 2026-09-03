from __future__ import annotations

import csv
from io import TextIOBase
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd

from src.material_normaliser import is_placeholder_material_name, normalise_material_name
from src.utils import is_positive_finite_number, normalise_life_cycle_stage, normalise_unit, safe_float


ALLOWED_FACTOR_UNITS = {'kgco2e/kg', 'kgco2e/m3', 'kgco2e/m2', 'kgco2e/item'}
REQUIRED_FACTOR_COLUMNS = {'material_name', 'carbon_factor', 'unit', 'life_cycle_stage', 'source'}


def load_carbon_factor_csv(path: str | Path | TextIOBase) -> pd.DataFrame:
    if hasattr(path, 'read'):
        source = path
        source_name = 'uploaded carbon factor CSV'
        should_close = False
    else:
        csv_path = Path(path)
        if not csv_path.exists():
            raise FileNotFoundError(f'Carbon factor file not found: {csv_path}')
        source = csv_path.open('r', encoding='utf-8-sig', newline='')
        source_name = str(csv_path)
        should_close = True

    rows: list[Dict[str, Any]] = []
    errors: list[str] = []
    try:
        reader = csv.DictReader(source)
        missing = REQUIRED_FACTOR_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'{source_name} is missing required columns: {", ".join(sorted(missing))}')

        for line_number, row in enumerate(reader, start=2):
            if not row or not any(str(value or '').strip() for value in row.values()):
                continue
            material_name = str(row.get('material_name') or '').strip()
            factor = safe_float(row.get('carbon_factor'))
            factor_unit = normalise_unit(row.get('unit'))
            stage = normalise_life_cycle_stage(row.get('life_cycle_stage'))
            source_reference = str(row.get('source') or '').strip()
            density_text = str(row.get('density_kg_per_m3') or '').strip()
            density = safe_float(density_text) if density_text else None
            density_source = str(row.get('density_source') or '').strip()
            is_demo_value = str(row.get('is_demo_value') or '').strip().lower() in {'true', '1', 'yes', 'y'}

            row_errors = []
            if not material_name:
                row_errors.append('material_name is empty')
            elif is_placeholder_material_name(material_name):
                row_errors.append('material_name is a placeholder')
            if not is_positive_finite_number(factor):
                row_errors.append('carbon_factor must be positive and finite')
            if factor_unit not in ALLOWED_FACTOR_UNITS:
                row_errors.append(f'unit must be one of {sorted(ALLOWED_FACTOR_UNITS)}')
            if stage != 'A1-A3':
                row_errors.append('life_cycle_stage must be A1-A3')
            if not source_reference:
                row_errors.append('source is empty')
            if density_text and not is_positive_finite_number(density):
                row_errors.append('density_kg_per_m3 must be positive and finite when supplied')
            if density_text and not density_source:
                row_errors.append('density_source is required when density_kg_per_m3 is supplied')
            if is_demo_value:
                row_errors.append('demo/placeholder factors cannot be used for a live IFC assessment')
            if row_errors:
                errors.append(f'row {line_number}: {"; ".join(row_errors)}')
                continue

            rows.append({
                'material_id': str(row.get('material_id') or '').strip(),
                'material_name': material_name,
                'normalised_name': normalise_material_name(row.get('normalised_name') or material_name),
                'category': str(row.get('category') or '').strip(),
                'carbon_factor': float(factor),
                'unit': factor_unit,
                'density_kg_per_m3': float(density) if density is not None else None,
                'density_source': density_source,
                'life_cycle_stage': 'A1-A3',
                'source': source_reference,
                'source_type': str(row.get('source_type') or 'User supplied').strip(),
                'notes': str(row.get('notes') or '').strip(),
                'is_demo_value': False,
            })
    finally:
        if should_close:
            source.close()

    if errors:
        preview = ' | '.join(errors[:8])
        suffix = f' | plus {len(errors) - 8} more error(s)' if len(errors) > 8 else ''
        raise ValueError(f'Invalid factor CSV: {preview}{suffix}')
    if not rows:
        raise ValueError('The factor CSV contains no valid A1-A3 factor rows.')
    duplicate_names = pd.Series([row['normalised_name'] for row in rows]).value_counts()
    duplicate_names = duplicate_names[duplicate_names > 1].index.tolist()
    if duplicate_names:
        raise ValueError(
            'The factor CSV contains ambiguous duplicate normalised material names: '
            + ', '.join(duplicate_names)
        )
    return pd.DataFrame(rows)


def _empty_match(method: str, reason: str) -> Dict[str, Any]:
    return {
        'matched': False,
        'matching_method': method,
        'matching_confidence': 'none',
        'matched_material_name': '',
        'carbon_factor': None,
        'carbon_factor_unit': '',
        'density_kg_per_m3': None,
        'density_source': '',
        'life_cycle_stage': '',
        'carbon_factor_source': '',
        'carbon_factor_source_type': '',
        'carbon_factor_is_demo': False,
        'material_id': '',
        'factor_category': '',
        'factor_notes': '',
        'factor_is_proxy': False,
        'reason': reason,
    }


def match_material_to_factor(material_name: str, factor_rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    material_parts = [part.strip() for part in str(material_name or '').split(';') if part.strip()]
    if len(material_parts) > 1:
        return _empty_match('multiple_materials', 'Multiple materials require layer-specific quantities')
    if is_placeholder_material_name(material_name):
        return _empty_match('invalid_placeholder', 'Placeholder or unnamed material is not valid for factor matching')
    target = normalise_material_name(material_name)
    if not target:
        return _empty_match('none', 'Missing material name')

    for row in factor_rows:
        candidate = normalise_material_name(row.get('normalised_name') or row.get('material_name') or '')
        if candidate == target:
            factor_notes = str(row.get('notes') or '').strip()
            return {
                'matched': True,
                'matching_method': 'exact_normalised_match',
                'matching_confidence': 'controlled_exact',
                'matched_material_name': row.get('material_name', ''),
                'carbon_factor': safe_float(row.get('carbon_factor')),
                'carbon_factor_unit': normalise_unit(row.get('unit')),
                'density_kg_per_m3': safe_float(row.get('density_kg_per_m3')),
                'density_source': row.get('density_source', ''),
                'life_cycle_stage': normalise_life_cycle_stage(row.get('life_cycle_stage')),
                'carbon_factor_source': row.get('source', ''),
                'carbon_factor_source_type': row.get('source_type', ''),
                'carbon_factor_is_demo': bool(row.get('is_demo_value', False)),
                'material_id': row.get('material_id', ''),
                'factor_category': row.get('category', ''),
                'factor_notes': factor_notes,
                'factor_is_proxy': any(word in factor_notes.lower() for word in ('proxy', 'assumption', 'assumes')),
                'reason': 'Exact normalised material match',
            }
    return _empty_match('unmatched', f'No carbon factor matched normalised material: {target}')
