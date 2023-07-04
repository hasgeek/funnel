"""Test live server."""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait


def test_open_homepage(live_server, selenium, db_session, org_uu) -> None:
    """Launch a live server and visit homepage."""
    wait = WebDriverWait(selenium, 10)
    org_uu.profile.is_verified = True
    db_session.commit()
    selenium.get(live_server.url)
    wait.until(ec.visibility_of_element_located((By.CLASS_NAME, 'project-headline')))
    assert selenium.find_element(By.CLASS_NAME, 'project-headline').text in (
        "Explore communities",
        "Past sessions",
    )


def test_transport_mock_sms(live_server, selenium, app) -> None:
    """Live server fixture mocks transport functions to a logger."""
    wait = WebDriverWait(selenium, 10)
    selenium.get(app.url_for('login'))
    selenium.find_element(By.NAME, 'username').send_keys("8123456789")
    wait.until(
        ec.element_to_be_clickable((By.CSS_SELECTOR, '#form-passwordlogin button'))
    ).send_keys(Keys.RETURN)
    wait.until(ec.element_to_be_clickable((By.NAME, "Confirm")))
    captured_sms = live_server.transport_calls.sms[-1]
    assert captured_sms.phone == '+918123456789'
    assert captured_sms.message.startswith("OTP is")
    assert 'otp' in captured_sms.vars
