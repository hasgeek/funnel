import time

from pytest_bdd import given, scenarios, then, when
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
import pytest

scenarios('profile/add_profile.feature')
pytestmark = pytest.mark.usefixtures('live_server')

TWOFLOWER_EMAIL = 'twoflower@example.org'
TWOFLOWER_PHONE = '+12015550123'
TWOFLOWER_PASSWORD = 'te@pwd3289'  # nosec


@given("Twoflower is logged in")
def given_twoflower_logs_in(live_server, selenium, db_session, user_twoflower):
    selenium.get(live_server.url)
    user_twoflower.password = TWOFLOWER_PASSWORD
    user_twoflower.add_phone(TWOFLOWER_PHONE)
    user_twoflower.add_email(TWOFLOWER_EMAIL)
    db_session.commit()
    wait = WebDriverWait(selenium, 10)
    time.sleep(1)
    wait.until(ec.element_to_be_clickable((By.CLASS_NAME, 'header__button'))).send_keys(
        Keys.RETURN
    )
    WebDriverWait(selenium, 10)
    time.sleep(1)
    selenium.find_element(By.NAME, 'username').send_keys('twoflower@example.org')
    selenium.find_element(By.ID, 'use-password-login').click()
    selenium.find_element(By.NAME, 'password').send_keys('te@pwd3289')
    selenium.find_element(By.ID, 'login-btn').send_keys(Keys.ENTER)


@when("they open account settings")
def when_open_account_settings(live_server, selenium):
    time.sleep(1)
    selenium.find_element(
        By.CSS_SELECTOR,
        '#hgnav > div > div > div.header__site-title__title__settings.mui--hidden-xs.mui--hidden-sm > div > a',
    ).send_keys(Keys.ENTER)


@when("they create a new organization")
def when_create_new_organization(live_server, selenium):
    selenium.find_element(
        By.CSS_SELECTOR,
        '#hgnav > div > div > div.js-account-menu-wrapper > ul > li:nth-child(2) > a',
    ).send_keys(Keys.ENTER)
    time.sleep(1)
    selenium.find_element(
        By.CSS_SELECTOR,
        'body > div.content-wrapper > div > div.mui-container.page-content > div > div > div > ul > li:nth-child(1) > a',
    ).send_keys(Keys.ENTER)
    time.sleep(1)
    selenium.find_element(
        By.CSS_SELECTOR,
        '#title',
    ).send_keys("Beta")
    selenium.find_element(
        By.CSS_SELECTOR,
        '#name',
    ).send_keys("beta")
    selenium.find_element(
        By.CSS_SELECTOR,
        '#form-org_new > div.mui-form.form-actions.mui--clearfix > div > button',
    ).send_keys(Keys.ENTER)
    time.sleep(1)
    selenium.find_element(
        By.CSS_SELECTOR,
        '#tagline',
    ).send_keys("description")
    selenium.find_element(
        By.CSS_SELECTOR,
        '#form-A4z7eOKTSRii0f4DH1VaDQ > div.mui-form.form-actions.mui--clearfix > div > button',
    ).send_keys(Keys.ENTER)


@then("a profile will be created")
def then_profile_is_created(live_server, selenium):
    selenium.get(live_server.url)
    assert live_server.url + 'beta'
