"""Test Project views."""

from funnel.views.project import get_registration_text


def test_registration_text() -> None:
    assert get_registration_text(count=0, registered=False).startswith("Be the first")
    assert get_registration_text(count=1, registered=True).startswith(
        "You are the first"
    )
    assert get_registration_text(count=1, registered=False).startswith("One")
    assert get_registration_text(count=2, registered=True).startswith("You &amp; one")
    assert get_registration_text(count=5, registered=True).startswith("You &amp; four")
    assert get_registration_text(count=5, registered=False).startswith("Five")
    # More than ten
    assert get_registration_text(count=33, registered=True).startswith("You &amp; 32")
    assert get_registration_text(count=3209, registered=False).startswith("3209")
