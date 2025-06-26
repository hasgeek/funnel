"""Test Project views."""

from flask.ctx import AppContext
from markupsafe import escape

from funnel.views.project import get_registration_text


def test_registration_text(app_context: AppContext) -> None:
    assert escape(get_registration_text(count=0, registered=False)).startswith(
        "Be the first"
    )
    assert escape(get_registration_text(count=1, registered=True)).startswith(
        "You have registered"
    )
    assert escape(get_registration_text(count=1, registered=False)).startswith("One")
    assert escape(get_registration_text(count=2, registered=True)).startswith(
        "You &amp; one"
    )
    assert escape(get_registration_text(count=5, registered=True)).startswith(
        "You &amp; four"
    )
    assert escape(get_registration_text(count=5, registered=False)).startswith("Five")
    # More than ten
    assert escape(get_registration_text(count=33, registered=True)).startswith(
        "You &amp; 32"
    )
    assert escape(get_registration_text(count=3209, registered=False)).startswith(
        "3,209"
    )
