"""Test live server."""


def test_open_homepage(live_server, browser, db_session, org_uu) -> None:
    """Launch a live server and visit homepage."""
    org_uu.profile.is_verified = True
    db_session.commit()
    browser.visit(live_server.url)
    assert browser.is_text_present("Explore communities")


def test_transport_mock_sms(live_server, app, browser) -> None:
    """Live server fixture mocks transport functions to a logger."""
    browser.visit(app.url_for('login'))
    assert list(live_server.transport_calls.sms) == []
    assert list(live_server.transport_calls.email) == []
    browser.find_by_name('username').fill('8123456789')
    browser.find_by_css('#form-passwordlogin button').click()
    browser.find_by_name('otp').click()  # This causes browser to wait until load
    assert list(live_server.transport_calls.sms) != []
    assert list(live_server.transport_calls.email) == []
    assert len(live_server.transport_calls.sms) == 1
    captured_sms = live_server.transport_calls.sms[-1]
    assert captured_sms.phone == '+918123456789'
    assert captured_sms.message.startswith('OTP is')
    assert 'otp' in captured_sms.vars
