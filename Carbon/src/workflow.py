from __future__ import annotations

from io import StringIO
from pathlib import Path
import tempfile

import pandas as pd

from src.assessment import process_element_record
from src.carbon_factors import load_carbon_factor_csv
from src.data_readiness import build_processing_error_record
from src.ifc_parser import parse_ifc_file, validate_ifc_file


def assess_ifc_bytes(ifc_bytes: bytes, factor_bytes: bytes) -> dict:
    """Run one complete live assessment and return cache/session-safe results."""
    factor_df = load_carbon_factor_csv(StringIO(factor_bytes.decode('utf-8-sig')))
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as temporary_file:
            temporary_file.write(ifc_bytes)
            temporary_path = Path(temporary_file.name)
        validation = validate_ifc_file(temporary_path)
        if not validation['valid']:
            raise ValueError(validation['reason'])
        scope = parse_ifc_file(temporary_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    elements = []
    processing_error_count = 0
    for source in scope['elements']:
        item = source.copy()
        try:
            elements.append(process_element_record(item, factor_df))
        except Exception as exc:
            elements.append(build_processing_error_record(item, exc))
            processing_error_count += 1
    scope['processing_error_count'] = processing_error_count
    return {'elements': elements, 'factor_df': factor_df, 'assessment_scope': scope}
