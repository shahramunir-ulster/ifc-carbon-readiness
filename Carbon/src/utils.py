from __future__ import annotations

import math
from typing import Any


def safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def is_positive_finite_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0


def normalise_life_cycle_stage(stage: Any) -> str:
    text = str(stage or '').strip().upper()
    return text.replace('\N{EN DASH}', '-').replace('\N{EM DASH}', '-').replace(' ', '')


def normalise_unit(unit: Any) -> str:
    if unit is None:
        return ''
    text = str(unit).strip().lower().replace('^', '')
    replacements = {
        'kgco2e/m3': 'kgco2e/m3',
        'kgco2e/m^3': 'kgco2e/m3',
        'kgco2e/m2': 'kgco2e/m2',
        'kgco2e/m^2': 'kgco2e/m2',
        'kgco2e/kg': 'kgco2e/kg',
        'kgco2e/item': 'kgco2e/item',
        'kgco2e / m3': 'kgco2e/m3',
        'kgco2e / m2': 'kgco2e/m2',
        'kgco2e / kg': 'kgco2e/kg',
        'm3': 'm3',
        'm^3': 'm3',
        'm2': 'm2',
        'm^2': 'm2',
        'kg': 'kg',
        'item': 'item',
        'count': 'item',
        'number': 'item',
        'ea': 'item',
    }
    return replacements.get(text, text)
