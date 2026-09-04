from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Dict, List

try:
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.unit
except ImportError:  # pragma: no cover
    ifcopenshell = None


ELIGIBLE_CLASS_ROOTS = (
    'IfcWall', 'IfcSlab', 'IfcBeam', 'IfcColumn', 'IfcDoor', 'IfcWindow', 'IfcRoof',
    'IfcCovering', 'IfcMember', 'IfcPlate', 'IfcFooting', 'IfcPile',
    'IfcReinforcingBar', 'IfcRampFlight', 'IfcStairFlight',
)
REVIEW_CLASS_ROOTS = (
    'IfcBuildingElementProxy', 'IfcCurtainWall', 'IfcRailing', 'IfcRamp', 'IfcStair',
    'IfcElementAssembly',
)
# Retained for demo/backwards compatibility; real IFC classification is inheritance-aware.
SUPPORTED_ELEMENT_CLASSES = {
    'IfcWall', 'IfcWallStandardCase', 'IfcSlab', 'IfcBeam', 'IfcColumn', 'IfcDoor',
    'IfcWindow', 'IfcRoof', 'IfcCovering', 'IfcMember', 'IfcPlate', 'IfcFooting',
    'IfcPile', 'IfcReinforcingBar', 'IfcRampFlight', 'IfcStairFlight',
}

QUANTITY_DEFINITIONS = {
    'VolumeValue': ('m3', 'VOLUMEUNIT', 3),
    'AreaValue': ('m2', 'AREAUNIT', 2),
    'WeightValue': ('kg', 'MASSUNIT', 1),
    'MassValue': ('kg', 'MASSUNIT', 1),
    'CountValue': ('item', None, 0),
    'LengthValue': ('m', 'LENGTHUNIT', 1),
}


def _is_a(element: Any, class_name: str) -> bool:
    try:
        return bool(element.is_a(class_name))
    except (RuntimeError, TypeError, ValueError):
        return False


def _has_element_children(element: Any) -> bool:
    for relation in getattr(element, 'IsDecomposedBy', []) or []:
        if any(_is_a(child, 'IfcElement') for child in (getattr(relation, 'RelatedObjects', []) or [])):
            return True
    return False


def classify_element_scope(element: Any) -> tuple[str, str]:
    """Return assessment status and reason without silently dropping IFC objects."""
    if any(_is_a(element, root) for root in REVIEW_CLASS_ROOTS):
        return 'review_required', 'Ambiguous, composite, or container class; excluded from automatic totals.'
    if any(_is_a(element, root) for root in ELIGIBLE_CLASS_ROOTS):
        if _has_element_children(element):
            return 'review_required', 'Parent element has decomposed child elements; excluded to prevent double counting.'
        return 'assessment_eligible', 'Physical element class included in the defined assessment scope.'
    return 'not_applicable', 'Class is outside the defined automatic embodied-carbon assessment scope.'


def validate_ifc_file(file_path: str | Path) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {'valid': False, 'reason': 'File does not exist.'}
    if path.suffix.lower() != '.ifc':
        return {'valid': False, 'reason': 'Invalid file type. Please upload an .ifc file.'}
    if path.stat().st_size == 0:
        return {'valid': False, 'reason': 'The IFC file is empty.'}
    try:
        file_size = path.stat().st_size
        with path.open('rb') as stream:
            prefix = stream.read(min(file_size, 131_072))
            stream.seek(max(0, file_size - 8_192))
            suffix = stream.read()
    except OSError as exc:
        return {'valid': False, 'reason': f'The IFC file could not be read: {exc}'}

    prefix_text = prefix.decode('utf-8-sig', errors='ignore').lstrip('\x00 \t\r\n').upper()
    suffix_text = suffix.decode('latin-1', errors='ignore').upper()
    if not prefix_text.startswith('ISO-10303-21;'):
        return {'valid': False, 'reason': 'Invalid IFC STEP header: expected ISO-10303-21.'}
    if 'HEADER;' not in prefix_text or 'DATA;' not in prefix_text:
        return {'valid': False, 'reason': 'Invalid IFC structure: HEADER or DATA section is missing.'}
    schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*['\"](IFC[^'\"]+)", prefix_text)
    if not schema_match:
        return {'valid': False, 'reason': 'Invalid IFC header: FILE_SCHEMA declaration is missing.'}
    if 'END-ISO-10303-21;' not in suffix_text:
        return {'valid': False, 'reason': 'Invalid IFC STEP termination marker.'}
    return {'valid': True, 'reason': f'Valid IFC STEP file ({schema_match.group(1)}).'}


def _extract_storey_name(element: Any) -> str:
    for rel in getattr(element, 'ContainedInStructure', []) or []:
        structure = getattr(rel, 'RelatingStructure', None)
        if structure is not None and getattr(structure, 'Name', None):
            return str(structure.Name)
    return ''


