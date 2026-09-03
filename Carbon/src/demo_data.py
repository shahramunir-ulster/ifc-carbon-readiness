from __future__ import annotations

import pandas as pd


def build_demo_factor_database() -> pd.DataFrame:
    return pd.DataFrame([
        {
            'material_id': 'M001',
            'material_name': 'Concrete',
            'normalised_name': 'concrete',
            'category': 'Concrete',
            'carbon_factor': 0.12,
            'unit': 'kgCO2e/m3',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
        {
            'material_id': 'M002',
            'material_name': 'Steel',
            'normalised_name': 'steel',
            'category': 'Steel',
            'carbon_factor': 1.75,
            'unit': 'kgCO2e/kg',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
        {
            'material_id': 'M003',
            'material_name': 'Brick',
            'normalised_name': 'brick',
            'category': 'Brick',
            'carbon_factor': 0.11,
            'unit': 'kgCO2e/m3',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
        {
            'material_id': 'M004',
            'material_name': 'Timber',
            'normalised_name': 'timber',
            'category': 'Timber',
            'carbon_factor': 0.45,
            'unit': 'kgCO2e/m3',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
        {
            'material_id': 'M005',
            'material_name': 'Glass',
            'normalised_name': 'glass',
            'category': 'Glass',
            'carbon_factor': 1.1,
            'unit': 'kgCO2e/m2',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
        {
            'material_id': 'M006',
            'material_name': 'Plasterboard',
            'normalised_name': 'plasterboard',
            'category': 'Board',
            'carbon_factor': 0.08,
            'unit': 'kgCO2e/m2',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
        {
            'material_id': 'M007',
            'material_name': 'Insulation',
            'normalised_name': 'insulation',
            'category': 'Insulation',
            'carbon_factor': 0.04,
            'unit': 'kgCO2e/m2',
            'life_cycle_stage': 'A1-A3',
            'source': 'Demo placeholder value for prototype testing - replace with verified published factor before formal assessment',
            'source_type': 'Demo',
            'notes': 'Placeholder only',
            'is_demo_value': True,
        },
    ])


def build_demo_element_rows() -> list[dict]:
    return [
        {
            'global_id': '1', 'ifc_class': 'IfcWall', 'element_name': 'External Wall 01', 'storey': 'Level 1',
            'material_name': 'Concrete C30', 'material_normalised': 'concrete', 'material_match_status': 'matched',
            'matched_material_name': 'Concrete', 'quantity_name': 'NetVolume', 'quantity_value': 12.5, 'quantity_unit': 'm3',
            'quantity_supported': True, 'unit_compatible': True, 'carbon_factor': 0.12, 'carbon_factor_unit': 'kgCO2e/m3',
            'calculation_possible': True, 'embodied_carbon_kgco2e': 1.5, 'readiness_status': 'ready / carbon calculated',
            'issues': [], 'recommended_action': 'Use this result as a preliminary estimate only.'
        },
        {
            'global_id': '2', 'ifc_class': 'IfcBeam', 'element_name': 'Steel Beam 02', 'storey': 'Level 1',
            'material_name': 'Steel - structural', 'material_normalised': 'steel', 'material_match_status': 'matched',
            'matched_material_name': 'Steel', 'quantity_name': 'Mass', 'quantity_value': 250, 'quantity_unit': 'kg',
            'quantity_supported': True, 'unit_compatible': True, 'carbon_factor': 1.75, 'carbon_factor_unit': 'kgCO2e/kg',
            'calculation_possible': True, 'embodied_carbon_kgco2e': 437.5, 'readiness_status': 'ready / carbon calculated',
            'issues': [], 'recommended_action': 'Use this result as a preliminary estimate only.'
        },
        {
            'global_id': '3', 'ifc_class': 'IfcSlab', 'element_name': 'Slab 01', 'storey': 'Level 1',
            'material_name': '', 'material_normalised': '', 'material_match_status': 'unmatched',
            'matched_material_name': '', 'quantity_name': 'GrossArea', 'quantity_value': 40, 'quantity_unit': 'm2',
            'quantity_supported': True, 'unit_compatible': True, 'carbon_factor': None, 'carbon_factor_unit': '',
            'calculation_possible': False, 'embodied_carbon_kgco2e': 0.0, 'readiness_status': 'missing material',
            'issues': ['missing material'], 'recommended_action': 'Add material name in BIM model.'
        },
        {
            'global_id': '4', 'ifc_class': 'IfcColumn', 'element_name': 'Column 04', 'storey': 'Level 2',
            'material_name': 'Brick', 'material_normalised': 'brick', 'material_match_status': 'matched',
            'matched_material_name': 'Brick', 'quantity_name': '', 'quantity_value': None, 'quantity_unit': '',
            'quantity_supported': False, 'unit_compatible': True, 'carbon_factor': 0.11, 'carbon_factor_unit': 'kgCO2e/m3',
            'calculation_possible': False, 'embodied_carbon_kgco2e': 0.0, 'readiness_status': 'missing quantity',
            'issues': ['missing quantity'], 'recommended_action': 'Export IFC with base quantities enabled.'
        },
        {
            'global_id': '5', 'ifc_class': 'IfcWindow', 'element_name': 'Window 01', 'storey': 'Level 1',
            'material_name': 'Unknown composite', 'material_normalised': 'unknown composite', 'material_match_status': 'unmatched',
            'matched_material_name': '', 'quantity_name': 'NetArea', 'quantity_value': 3.5, 'quantity_unit': 'm2',
            'quantity_supported': True, 'unit_compatible': True, 'carbon_factor': None, 'carbon_factor_unit': '',
            'calculation_possible': False, 'embodied_carbon_kgco2e': 0.0, 'readiness_status': 'no matching carbon factor',
            'issues': ['unmatched material'], 'recommended_action': 'Add carbon factor for this material or map a synonym.'
        },
        {
            'global_id': '6', 'ifc_class': 'IfcWall', 'element_name': 'Wall 06', 'storey': 'Level 1',
            'material_name': 'Concrete', 'material_normalised': 'concrete', 'material_match_status': 'matched',
            'matched_material_name': 'Concrete', 'quantity_name': 'IncorrectMass', 'quantity_value': 10, 'quantity_unit': 'kg',
            'quantity_supported': True, 'unit_compatible': False, 'carbon_factor': 1.75, 'carbon_factor_unit': 'kgCO2e/kg',
            'calculation_possible': False, 'embodied_carbon_kgco2e': 0.0, 'readiness_status': 'incompatible quantity and carbon-factor units',
            'issues': ['incompatible quantity and carbon-factor units'], 'recommended_action': 'Use a compatible carbon factor or add density conversion logic.'
        },
        {
            'global_id': '7', 'ifc_class': 'IfcElement', 'element_name': '', 'storey': 'Level 1',
            'material_name': 'Concrete', 'material_normalised': 'concrete', 'material_match_status': 'matched',
            'matched_material_name': 'Concrete', 'quantity_name': 'GrossVolume', 'quantity_value': 5, 'quantity_unit': 'm3',
            'quantity_supported': True, 'unit_compatible': True, 'carbon_factor': 0.12, 'carbon_factor_unit': 'kgCO2e/m3',
            'calculation_possible': False, 'embodied_carbon_kgco2e': 0.0, 'readiness_status': 'unclear classification',
            'issues': ['unclear classification'], 'recommended_action': 'Clarify the IFC element classification.'
        },
        {
            'global_id': '8', 'ifc_class': 'IfcWall', 'element_name': 'Layered Wall', 'storey': 'Level 2',
            'material_name': 'Concrete; Insulation; Plasterboard', 'material_normalised': 'concrete insulation plasterboard',
            'material_match_status': 'multiple_materials_review_required', 'matched_material_name': '', 'quantity_name': 'GrossVolume',
            'quantity_value': 8.2, 'quantity_unit': 'm3', 'quantity_supported': True, 'unit_compatible': True,
            'carbon_factor': None, 'carbon_factor_unit': '', 'calculation_possible': False,
            'embodied_carbon_kgco2e': 0.0, 'readiness_status': 'multiple materials require review',
            'issues': ['multiple materials require review'], 'recommended_action': 'Review layered materials and allocate quantities by layer if needed.'
        },
    ]
