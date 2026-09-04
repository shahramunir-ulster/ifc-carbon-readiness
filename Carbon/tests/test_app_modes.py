from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_switching_from_completed_demo_to_live_without_ifc_does_not_reuse_demo_result():
    app_path = Path(__file__).resolve().parents[1] / 'app.py'
    app = AppTest.from_file(app_path, default_timeout=30).run()
    next(button for button in app.button if button.label == 'Run assessment').click().run()
    assert not app.exception

    next(checkbox for checkbox in app.checkbox if checkbox.label == 'Use demo data').uncheck().run()

    assert not app.exception
    assert any('Upload an IFC file' in info.value for info in app.info)