def _extract_material_names(element: Any) -> List[str]:
    names: List[str] = []

    def collect(material: Any) -> None:
        if material is None:
            return
        material_type = getattr(material, 'is_a', lambda: '')()
        if material_type == 'IfcMaterial':
            if getattr(material, 'Name', None):
                names.append(str(material.Name))
        elif material_type == 'IfcMaterialLayerSetUsage':
            collect(getattr(material, 'ForLayerSet', None))
        elif material_type == 'IfcMaterialLayerSet':
            for layer in getattr(material, 'MaterialLayers', []) or []:
                collect(getattr(layer, 'Material', None))
        elif material_type == 'IfcMaterialProfileSetUsage':
            collect(getattr(material, 'ForProfileSet', None))
        elif material_type == 'IfcMaterialProfileSet':
            for profile in getattr(material, 'MaterialProfiles', []) or []:
                collect(getattr(profile, 'Material', None))
        elif material_type == 'IfcMaterialConstituentSet':
            for constituent in getattr(material, 'MaterialConstituents', []) or []:
                collect(getattr(constituent, 'Material', None))
        elif material_type == 'IfcMaterialList':
            for item in getattr(material, 'Materials', []) or []:
                collect(item)

    collect(ifcopenshell.util.element.get_material(element, should_skip_usage=True, should_inherit=True))
    return list(dict.fromkeys(name.strip() for name in names if name.strip()))


def _quantity_unit_scale(model: Any, unit: Any, unit_type: str, exponent: int) -> float:
    current_unit = unit
    scale = 1.0
    while current_unit is not None and getattr(current_unit, 'is_a', lambda: '')() == 'IfcConversionBasedUnit':
        conversion = current_unit.ConversionFactor
        scale *= float(conversion.ValueComponent.wrappedValue)
        current_unit = conversion.UnitComponent
    if current_unit is not None and getattr(current_unit, 'is_a', lambda: '')() == 'IfcSIUnit':
        prefix = getattr(current_unit, 'Prefix', None)
        multiplier = ifcopenshell.util.unit.get_prefix_multiplier(prefix) if prefix else 1.0
        if unit_type == 'MASSUNIT':
            return scale * multiplier / 1000.0  # IFC mass SI base is gram; calculator base is kg.
        return scale * multiplier ** exponent
    return float(ifcopenshell.util.unit.calculate_unit_scale(model, unit_type))


def _quantity_unit_symbol(unit: Any) -> str:
    """Return an auditable symbol, including IFC conversion-based units."""
    if unit is None:
        return ''
    if getattr(unit, 'is_a', lambda: '')() == 'IfcConversionBasedUnit':
        name = re.sub(r'\s+', ' ', str(getattr(unit, 'Name', '') or '').strip().upper())
        conversion_symbols = {
            'FOOT': 'ft', 'FEET': 'ft',
            'SQUARE FOOT': 'ft2', 'SQUARE FEET': 'ft2',
            'CUBIC FOOT': 'ft3', 'CUBIC FEET': 'ft3',
            'INCH': 'in', 'INCHES': 'in',
            'SQUARE INCH': 'in2', 'SQUARE INCHES': 'in2',
            'CUBIC INCH': 'in3', 'CUBIC INCHES': 'in3',
        }
        return conversion_symbols.get(name, name.lower() or '?')
    return str(ifcopenshell.util.unit.get_unit_symbol(unit) or '')


def _extract_quantities(element: Any, model: Any) -> List[Dict[str, Any]]:
    quantities: List[Dict[str, Any]] = []
    for rel in getattr(element, 'IsDefinedBy', []) or []:
        prop_def = getattr(rel, 'RelatingPropertyDefinition', None)
        if prop_def is None or getattr(prop_def, 'is_a', lambda: '')() != 'IfcElementQuantity':
            continue
        for quantity in getattr(prop_def, 'Quantities', []) or []:
            for attribute, (si_unit, unit_type, exponent) in QUANTITY_DEFINITIONS.items():
                raw_value = getattr(quantity, attribute, None)
                if raw_value is None:
                    continue
                explicit_unit = getattr(quantity, 'Unit', None)
                resolved_unit = explicit_unit
                if unit_type and resolved_unit is None:
                    resolved_unit = ifcopenshell.util.unit.get_property_unit(quantity, model)
                if unit_type and resolved_unit is None:
                    quantities.append({
                        'name': getattr(quantity, 'Name', '') or '', 'value': None, 'unit': '',
                        'type': quantity.is_a(), 'raw_value': float(raw_value), 'raw_unit': '',
                        'conversion_factor': None, 'unit_source': 'missing',
                        'quantity_set_name': getattr(prop_def, 'Name', '') or '',
                    })
                    break
                scale = 1.0 if unit_type is None else _quantity_unit_scale(model, resolved_unit, unit_type, exponent)
                raw_unit = 'item' if unit_type is None else _quantity_unit_symbol(resolved_unit)
                quantities.append({
                    'name': getattr(quantity, 'Name', '') or '',
                    'value': float(raw_value) * scale,
                    'unit': si_unit,
                    'type': quantity.is_a(),
                    'raw_value': float(raw_value),
                    'raw_unit': raw_unit,
                    'conversion_factor': scale,
                    'unit_source': 'explicit' if explicit_unit is not None else ('count' if unit_type is None else 'project'),
                    'quantity_set_name': getattr(prop_def, 'Name', '') or '',
                })
                break
    return quantities


