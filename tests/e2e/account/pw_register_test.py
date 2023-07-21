"""Test account registration."""

import re
from typing import Dict

import pytest
from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

scenarios('account/register.feature')
pytestmark = pytest.mark.usefixtures('live_server')

TWOFLOWER_EMAIL = 'twoflower@example.org'
TWOFLOWER_PHONE = '+12015550123'
TWOFLOWER_PASSWORD = 'te@pwd3289'  # nosec


def check_recaptcha_loaded(page: Page) -> None:
    page.wait_for_selector(
        "#form-passwordlogin > div.g-recaptcha > div > div.grecaptcha-logo > iframe",
        timeout=10000,
    )


@given("Anonymous visitor is on the home page")
def given_anonuser_home_page(live_server, page) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title(re.compile("Test Hasgeek"))


@when(
    parsers.re(
        "they navigate to the login page and submit"
        " (?P<phone_or_email>a phone number|an email address)"
    ),
    target_fixture='anon_username',
)
def when_anonuser_navigates_login_and_submits(
    app, live_server, phone_or_email, page
) -> Dict[str, str]:
    if phone_or_email == "a phone number":
        username = '8123456789'
    elif phone_or_email == "an email address":
        username = 'anon@example.com'
    else:
        pytest.fail("Unknown username type")
    page.click(".header__button")
    check_recaptcha_loaded(page)
    page.wait_for_selector("input[name=username]").fill(username)
    page.click("#form-passwordlogin button")
    return {'phone_or_email': phone_or_email, 'username': username}


@then("they are prompted for their name and the OTP, which they provide")
def then_anonuser_prompted_name_and_otp(live_server, anon_username, page) -> None:
    page.wait_for_selector("input[name=fullname]").fill('Twoflower')
    if anon_username['phone_or_email'] == "a phone number":
        otp = live_server.transport_calls.sms[-1].vars['otp']
    elif anon_username['phone_or_email'] == "an email address":
        otp = live_server.transport_calls.email[-1].subject.split(' ')[-1]
    else:
        pytest.fail("Unknown username type")
    page.wait_for_selector("input[name=otp]").fill(otp)
    page.click("#form-otp button")


@then("they get an account and are logged in")
def then_they_are_logged_in(live_server, page) -> None:
    assert (
        page.get_by_text("You are now one of us. Welcome aboard!").inner_text()
        == "You are now one of us. Welcome aboard!"
    )


@given("Twoflower visitor is on the home page")
def when_twoflower_visits_homepage(
    live_server, page, db_session, user_twoflower
) -> None:
    page.goto(live_server.url)
    user_twoflower.password = TWOFLOWER_PASSWORD
    user_twoflower.add_phone(TWOFLOWER_PHONE)
    user_twoflower.add_email(TWOFLOWER_EMAIL)
    db_session.commit()


@when("they navigate to the login page")
def when_navigate_to_login_page(app, live_server, page):
    page.click(".header__button")


@when("they submit the email address with password")
@when("submit an email address with password")
def when_submit_email_password(page) -> None:
    check_recaptcha_loaded(page)
    page.wait_for_selector("input[name=username]").fill(TWOFLOWER_EMAIL)
    page.click("#use-password-login")
    page.wait_for_selector("input[name=password]").fill(TWOFLOWER_PASSWORD)
    page.click("#login-btn")


@then("they are logged in")
def then_logged_in(live_server, page) -> None:
    assert (
        page.wait_for_selector(".alert__text").inner_text() == "You are now logged in"
    )


@when("they submit the phone number with password")
@when("submit a phone number with password")
def when_submit_phone_password(app, live_server, page) -> None:
    check_recaptcha_loaded(page)
    page.wait_for_selector("input[name=username]").fill(TWOFLOWER_PHONE)
    page.click("#use-password-login")
    page.wait_for_selector("input[name=password]").fill(TWOFLOWER_PASSWORD)
    page.click("#login-btn")


@given("Anonymous visitor is on a project page")
def given_anonymous_project_page(live_server, page, db_session, new_project) -> None:
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    page.goto(live_server.url + new_project.profile.name + '/' + new_project.name)


@when("they click on follow")
def when_they_click_follow(page) -> None:
    page.wait_for_selector("#register-nav").click()


@then("a register modal appears")
def then_register_modal_appear(page) -> None:
    assert (
        page.wait_for_selector('xpath=//*[@id="passwordform"]/p[2]').inner_text()
        == "Tell us where you’d like to get updates. We’ll send an OTP to confirm."
    )


@when(
    parsers.re("they enter (?P<phone_or_email>a phone number|an email address)"),
    target_fixture='anon_username',
)
def when_they_enter_email(page, phone_or_email) -> Dict[str, str]:
    check_recaptcha_loaded(page)
    if phone_or_email == "a phone number":
        username = '8123456789'
    elif phone_or_email == "an email address":
        username = 'anon@example.com'
    else:
        pytest.fail("Unknown username type")
    page.wait_for_selector("input[name=username]").fill(username)
    page.click("#form-passwordlogin button")
    return {'phone_or_email': phone_or_email, 'username': username}


@given("Twoflower is on the project page")
def given_twoflower_visits_project(
    live_server, page, db_session, user_twoflower, new_project
) -> None:
    user_twoflower.password = TWOFLOWER_PASSWORD
    user_twoflower.add_phone(TWOFLOWER_PHONE)
    user_twoflower.add_email(TWOFLOWER_EMAIL)
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    page.goto(live_server.url + new_project.profile.name + '/' + new_project.name)


@given("the server uses Recaptcha")
def given_server_uses_recaptcha(
    live_server, db_session, user_twoflower, new_project, funnel
) -> None:
    user_twoflower.password = TWOFLOWER_PASSWORD
    user_twoflower.add_phone(TWOFLOWER_PHONE)
    user_twoflower.add_email(TWOFLOWER_EMAIL)
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    assert funnel.app.config['RECAPTCHA_PRIVATE_KEY']


@when("twoflower visits the login page, Recaptcha is required")
def when_twoflower_visits_login_page_recaptcha(app, live_server, page) -> None:
    page.goto(live_server.url + 'login')
    assert page.wait_for_selector(
        "#form-passwordlogin > div.g-recaptcha > div > div.grecaptcha-logo > iframe",
        timeout=10000,
    )


@then("they submit and Recaptcha validation passes")
def then_submit_recaptcha_validation_passes(live_server, page) -> None:
    page.wait_for_selector("input[name=username]").fill(TWOFLOWER_EMAIL)
    page.click("#use-password-login")
    page.wait_for_selector("input[name=password]").fill(TWOFLOWER_PASSWORD)
    page.click("#login-btn")
