"""Test live server."""

from flask import url_for


def test_some_browser_stuff(browser, db_session, app, live_server, org_uu):
    """Launch a live server and visit homepage."""
    org_uu.profile.is_verified = True
    db_session.commit()
    browser.visit(url_for('index', _external=True))
    assert browser.is_text_present("Explore communities")
