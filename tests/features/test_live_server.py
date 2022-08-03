"""Test live server."""


def test_open_homepage(browser, db_session, live_server, org_uu) -> None:
    """Launch a live server and visit homepage."""
    org_uu.profile.is_verified = True
    db_session.commit()
    browser.visit(live_server.url)
    assert browser.is_text_present("Explore communities")
