# IFC Carbon Readiness

A Streamlit prototype for preliminary A1-A3 embodied-carbon assessment and BIM data-readiness review. It extracts supported IFC elements, inherited material associations, quantities, declared IFC units, and storeys; matches materials to a user-supplied factor CSV; calculates compatible results; and reports exclusions transparently.

## Scope

- IFC upload validation including STEP signature, IFC schema, DATA section, and termination marker
- Material and base-quantity extraction with IfcOpenShell
- Conversion from declared IFC project or quantity units to SI units
- Controlled material-name normalisation
- Required, validated A1-A3 factor CSV for live IFC assessments
- Factor-aware quantity selection and compatible mass, volume, area, or item calculations
- Net quantities preferred over gross quantities where both are available
- Inheritance-aware scope classification with separate eligible, review-required, and not-applicable populations
- Parent/container exclusion to reduce component double counting
- Conservative handling of CMU, rebar, metal deck, gypsum board, and placeholder materials
- Data-readiness metrics, excluded-class counts, and missing-data diagnosis
- Auditable result, CSV, and multi-sheet Excel exports
- Element-level processing diagnostics retained in results and server logs
- Self-contained demonstration mode

This is not a certified whole-life carbon assessment, operational-carbon model, geometry-based quantity reconstruction tool, or replacement for professional assessment.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Run tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Reproduce the Snowdon validation

For local validation, keep the Snowdon IFC models and controlled A1-A3 factor table alongside the repository, then run:

```bash
python scripts/run_snowdon_validation.py
```

This recreates `Snowdon_Formal_Validation.xlsx`, including model hashes, scope populations, readiness results, factor provenance, all eligible-element results, the complete IFC scope register, and a 20-element independent arithmetic check. The generated workbook is local validation evidence and is not required to run the Streamlit app.

## Deploy on Streamlit Community Cloud

Push the repository to GitHub, create an app at `share.streamlit.io`, select the repository and branch, and use `app.py` as the entrypoint.

## Repository structure

- `app.py` - Streamlit application
- `src/` - extraction, calculation, readiness, analytics, and reporting modules
- `tests/` - automated test suite
- `scripts/run_snowdon_validation.py` - reproducible Snowdon validation runner
- `snowdon_controlled_factors.csv` - controlled Snowdon A1-A3 application factors
- `requirements.txt` - runtime dependencies
- `requirements-dev.txt` - test dependencies

## Carbon-factor CSV

For a live IFC assessment, upload a CSV containing `material_name`, `carbon_factor`, `unit`, `life_cycle_stage`, and `source`. Every row must use the `A1-A3` lifecycle boundary and a positive finite factor. Accepted units are `kgCO2e/kg`, `kgCO2e/m3`, `kgCO2e/m2`, and `kgCO2e/item`. Optional fields include `density_kg_per_m3`, `density_source`, `normalised_name`, `category`, `material_id`, `source_type`, `notes`, and `is_demo_value`. When density is supplied, `density_source` is mandatory. Uploaded rows marked `is_demo_value=true` are rejected; placeholder factors are restricted to the built-in demo workflow.

The prototype-defined readiness indicator is an equal-weight average of material completeness, valid-positive quantity completeness, unit completeness, factor coverage across all eligible elements, and successful calculation rate. The dashboard separately reports factor match success when attempted, calculated only from genuine matched and unmatched single-material cases. It is a research-specific diagnostic indicator rather than an official BIM, RICS, or ISO metric; its five readiness component percentages should remain the primary evidence.

The dashboard reports BIM data completeness (material, valid quantity, and unit availability) separately from carbon-assessment coverage (factor matching and calculation success). This distinction prevents limitations in an external factor dataset from being misreported as defects in the IFC model.

Use only factor data you are authorised to use. The Streamlit interface does not expose a download for the source ICE workbook; its storage or distribution must follow the licence or permission held by the project owner. The official source is the [Circular Ecology download page](https://circularecology.com/embodied-carbon-footprint-database.html).

Results depend on IFC completeness and factor quality. Elements without compatible material, quantity, unit, factor, or density data are excluded from the calculated total and remain visible in the readiness report.
