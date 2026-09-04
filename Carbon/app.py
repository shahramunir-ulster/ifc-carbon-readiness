from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics import aggregate_by_material, aggregate_by_storey, aggregate_by_type, issue_breakdown, top_carbon_elements
from src.assessment import process_element_record
from src.charts import horizontal_bar_chart
from src.data_readiness import compute_readiness_metrics
from src.demo_data import build_demo_element_rows, build_demo_factor_database
from src.presentation import carbon_display_tonnes, carbon_headline
from src.reporting import build_excel_export, filter_element_dataframe
from src.version import APPLICATION_VERSION, source_tree_sha256
from src.workflow import assess_ifc_bytes

st.set_page_config(
    page_title='Carbon Ready | IFC Assessment',
    page_icon='◼',
    layout='wide',
    initial_sidebar_state='expanded',
)

READINESS_EXPLANATION = (
    'Research-specific indicator: equal-weight average of material completeness, '
    'quantity completeness, unit completeness, factor coverage of eligible elements, and successful '
    'calculation rates. It is not an official BIM, RICS, or ISO metric.'
)

st.markdown(
    '''
    <style>
    :root { --carbon-green: #0f766e; --carbon-ink: #17312d; --carbon-soft: #ecf7f4; }
    .stApp { background: linear-gradient(180deg, #f6faf9 0, #ffffff 18rem); }
    .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background: #f0f7f5; border-right: 1px solid #d8e9e4; }
    [data-testid="stMetric"] {
        background: rgba(255,255,255,.94); border: 1px solid #dcebe7;
        border-radius: 14px; padding: 1rem 1.1rem; box-shadow: 0 5px 18px rgba(20,70,60,.06);
    }
    [data-testid="stMetricLabel"] {
        color: #48645e; min-height: 3rem; align-items: flex-start;
        white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--carbon-ink); white-space: normal !important;
        overflow: visible !important; text-overflow: clip !important;
    }
    [data-testid="stMetric"] { min-height: 9.5rem; }
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] > div,
    [data-testid="stMetricValue"] > div {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        overflow-wrap: anywhere !important;
        line-height: 1.25 !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid #dcebe7; }
    .stTabs [data-baseweb="tab"] { border-radius: 9px 9px 0 0; padding: .55rem .9rem; }
    .stTabs [aria-selected="true"] { background: var(--carbon-soft); color: var(--carbon-green); }
    .hero {
        padding: 1.65rem 1.8rem; border: 1px solid #cfe5df; border-radius: 18px;
        background: linear-gradient(120deg, #ffffff 0%, #e9f6f2 100%);
        box-shadow: 0 10px 30px rgba(20,70,60,.08); margin-bottom: 1.25rem;
    }
    .hero-kicker { color: var(--carbon-green); font-weight: 700; letter-spacing: .08em; font-size: .78rem; }
    .hero h1 { color: var(--carbon-ink); margin: .25rem 0 .45rem; font-size: 2.15rem; line-height: 1.15; }
    .hero p { color: #48645e; margin: 0; max-width: 880px; font-size: 1.02rem; }
    .footer-note { margin-top: 2rem; padding: 1rem 1.2rem; border-radius: 12px; background: #f3f7f6; color: #526964; }
    div[data-testid="stDataFrame"] { border: 1px solid #dcebe7; border-radius: 12px; overflow: hidden; }
    </style>
    ''',
    unsafe_allow_html=True,
)

@st.cache_data
def get_demo_data():
    return build_demo_element_rows(), build_demo_factor_database()


@st.cache_data(show_spinner=False, max_entries=2, ttl=3600)
def run_cached_live_assessment(ifc_bytes: bytes, factor_bytes: bytes) -> dict:
    return assess_ifc_bytes(ifc_bytes, factor_bytes)


