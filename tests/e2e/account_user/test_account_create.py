import time

from pytest_bdd import given, parsers, scenarios, then, when
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
import pytest

scenarios('account_user/account_create.feature')
pytestmark = pytest.mark.usefixtures('live_server')


# @given(parsers.parse("the browser locale is {language}"))
# def given_browser_locale(browser, db_session, language):
#     browser.execute_script(f"window.navigator.language = {language}")


# Parameterization is not working
# @pytest.mark.parametrize("locale", [('firefox_hi'), ('firefox_en')])
@given("Anonymous visitor is on the home page")
def given_anonuser_home_page(live_server, selenium, db_session):
    selenium.get(live_server.url)


@when(
    parsers.re(
        "they navigate to the login page and submit"
        " (?P<phone_or_email>a phone number|an email address)"
    ),
    target_fixture='anon_username',
)
def when_anonuser_navigates_login_and_submits(
    app, live_server, selenium, phone_or_email
):
    assert selenium.current_url == live_server.url
    wait = WebDriverWait(selenium, 10)
    time.sleep(2)
    # Ideally wait.until() should wait until the element is clickable,
    # but the test is failing when used without time.sleep
    wait.until(ec.element_to_be_clickable((By.CLASS_NAME, 'header__button'))).send_keys(
        Keys.RETURN
    )
    if phone_or_email == "a phone number":
        username = '8123456789'
    elif phone_or_email == "an email address":
        username = 'anon@example.com'
    else:
        pytest.fail("Unknown username type")
    wait.until(ec.element_to_be_clickable((By.NAME, "username"))).send_keys(username)
    time.sleep(2)
    wait.until(
        ec.element_to_be_clickable((By.CSS_SELECTOR, '#form-passwordlogin button'))
    ).send_keys(Keys.ENTER)
    return {'phone_or_email': phone_or_email, 'username': username}


@then("they are prompted for their name and the OTP, which they provide")
def then_anonuser_prompted_name_and_otp(live_server, selenium, anon_username):
    time.sleep(2)
    selenium.find_element(By.NAME, 'fullname').send_keys("Twoflower")
    if anon_username['phone_or_email'] == "a phone number":
        otp = live_server.transport_calls.sms[-1].vars['otp']
    elif anon_username['phone_or_email'] == "an email address":
        otp = live_server.transport_calls.email[-1].subject.split(' ')[-1]
    else:
        pytest.fail("Unknown username type")
    selenium.find_element(By.NAME, 'otp').send_keys(otp)
    selenium.find_element(By.CSS_SELECTOR, '#form-otp button').send_keys(Keys.ENTER)


@then("they get an account and are logged in")
def then_they_are_logged_in(selenium):
    time.sleep(2)
    assert (
        selenium.find_element(By.CLASS_NAME, "alert__text").text
        == "You are now one of us. Welcome aboard!"
    )


@given("Twoflower visitor is on the home page")
def when_twoflower_visits_homepage(live_server, selenium, db_session, user_twoflower):
    selenium.get(live_server.url)
    user_twoflower.password = 'te@pwd3289'  # nosec
    user_twoflower.add_phone('+12345678900')
    user_twoflower.add_email('twoflower@example.org')
    db_session.commit()


@when("they navigate to the login page")
def when_navigate_to_login_page(app, live_server, selenium):
    wait = WebDriverWait(selenium, 10)
    time.sleep(2)
    wait.until(ec.element_to_be_clickable((By.CLASS_NAME, 'header__button'))).send_keys(
        Keys.RETURN
    )


@when("they submit the email address with password")
@when("submit an email address with password")
def when_submit_email_password(selenium):
    WebDriverWait(selenium, 10)
    time.sleep(2)
    selenium.find_element(By.NAME, 'username').send_keys('twoflower@example.org')
    selenium.find_element(By.ID, 'use-password-login').click()
    selenium.find_element(By.NAME, 'password').send_keys('te@pwd3289')
    selenium.find_element(By.ID, 'login-btn').send_keys(Keys.ENTER)


@then("they are logged in")
def then_logged_in(selenium):
    time.sleep(2)
    assert (
        selenium.find_element(By.CLASS_NAME, "alert__text").text
        == "You are now logged in"
    )


@when("they submit the phone number with password")
@when("submit a phone number with password")
def when_submit_phone_password(app, live_server, selenium):
    WebDriverWait(selenium, 10)
    time.sleep(2)
    selenium.find_element(By.NAME, 'username').send_keys('+12345678900')
    selenium.find_element(By.ID, 'use-password-login').click()
    selenium.find_element(By.NAME, 'password').send_keys('te@pwd3289')
    selenium.find_element(By.ID, 'login-btn').send_keys(Keys.ENTER)


@given("Anonymous visitor is on a project page")
def given_anonymous_project_page(live_server, selenium, db_session, new_project):
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    selenium.get(live_server.url + new_project.profile.name + '/' + new_project.name)


@when("they click on follow")
def when_they_click_follow(selenium):
    time.sleep(2)
    selenium.find_element(By.ID, 'register-nav').send_keys(Keys.ENTER)


@then("a register modal appears")
def then_register_modal_appear(selenium):
    time.sleep(2)
    assert (
        selenium.find_element(By.XPATH, '//*[@id="passwordform"]/p[2]').text
        == "Tell us where you’d like to get updates. We’ll send an OTP to confirm."
    )


@when(
    parsers.re("they enter (?P<phone_or_email>a phone number|an email address)"),
    target_fixture='anon_username',
)
def when_they_enter_email(selenium, phone_or_email):
    wait = WebDriverWait(selenium, 10)
    time.sleep(2)
    if phone_or_email == "a phone number":
        username = '8123456789'
    elif phone_or_email == "an email address":
        username = 'anon@example.com'
    else:
        pytest.fail("Unknown username type")
    wait.until(ec.element_to_be_clickable((By.NAME, "username"))).send_keys(username)
    time.sleep(2)
    wait.until(
        ec.element_to_be_clickable((By.CSS_SELECTOR, '#form-passwordlogin button'))
    ).send_keys(Keys.ENTER)
    return {'phone_or_email': phone_or_email, 'username': username}


@given("Twoflower is on the project page")
def given_twoflower_visits_project(
    live_server, selenium, db_session, user_twoflower, new_project
):
    user_twoflower.password = 'te@pwd3289'  # nosec
    user_twoflower.add_phone('+12345678900')
    user_twoflower.add_email('twoflower@example.org')
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    selenium.get(live_server.url + new_project.profile.name + '/' + new_project.name)
