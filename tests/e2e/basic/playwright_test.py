"""Test live server."""

import re

from playwright.sync_api import expect


def test_open_homepage(live_server, page, db_session, org_uu):
    page.goto(live_server.url)
    expect(page).to_have_title(re.compile("Test Hasgeek"))
    expect(page.get_by_text("Past sessions")).to_be_visible()


def test_transport_mock_sms(live_server, page, app):
    page.goto(app.url_for('login'))
    textbox = page.locator('#username')
    textbox.fill("8123456789")
    page.locator('#get-otp-btn').click()
    page.get_by_role("button", name="Confirm").is_enabled()
    captured_sms = live_server.transport_calls.sms[-1]
    assert captured_sms.phone == '+918123456789'
    assert captured_sms.message.startswith("OTP is")
    assert 'otp' in captured_sms.vars
