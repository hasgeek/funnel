"""Test live server."""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def test_open_homepage(live_server, selenium, db_session, org_uu) -> None:
    """Launch a live server and visit homepage."""
    org_uu.profile.is_verified = True
    db_session.commit()
    selenium.get(live_server.url)
    time.sleep(1)
    assert (
        selenium.find_element(By.CLASS_NAME, "project-headline").text
        == "Explore communities"
    )


def test_transport_mock_sms(live_server, selenium, app) -> None:
    """Live server fixture mocks transport functions to a logger."""
    selenium.get(app.url_for('login'))
    selenium.find_element(By.NAME, "username").send_keys("8123456789")
    selenium.find_element(By.CSS_SELECTOR, "#form-passwordlogin button").send_keys(
        Keys.RETURN
    )
    # browser.find_by_name('username').fill('8123456789')
    # browser.find_by_css('#form-passwordlogin button').click()
    # browser.find_by_name('otp').click()  # This causes browser to wait until load
    time.sleep(1)
    captured_sms = live_server.transport_calls.sms[-1]
    assert captured_sms.phone == '+918123456789'
    assert captured_sms.message.startswith('OTP is')
    assert 'otp' in captured_sms.vars
