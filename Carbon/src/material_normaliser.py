from __future__ import annotations

import re


SYNONYMS = {
    'conc': 'concrete',
    'concrete c30': 'concrete',
    'cast in place concrete': 'concrete',
    'cast-in-place concrete': 'concrete',
    'reinforced concrete': 'concrete',
    'in situ concrete': 'concrete',
    'steel structural': 'steel',
    'structural steel': 'steel',
    'steel - structural': 'steel',
    'steel - mild': 'steel',
    'plasterboard': 'plasterboard',
    'plaster board': 'plasterboard',
    'gypsum board': 'plasterboard',
    'gypsum wall board': 'plasterboard',
    'insulation': 'insulation',
    'glass': 'glass',
    'timber': 'timber',
    'wood': 'timber',
    'brick': 'brick',
    'stone sand lime': 'brick',
    'stone sand-lime': 'brick',
    'sand-lime brick': 'brick',
    'blockwork': 'blockwork',
    'masonry block': 'blockwork',
    'concrete block': 'blockwork',
    'concrete masonry units': 'concrete masonry unit',
    'concrete masonry unit': 'concrete masonry unit',
    'cmu': 'concrete masonry unit',
    'cmu, split face': 'concrete masonry unit',
    'metal deck': 'steel deck',
    'steel deck': 'steel deck',
    'rebar': 'reinforcement steel',
    'reinforcing steel': 'reinforcement steel',
    'reinforcement steel': 'reinforcement steel',
    'rebar, astm a615, grade 60': 'reinforcement steel',
    'holz': 'timber',
    'stahlbeton': 'concrete',
    'glas': 'glass',
    '玻璃': 'glass',
    'aluminum': 'aluminium',
    'aluminium': 'aluminium',
    'metal stud layer': 'steel',
}


KEYWORD_PATTERNS = (
    (('concrete masonry', 'masonry unit', 'cmu'), 'concrete masonry unit'),
    (('reinforcement steel', 'reinforcing steel', 'rebar'), 'reinforcement steel'),
    (('metal deck', 'steel deck'), 'steel deck'),
    (('gypsum wall board', 'gypsum board'), 'plasterboard'),
    (('reinforced concrete', 'cast in place concrete', 'cast-in-place concrete',
      'cast in place', 'stahlbeton', 'concrete', 'beton'), 'concrete'),
    (('structural steel', 'metal steel', 'metal stud', 'steel', 'stahl'), 'steel'),
    (('aluminium', 'aluminum'), 'aluminium'),
    (('spruce', 'plywood', 'timber', 'wood', 'holz'), 'timber'),
    (('plasterboard', 'plaster board', 'gypsum board'), 'plasterboard'),
    (('sand lime', 'sand-lime', 'clay brick', 'brick', 'ziegel'), 'brick'),
    (('concrete block', 'masonry block', 'blockwork'), 'blockwork'),
    (('insulation', 'insulated', 'dämmung'), 'insulation'),
    (('glass', 'glazing', 'glas', '玻璃'), 'glass'),
)


PLACEHOLDER_MATERIAL_NAMES = {
    '', 'unnamed', 'default', 'default wall', 'default material', 'by category',
    'material', 'unknown', 'n a', 'na', 'none',
}


def is_placeholder_material_name(material_name: str) -> bool:
    text = str(material_name or '').strip().lower()
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text in PLACEHOLDER_MATERIAL_NAMES


def normalise_material_name(material_name: str) -> str:
    if material_name is None:
        return ''
    text = str(material_name).strip().lower()
    if text in SYNONYMS:
        return SYNONYMS[text]
    text = text.replace('&', ' and ')
    text = text.replace('/', ' ')
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    if text in PLACEHOLDER_MATERIAL_NAMES:
        return ''
    for key, value in SYNONYMS.items():
        if text == key:
            return value
    if text in {'concrete c30', 'concrete c35', 'concrete c40'}:
        return 'concrete'
    if ('concrete' in text and ('masonry' in text or ' cmu ' in f' {text} ')):
        return 'concrete masonry unit'
    if 'rebar' in text or 'reinforcing steel' in text or 'reinforcement steel' in text:
        return 'reinforcement steel'
    if 'metal deck' in text or 'steel deck' in text:
        return 'steel deck'
    if 'gypsum' in text and 'board' in text:
        return 'plasterboard'
    if text.startswith('concrete'):
        return 'concrete'
    if text.startswith('steel'):
        return 'steel'
    if text.startswith('timber') or text.startswith('wood'):
        return 'timber'
    if text.startswith('glass'):
        return 'glass'
    if text.startswith('brick'):
        return 'brick'
    if text.startswith('plaster'):
        return 'plasterboard'
    if text.startswith('insul'):
        return 'insulation'
    if text.startswith('block'):
        return 'blockwork'
    padded_text = f' {text} '
    for keywords, canonical_name in KEYWORD_PATTERNS:
        if any(keyword in padded_text for keyword in keywords):
            return canonical_name
    return text