st.markdown(
    '''
    <section class="hero">
      <div class="hero-kicker">OPENBIM · A1–A3 · DATA READINESS</div>
      <h1>IFC Carbon Readiness Assessment</h1>
      <p>Turn IFC quantities and material data into a transparent preliminary embodied-carbon estimate—while showing exactly what is missing, unmatched, or not yet calculable.</p>
    </section>
    ''',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header('Project overview')
    st.markdown(
        '''
        This prototype supports preliminary embodied carbon assessment and BIM data-readiness checking for SME building project workflows.
        It is designed for dissertation demonstration and is not a certified carbon assessment tool.
        '''
    )
    use_demo = st.checkbox('Use demo data', value=True)
    uploaded_file = st.file_uploader('Upload IFC file', type=['ifc'])
    uploaded_factor_file = st.file_uploader(
        'Upload verified A1-A3 factor CSV',
        type=['csv'],
        help='Required for uploaded IFC files. Use a dataset you are authorised to use; required columns are material_name, carbon_factor, unit, life_cycle_stage, and source.',
    )
    if uploaded_file is not None:
        st.caption(f'Uploaded file: {uploaded_file.name}')
    if uploaded_factor_file is not None:
        st.caption(f'Using factor file: {uploaded_factor_file.name}')

    run_requested = st.button(
        'Run assessment',
        type='primary',
        disabled=(uploaded_file is None and not use_demo) or (uploaded_file is not None and uploaded_factor_file is None),
        help='Process the selected IFC file and generate the assessment results.',
    )

    st.info('Live IFC mode requires a user-supplied, authorised A1-A3 factor CSV. The app does not redistribute third-party databases.')
    st.download_button(
        'Download factor CSV template',
        data='material_id,material_name,normalised_name,category,carbon_factor,unit,density_kg_per_m3,density_source,life_cycle_stage,source,source_type,notes\n',
        file_name='a1_a3_factor_template.csv',
        mime='text/csv',
    )

    st.markdown('---')
    st.subheader('Filter results')
    st.caption('Use these filters to review the dataset in the dissertation-style reporting views.')

    st.markdown('---')
    st.caption('Important note: demo carbon factors are placeholder values for prototype testing only.')

is_demo_run = bool(use_demo and uploaded_file is None)
input_signature = 'mode:demo' if is_demo_run else 'mode:live'
input_bytes = None
factor_bytes = None
if uploaded_file is not None:
    input_bytes = uploaded_file.getvalue()
    input_signature += f':ifc:{uploaded_file.name}:{hashlib.sha256(input_bytes).hexdigest()}'
if uploaded_factor_file is not None:
    factor_bytes = uploaded_factor_file.getvalue()
    if not is_demo_run:
        input_signature += f':factor:{hashlib.sha256(factor_bytes).hexdigest()}'

if st.session_state.get('assessment_input_signature') != input_signature:
    st.session_state.assessment_input_signature = input_signature
    st.session_state.assessment_started = False
    st.session_state.assessment_result = None
    st.session_state.assessment_export_signature = None
    st.session_state.assessment_excel_bytes = None

if run_requested:
    try:
        with st.spinner('Running IFC carbon-readiness assessment...'):
            if is_demo_run:
                demo_elements, demo_factors = get_demo_data()
                factor_df = pd.DataFrame(demo_factors)
                elements = [process_element_record(item.copy(), factor_df) for item in demo_elements]
                assessment_scope = {
                    'total_ifc_elements': len(elements), 'in_scope_elements': len(elements),
                    'excluded_elements': 0, 'review_required_elements': 0, 'not_applicable_elements': 0,
                    'excluded_class_counts': {}, 'scope_report': [], 'metadata': {},
                    'extraction_error_count': 0, 'error_count': 0, 'processing_error_count': 0,
                }
                result = {'elements': elements, 'factor_df': factor_df, 'assessment_scope': assessment_scope}
            else:
                if input_bytes is None or factor_bytes is None:
                    raise ValueError('Upload both an IFC file and a verified A1-A3 factor CSV.')
                result = run_cached_live_assessment(input_bytes, factor_bytes)
        result['assessment_generated_utc'] = datetime.now(timezone.utc).isoformat()
        st.session_state.assessment_result = result
        st.session_state.assessment_started = True
        st.session_state.assessment_export_signature = None
        st.session_state.assessment_excel_bytes = None
    except Exception as exc:
        st.session_state.assessment_started = False
        st.session_state.assessment_result = None
        st.error(f'Assessment failed: {exc}')
        st.stop()

if not st.session_state.get('assessment_started', False) or st.session_state.get('assessment_result') is None:
    if uploaded_file is None and not use_demo:
        st.info('Upload an IFC file, then select Run assessment to generate results.')
    else:
        st.info('Select Run assessment to process the selected data and generate results.')
    st.stop()

assessment_result = st.session_state.assessment_result
elements = assessment_result['elements']
factor_df = assessment_result['factor_df']
assessment_scope = assessment_result['assessment_scope']

if is_demo_run:
    assessed_file_name = 'demo_dataset'
    assessed_file_sha256 = 'not_applicable'
else:
    assessed_file_name = uploaded_file.name
    assessed_file_sha256 = hashlib.sha256(input_bytes).hexdigest()

scope_report_df = pd.DataFrame(assessment_scope.get('scope_report', []))
if not elements:
    st.warning('No assessment-eligible building elements were found. Review the scanned-scope report below.')
    if not scope_report_df.empty:
        st.dataframe(scope_report_df, width='stretch')
    st.stop()

summary_df = pd.DataFrame(elements)
metrics = compute_readiness_metrics(elements)
carbon_total = float(summary_df['embodied_carbon_kgco2e'].sum()) if not summary_df.empty else 0.0
calculation_coverage = (metrics['calculated_elements'] / len(elements) * 100) if elements else 0.0
carbon_metric_label = carbon_headline(metrics['calculated_elements'], len(elements))
coverage_warning = (
    f'Calculated carbon is {carbon_display_tonnes(carbon_total)} for '
    f'{metrics["calculated_elements"]} of {len(elements)} in-scope IFC elements '
    f'({calculation_coverage:.1f}% coverage). This is not a whole-building total.'
)

if 'global_id' in summary_df.columns:
    result_columns = [
        'global_id', 'ifc_class', 'element_type', 'object_type', 'element_name', 'storey', 'material_name',
        'material_normalised', 'material_names', 'matched_material_name', 'material_id',
        'factor_category', 'factor_notes', 'factor_is_proxy', 'quantity_set_name',
        'quantity_type', 'quantity_name', 'raw_quantity_value', 'raw_quantity_unit', 'quantity_value',
        'quantity_unit', 'unit_conversion_factor', 'unit_source', 'quantity_supported', 'unit_compatible',
        'quantity_selection_method', 'density_kg_per_m3', 'density_source',
        'calculated_mass_kg', 'carbon_factor', 'carbon_factor_unit',
        'life_cycle_stage', 'carbon_factor_source', 'matching_method',
        'matching_confidence', 'calculation_possible', 'embodied_carbon_kgco2e',
        'calculation_reason', 'calculation_failure_code', 'material_extraction_error', 'quantity_extraction_error',
        'extraction_error', 'processing_error', 'readiness_status', 'issues', 'recommended_action',
    ]
    result_table = summary_df.reindex(columns=result_columns, fill_value='').copy()
else:
    result_table = summary_df.copy()

with st.sidebar:
    st.subheader('Quick filters')
    classes = ['All'] + sorted([str(v) for v in result_table['ifc_class'].dropna().unique() if str(v).strip()])
    selected_class = st.selectbox('IFC class', classes, index=0)
    materials = ['All'] + sorted([str(v) for v in result_table['material_name'].fillna('').astype(str).unique() if str(v).strip()])
    selected_material = st.selectbox('Material', materials, index=0)
    storeys = ['All'] + sorted([str(v) for v in result_table['storey'].fillna('').astype(str).unique() if str(v).strip()])
    selected_storey = st.selectbox('Storey', storeys, index=0)
    statuses = ['All'] + sorted([str(v) for v in result_table['readiness_status'].fillna('').astype(str).unique() if str(v).strip()])
    selected_status = st.selectbox('Readiness status', statuses, index=0)
    search_term = st.text_input('Search elements', placeholder='Wall, concrete, Level 1...')

filtered_results = filter_element_dataframe(
    result_table,
    ifc_class=None if selected_class == 'All' else selected_class,
    material=None if selected_material == 'All' else selected_material,
    storey=None if selected_storey == 'All' else selected_storey,
    readiness=None if selected_status == 'All' else selected_status,
    search=search_term or None,
)

missing_df = summary_df[summary_df['issues'].apply(lambda x: bool(x))].copy()
missing_report = missing_df.reindex(columns=[
    'global_id', 'ifc_class', 'element_type', 'object_type', 'element_name', 'storey', 'material_name', 'material_match_status',
    'quantity_type', 'quantity_set_name', 'quantity_name', 'raw_quantity_value', 'raw_quantity_unit',
    'quantity_value', 'quantity_unit', 'unit_source', 'quantity_supported', 'unit_compatible',
    'calculation_failure_code', 'readiness_status', 'issues',
    'calculation_reason', 'material_extraction_error', 'quantity_extraction_error',
    'extraction_error', 'processing_error', 'recommended_action',
], fill_value='').copy()
match_df = summary_df.reindex(columns=[
    'global_id', 'material_name', 'material_normalised', 'matched_material_name',
    'material_match_status', 'matching_method', 'matching_confidence', 'material_id',
    'factor_category', 'factor_notes', 'factor_is_proxy', 'carbon_factor',
    'carbon_factor_unit', 'density_kg_per_m3', 'density_source', 'life_cycle_stage',
    'carbon_factor_source', 'carbon_factor_source_type', 'carbon_factor_is_demo',
], fill_value='').copy()

application_source_sha256 = source_tree_sha256(Path(__file__).resolve().parent)
summary_rows = [
    {'metric': 'assessment_generated_utc', 'value': assessment_result.get('assessment_generated_utc', '')},
    {'metric': 'application_version', 'value': APPLICATION_VERSION},
    {'metric': 'source_code_sha256', 'value': application_source_sha256},
    {'metric': 'input_file_name', 'value': assessed_file_name},
    {'metric': 'input_file_sha256', 'value': assessed_file_sha256},
    {'metric': 'factor_file_name', 'value': 'demo_factor_table' if is_demo_run else uploaded_factor_file.name},
    {'metric': 'factor_file_sha256', 'value': 'not_applicable' if is_demo_run else hashlib.sha256(factor_bytes).hexdigest()},
    {'metric': 'assessment_boundary', 'value': 'A1-A3'},
    {'metric': 'ifc_elements_detected', 'value': assessment_scope.get('total_ifc_elements', len(elements))},
    {'metric': 'in_scope_elements', 'value': len(elements)},
    {'metric': 'excluded_elements', 'value': assessment_scope.get('excluded_elements', 0)},
    {'metric': 'review_required_elements', 'value': assessment_scope.get('review_required_elements', 0)},
    {'metric': 'not_applicable_elements', 'value': assessment_scope.get('not_applicable_elements', 0)},
    {'metric': 'element_extraction_errors', 'value': assessment_scope.get('extraction_error_count', assessment_scope.get('error_count', 0))},
    {'metric': 'element_processing_errors', 'value': assessment_scope.get('processing_error_count', 0)},
    {'metric': 'excluded_class_counts', 'value': str(assessment_scope.get('excluded_class_counts', {}))},
    {'metric': 'ifc_project_name', 'value': assessment_scope.get('metadata', {}).get('project_name', '')},
    {'metric': 'ifc_project_long_name', 'value': assessment_scope.get('metadata', {}).get('project_long_name', '')},
    {'metric': 'ifc_project_phase', 'value': assessment_scope.get('metadata', {}).get('phase', '')},
    {'metric': 'calculated_elements', 'value': metrics['calculated_elements']},
    {'metric': 'calculation_success_rate_pct', 'value': round(metrics['calculation_success_rate'], 2)},
    {'metric': 'missing_or_incomplete_elements', 'value': metrics['missing_or_incomplete']},
    {'metric': 'genuine_unmatched_materials', 'value': metrics['unmatched_materials']},
    {'metric': 'multiple_material_elements', 'value': metrics['multiple_material_elements']},
    {'metric': 'incompatible_unit_elements', 'value': metrics['incompatible_units']},
    {'metric': 'calculated_A1_A3_carbon_assessment_eligible_elements_kgco2e', 'value': round(carbon_total, 3)},
    {'metric': 'prototype_defined_readiness_score', 'value': round(metrics['ready_score'], 2)},
    {'metric': 'material_completeness_pct', 'value': round(metrics['material_completeness'], 2)},
    {'metric': 'quantity_completeness_pct', 'value': round(metrics['quantity_completeness'], 2)},
    {'metric': 'unit_completeness_pct', 'value': round(metrics['unit_completeness'], 2)},
    {'metric': 'factor_coverage_of_eligible_elements_pct', 'value': round(metrics['factor_coverage_rate'], 2)},
    {'metric': 'factor_match_attempts', 'value': metrics['factor_match_attempts']},
    {'metric': 'factor_match_success_when_attempted_pct', 'value': round(metrics['factor_match_success_rate'], 2)},
]

home, upload, dashboard, missing, matching, methodology, exports = st.tabs([
    'Home',
    'Upload & Processing',
    'Dashboard',
    'Missing Data',
    'Factor Matching',
    'Methodology',
    'Exports',
])

with home:
    st.subheader('Research context')
    st.markdown(
        '''
        This prototype supports the dissertation objective of combining two evidence streams in early design decision-making:

        1. preliminary embodied carbon assessment from IFC-derived quantities and material assumptions;
        2. BIM data-readiness assessment to diagnose where information is missing or incompatible before formal carbon reporting.

        The output is intentionally conservative and transparency-first. It highlights issues rather than hiding them.
        '''
    )

    col1, col2, col3 = st.columns(3)
    col1.metric('Elements analysed', len(elements))
    col2.metric(carbon_metric_label, carbon_display_tonnes(carbon_total))
    col3.metric('Prototype-defined readiness', round(metrics['ready_score'], 1))
    st.caption(READINESS_EXPLANATION)
    if calculation_coverage < 100:
        st.warning(coverage_warning)
    if any('sand-lime' in str(element.get('material_name', '')).lower() for element in elements):
        st.info('Sand-lime masonry is normalised to the brick category as a preliminary proxy. Use a product-specific EPD and verify the mapping before relying on the result.')

    st.write('')
    st.markdown('### Prototype scope')
    st.markdown('- IFC element extraction using material associations and property quantities')
    st.markdown('- Data-readiness status logic for missing fields, incompatible units, and unclear classification')
    st.markdown('- Embodied carbon estimation using compatible quantity-to-factor pairings only')
    st.markdown('- Dashboard reporting and exportable outputs for SME project review')

    st.markdown('---')
    st.subheader('Carbon-factor transparency')
    st.markdown(
        'Uploaded IFC assessments use only the A1-A3 factor CSV supplied by the user. '
        'Every result retains its factor value, unit, lifecycle boundary, density (when used), and source reference. '
        'The app does not bundle or redistribute third-party carbon databases.'
    )
    st.link_button('Visit the official ICE database page', 'https://circularecology.com/embodied-carbon-footprint-database.html')

with upload:
    st.subheader('Upload and processing status')
    st.markdown('''
    The workflow supports both demo-mode and live IFC uploads. When a valid IFC file is supplied, the app extracts element classes, storeys, material associations, and quantity metadata before assessment.
    ''')

    factor_source_label = 'Demo placeholder factor table' if is_demo_run else uploaded_factor_file.name

    st.json({
        'upload_mode': 'demo' if is_demo_run else 'ifc_file',
        'element_count': len(elements),
        'file_name': uploaded_file.name if uploaded_file is not None else 'demo_dataset',
        'factor_database_rows': int(len(factor_df)) if factor_df is not None else 0,
        'factor_database_source': factor_source_label,
        'ifc_elements_detected': assessment_scope.get('total_ifc_elements', len(elements)),
        'in_scope_elements': len(elements),
        'excluded_elements': assessment_scope.get('excluded_elements', 0),
        'review_required_elements': assessment_scope.get('review_required_elements', 0),
        'not_applicable_elements': assessment_scope.get('not_applicable_elements', 0),
        'excluded_class_counts': assessment_scope.get('excluded_class_counts', {}),
        'element_extraction_errors': assessment_scope.get('extraction_error_count', assessment_scope.get('error_count', 0)),
        'element_processing_errors': assessment_scope.get('processing_error_count', 0),
    })
    if not scope_report_df.empty:
        with st.expander('Review scanned IFC scope'):
            st.dataframe(scope_report_df, width='stretch')

    st.info('This prototype deliberately avoids claiming formal carbon certification. It is a preliminary decision-support tool for early design and BIM readiness review.')

with dashboard:
    st.subheader('Processing status')
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    col1.metric('IFC elements detected', assessment_scope.get('total_ifc_elements', len(elements)))
    col2.metric('In-scope elements', len(elements))
    col3.metric('Review required', assessment_scope.get('review_required_elements', 0))
    col4.metric('Not applicable', assessment_scope.get('not_applicable_elements', 0))
    col5.metric('Successfully calculated', metrics['calculated_elements'])
    col6.metric('Prototype-defined readiness', round(metrics['ready_score'], 1))
    st.caption(READINESS_EXPLANATION)

    if calculation_coverage < 100:
        st.warning(coverage_warning + ' Unmatched or incomplete elements are excluded from this value.')

    st.markdown('---')
    st.subheader('BIM data completeness')
    st.caption('These indicators describe information available within the assessment-eligible IFC elements.')
    bim_metric_cols = st.columns(3)
    bim_metric_cols[0].metric('Material completeness', f"{metrics['material_completeness']:.1f}%")
    bim_metric_cols[1].metric('Valid quantity completeness', f"{metrics['quantity_completeness']:.1f}%")
    bim_metric_cols[2].metric('Unit completeness', f"{metrics['unit_completeness']:.1f}%")

    st.subheader('Carbon assessment coverage')
    st.caption('These indicators also depend on the supplied carbon-factor dataset and calculation compatibility.')
    carbon_metric_top = st.columns(3)
    carbon_metric_bottom = st.columns(3)
    carbon_metric_top[0].metric(carbon_metric_label, carbon_display_tonnes(carbon_total))
    carbon_metric_top[1].metric('Factor coverage of eligible elements', f"{metrics['factor_coverage_rate']:.1f}%")
    carbon_metric_top[2].metric('Factor match success when attempted', f"{metrics['factor_match_success_rate']:.1f}%")
    carbon_metric_bottom[0].metric('Calculation success rate', f"{metrics['calculation_success_rate']:.1f}%")
    carbon_metric_bottom[1].metric('Genuine unmatched materials', metrics['unmatched_materials'])
    carbon_metric_bottom[2].metric('Multiple-material review', metrics['multiple_material_elements'])

    material_chart = aggregate_by_material(elements)
    if not material_chart.empty:
        st.subheader('Carbon by controlled factor category')
        st.altair_chart(
            horizontal_bar_chart(
                material_chart, 'matched_material_name', 'embodied_carbon_kgco2e',
                'Calculated A1-A3 carbon (kgCO2e)',
            ),
            width='stretch',
        )

    hotspot_df = top_carbon_elements(elements, limit=10)
    if not hotspot_df.empty:
        st.subheader('Top 10 highest-carbon elements')
        st.dataframe(hotspot_df, width='stretch', hide_index=True)

    colA, colB = st.columns(2)
    type_chart = aggregate_by_type(elements)
    if not type_chart.empty:
        colA.subheader('Carbon by element type')
        colA.altair_chart(
            horizontal_bar_chart(type_chart, 'ifc_class', 'embodied_carbon_kgco2e', 'kgCO2e'),
            width='stretch',
        )
    storey_chart = aggregate_by_storey(elements)
    if not storey_chart.empty:
        colB.subheader('Carbon by storey')
        colB.altair_chart(
            horizontal_bar_chart(storey_chart, 'storey', 'embodied_carbon_kgco2e', 'kgCO2e'),
            width='stretch',
        )

    issue_df = issue_breakdown(elements)
    if not issue_df.empty:
        st.subheader('Missing-data breakdown')
        st.caption('This chart counts issue occurrences; one element may contribute more than one issue.')
        st.altair_chart(
            horizontal_bar_chart(issue_df, 'issue', 'count', 'Issue occurrences', color='#d97706'),
            width='stretch',
        )

    st.markdown('---')
    st.subheader('Element-level results')
    st.dataframe(filtered_results, width='stretch')

with missing:
    st.subheader('Missing-data report')
    filtered_missing = filter_element_dataframe(
        missing_report,
        ifc_class=None if selected_class == 'All' else selected_class,
        material=None if selected_material == 'All' else selected_material,
        storey=None if selected_storey == 'All' else selected_storey,
        readiness=None if selected_status == 'All' else selected_status,
        search=search_term or None,
    )
    if filtered_missing.empty:
        st.info('No missing-data issues were identified in the filtered dataset.')
    else:
        st.dataframe(filtered_missing, width='stretch')

with matching:
    st.subheader('Carbon-factor matching report')
    st.caption('Matching uses controlled material normalisation and exact normalised names. Ambiguous multi-material elements are rejected until layer-specific quantities are available; no fuzzy match is silently accepted.')
    match_columns = st.columns(4)
    match_columns[0].metric('Matched', int((summary_df['material_match_status'] == 'matched').sum()))
    match_columns[1].metric('Unmatched', int((summary_df['material_match_status'] == 'unmatched').sum()))
    match_columns[2].metric('Invalid placeholders', int((summary_df['material_match_status'] == 'invalid').sum()))
    match_columns[3].metric('Layered / multiple', int((summary_df['material_match_status'] == 'multiple_materials_review_required').sum()))
    with st.expander('Review active A1-A3 factor table'):
        factor_preview_columns = [
            'material_id', 'material_name', 'normalised_name', 'category',
            'carbon_factor', 'unit', 'density_kg_per_m3', 'density_source',
            'life_cycle_stage', 'source', 'notes',
        ]
        st.dataframe(factor_df.reindex(columns=factor_preview_columns), width='stretch')
    filtered_match = match_df.copy()
    if selected_class != 'All':
        filtered_match = filtered_match[filtered_match['global_id'].isin(summary_df[summary_df['ifc_class'].astype(str) == selected_class]['global_id'])]
    if selected_material != 'All':
        filtered_match = filtered_match[filtered_match['material_name'].fillna('').astype(str).str.contains(str(selected_material).strip(), case=False, na=False)]
    if selected_storey != 'All':
        filtered_match = filtered_match[filtered_match['global_id'].isin(summary_df[summary_df['storey'].fillna('').astype(str).str.contains(str(selected_storey).strip(), case=False, na=False)]['global_id'])]
    if search_term:
        term = search_term.lower()
        filtered_match = filtered_match[filtered_match.astype(str).apply(lambda row: ' '.join(row.values).lower(), axis=1).str.contains(term, na=False)]
    st.dataframe(filtered_match.reset_index(drop=True), width='stretch')

with methodology:
    st.subheader('Methodological note')
    st.markdown(
        '''
        The prototype follows a staged logic:

        1. IFC validation and parsing of element classes, material associations, and quantity sets.
        2. Inheritance-aware classification into assessment eligible, review required, and not applicable. Composite containers and decomposed parents are withheld from automatic totals to reduce double counting.
        3. Conservative material normalisation to reduce naming variation without silently treating CMU, rebar, or steel deck as generic materials.
        4. Quantity selection and unit checks. Net quantity is preferred, gross quantity is a documented fallback, and declared IFC units are converted to SI.
        5. Data-readiness classification and reporting for missing information, incompatible units, unclear classifications, and excluded objects.

        This approach is intentionally suited to preliminary net-zero and early design review, not formal product declaration or certification.
        '''
    )
    st.markdown('''
    **Calculation rules (A1-A3 only)**

    - Volume factor: `carbon = volume (m3) x factor (kgCO2e/m3)`
    - Area factor: `carbon = area (m2) x factor (kgCO2e/m2)`
    - Mass factor: `carbon = mass (kg) x factor (kgCO2e/kg)`
    - Volume-to-mass: `carbon = volume (m3) x density (kg/m3) x factor (kgCO2e/kg)`
    - Item factor: `carbon = count x factor (kgCO2e/item)`

    Values are calculated only when the quantity, factor, units, lifecycle stage, and any required density pass validation. A supplied density must include a source. IFC project or explicit quantity units are converted to SI before calculation. The export records the full scanned scope, raw quantities, conversion factors, selected quantities, density and calculated mass, factor sources, and input-file hashes for auditability.

    The prototype-defined readiness indicator is the equal-weight arithmetic mean of material completeness, valid-positive quantity completeness, unit completeness, factor coverage across all eligible elements, and successful calculation rate. Factor match success when attempted is reported separately using only genuine matched and unmatched single-material cases. This is a research-specific diagnostic indicator, not an official BIM, RICS, or ISO metric; the five readiness component percentages remain the primary evidence.
    ''')

with exports:
    st.subheader('Export package')
    st.caption('The Excel workbook always contains the complete assessment. Dashboard filters apply only to the separate filtered CSV.')

    export_signature = f'{input_signature}:app:{APPLICATION_VERSION}:source:{application_source_sha256}'
    if st.session_state.get('assessment_export_signature') != export_signature:
        st.session_state.assessment_excel_bytes = build_excel_export(
            result_table.reset_index(drop=True),
            missing_report.reset_index(drop=True),
            match_df.reset_index(drop=True),
            summary_rows,
            scope_report_df,
        )
        st.session_state.assessment_export_signature = export_signature
    excel_bytes = st.session_state.assessment_excel_bytes

    st.download_button(
        'Download Excel workbook',
        data=excel_bytes,
        file_name='ifc_carbon_readiness_report.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )

    csv_buffer = filtered_results.to_csv(index=False)
    st.download_button('Download filtered CSV', csv_buffer, file_name='filtered_results.csv', mime='text/csv')

    missing_csv = missing_report.to_csv(index=False)
    st.download_button('Download missing-data CSV', missing_csv, file_name='missing_data_report.csv', mime='text/csv')

    summary_csv = pd.DataFrame(summary_rows).to_csv(index=False)
    st.download_button('Download summary CSV', summary_csv, file_name='carbon_summary.csv', mime='text/csv')

st.markdown(
    '<div class="footer-note"><strong>Assessment boundary:</strong> Preliminary A1–A3 embodied-carbon estimation and BIM data-readiness review. Results do not replace formal carbon assessment or verified product declarations.</div>',
    unsafe_allow_html=True,
)