def parse_ifc_file(file_path: str | Path) -> Dict[str, Any]:
    if ifcopenshell is None:
        raise RuntimeError('IfcOpenShell is not available in this environment.')
    model = ifcopenshell.open(str(Path(file_path)))
    all_elements = list(model.by_type('IfcElement'))
    scope_rows = []
    scope_status_counts: Counter[str] = Counter()
    excluded_counts: Counter[str] = Counter()
    for element in all_elements:
        status, reason = classify_element_scope(element)
        scope_status_counts[status] += 1
        if status != 'assessment_eligible':
            excluded_counts[element.is_a()] += 1
        scope_rows.append({
            'global_id': getattr(element, 'GlobalId', ''),
            'ifc_class': element.is_a(),
            'element_name': getattr(element, 'Name', None) or '',
            'scope_status': status,
            'scope_reason': reason,
        })
    elements: List[Dict[str, Any]] = []
    extraction_error_count = 0
    for element in all_elements:
        scope_status, scope_reason = classify_element_scope(element)
        if scope_status != 'assessment_eligible':
            continue
        material_error = ''
        quantity_error = ''
        try:
            material_names = _extract_material_names(element)
        except Exception as exc:
            material_names = []
            material_error = f'{type(exc).__name__}: {exc}'[:1000]
        try:
            quantities = _extract_quantities(element, model)
        except Exception as exc:
            quantities = []
            quantity_error = f'{type(exc).__name__}: {exc}'[:1000]
        if material_error or quantity_error:
            extraction_error_count += 1
        first = quantities[0] if quantities else {}
        notes = []
        if material_error:
            notes.append(f'Material extraction failed: {material_error}')
        elif not material_names:
            notes.append('Material association not found.')
        if quantity_error:
            notes.append(f'Quantity extraction failed: {quantity_error}')
        elif not quantities:
            notes.append('No quantity set found.')
        elif not any(q.get('value') is not None for q in quantities):
            notes.append('Quantity found, but its IFC unit could not be resolved.')
        elements.append({
            'global_id': getattr(element, 'GlobalId', ''),
            'ifc_class': element.is_a(),
            'element_type': getattr(element, 'PredefinedType', None) or '',
            'element_name': getattr(element, 'Name', None) or '',
            'object_type': getattr(element, 'ObjectType', None) or '',
            'storey': _extract_storey_name(element),
            'material_name': '; '.join(material_names),
            'material_names': material_names,
            'multiple_materials': len(material_names) > 1,
            'quantities': quantities,
            'quantity_name': first.get('name', ''),
            'quantity_set_name': first.get('quantity_set_name', ''),
            'quantity_value': first.get('value'),
            'quantity_unit': first.get('unit', ''),
            'quantity_supported': bool(first.get('unit') in {'m3', 'm2', 'kg', 'item'}),
            'extraction_notes': ' '.join(notes),
            'material_extraction_error': material_error,
            'quantity_extraction_error': quantity_error,
            'extraction_error': ' | '.join(error for error in (material_error, quantity_error) if error),
            'scope_status': scope_status,
            'scope_reason': scope_reason,
        })

    project = model.by_type('IfcProject')
    project_data = project[0] if project else None
    return {
        'elements': elements,
        'metadata': {
            'project_name': getattr(project_data, 'Name', None) or '',
            'project_long_name': getattr(project_data, 'LongName', None) or '',
            'phase': getattr(project_data, 'Phase', None) or '',
        },
        'total_ifc_elements': len(all_elements),
        'in_scope_elements': len(elements),
        'excluded_elements': len(all_elements) - len(elements),
        'review_required_elements': scope_status_counts['review_required'],
        'not_applicable_elements': scope_status_counts['not_applicable'],
        'scope_status_counts': dict(scope_status_counts),
        'scope_report': scope_rows,
        'excluded_class_counts': dict(sorted(excluded_counts.items())),
        'warning_count': sum(bool(e['extraction_notes']) for e in elements),
        'extraction_error_count': extraction_error_count,
        'error_count': extraction_error_count,
    }
