"""Test account registration."""
# pylint: disable=redefined-outer-name

import re

import pytest
from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models

scenarios('account/register.feature')
pytestmark = pytest.mark.usefixtures('live_server')

TWOFLOWER_EMAIL = 'twoflower@example.org'
TWOFLOWER_PHONE = '+12015550123'
TWOFLOWER_PASSWORD = 'te@pwd3289'  # nosec
ANONYMOUS_PHONE = '8123456789'
ANONYMOUS_EMAIL = 'anon@example.com'

pytestmark = pytest.mark.filterwarnings(
    "ignore:Object of type <AccountPhone> not in session",
    "ignore:Object of type <AccountEmail> not in session",
)


@pytest.fixture()
def published_project(db_session, new_project: models.Project) -> models.Project:
    """Published project fixture."""
    new_project.publish()
    new_project.rsvp_state = models.PROJECT_RSVP_STATE.ALL
    db_session.commit()
    return new_project


@pytest.fixture()
def user_twoflower_with_password_and_contact(
    db_session, user_twoflower: models.User
) -> models.User:
    """User fixture with a password and contact."""
    user_twoflower.password = TWOFLOWER_PASSWORD
    user_twoflower.add_phone(TWOFLOWER_PHONE)
    user_twoflower.add_email(TWOFLOWER_EMAIL)
    db_session.commit()
    return user_twoflower


def wait_until_recaptcha_loaded(page: Page) -> None:
    page.wait_for_selector(
        '#form-passwordlogin > div.g-recaptcha > div > div.grecaptcha-logo > iframe',
        timeout=10000,
    )


@given("Anonymous visitor is on the home page")
def given_anonuser_home_page(live_server, page: Page) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Test Hasgeek")


@when(
    parsers.re(
        "they navigate to the login page and submit"
        " (?P<phone_or_email>a phone number|an email address)"
    ),
    target_fixture='anon_username',
)
def when_anonuser_navigates_login_and_submits(
    app, live_server, phone_or_email: str, page: Page
) -> dict[str, str]:
    if phone_or_email == "a phone number":
        username = ANONYMOUS_PHONE
    elif phone_or_email == "an email address":
        username = ANONYMOUS_EMAIL
    else:
        pytest.fail("Unknown username type")
    page.click('.header__button')
    wait_until_recaptcha_loaded(page)
    selector = page.wait_for_selector('input[name=username]')
    assert selector is not None
    selector.fill(username)
    page.click('#form-passwordlogin button')
    return {'phone_or_email': phone_or_email, 'username': username}


@then("they are prompted for their name and the OTP, which they provide")
def then_anonuser_prompted_name_and_otp(anon_username, live_server, page: Page) -> None:
    selector = page.wait_for_selector('input[name=fullname]')
    assert selector is not None
    selector.fill('Twoflower')
    if anon_username['phone_or_email'] == "a phone number":
        otp = live_server.transport_calls.sms[-1].vars['otp']
    elif anon_username['phone_or_email'] == "an email address":
        subject = live_server.transport_calls.email[-1].subject
        match = re.search(r'\b\d{4}\b', subject)
        assert match is not None
        otp = match.group(0)
    else:
        pytest.fail("Unknown username type")
    selector = page.wait_for_selector('input[name=otp]')
    assert selector is not None
    selector.fill(otp)
    page.click('#form-otp button')


@then("they get an account and are logged in")
def then_they_are_logged_in(
    user_twoflower_with_password_and_contact, live_server, page: Page
) -> None:
    selector = page.wait_for_selector('.alert__text')
    assert selector is not None
    assert selector.inner_text() == "You are now one of us. Welcome aboard!"


@given("Twoflower visitor is on the home page")
def when_twoflower_visits_homepage(
    db_session, user_twoflower_with_password_and_contact, live_server, page: Page
) -> None:
    db_session.commit()
    page.goto(live_server.url)


@when("they navigate to the login page")
def when_navigate_to_login_page(app, live_server, page: Page):
    page.click('.header__button')


@when("they submit the email address with password")
@when("submit an email address with password")
def when_submit_email_password(page: Page) -> None:
    wait_until_recaptcha_loaded(page)
    selector = page.wait_for_selector('input[name=username]')
    assert selector is not None
    selector.fill(TWOFLOWER_EMAIL)
    page.click('#use-password-login')
    selector = page.wait_for_selector('input[name=password]')
    assert selector is not None
    selector.fill(TWOFLOWER_PASSWORD)
    page.click('#login-btn')


@then("they are logged in")
def then_logged_in(live_server, page: Page) -> None:
    selector = page.wait_for_selector('.alert__text')
    assert selector is not None
    assert selector.inner_text() == "You are now logged in"


@when("they submit the phone number with password")
@when("submit a phone number with password")
def when_submit_phone_password(app, live_server, page: Page) -> None:
    wait_until_recaptcha_loaded(page)
    selector = page.wait_for_selector('input[name=username]')
    assert selector is not None
    selector.fill(TWOFLOWER_PHONE)
    page.click('#use-password-login')
    selector = page.wait_for_selector('input[name=password]')
    assert selector is not None
    selector.fill(TWOFLOWER_PASSWORD)
    page.click('#login-btn')


@given("Anonymous visitor is on a project page")
def given_anonymous_project_page(
    db_session, published_project, live_server, page: Page
) -> None:
    page.goto(published_project.absolute_url)


@when("they click on follow")
def when_they_click_follow(page: Page) -> None:
    selector = page.wait_for_selector("#register-nav")
    assert selector is not None
    selector.click()


@then("a register modal appears")
def then_register_modal_appear(page: Page) -> None:
    selector = page.wait_for_selector('xpath=//*[@id="passwordform"]/p[2]')
    assert selector is not None
    assert (
        selector.inner_text()
        == "Tell us where you’d like to get updates. We’ll send an OTP to confirm."
    )


@when(
    parsers.re("they enter (?P<phone_or_email>a phone number|an email address)"),
    target_fixture='anon_username',
)
def when_they_enter_email(page: Page, phone_or_email: str) -> dict[str, str]:
    wait_until_recaptcha_loaded(page)
    if phone_or_email == "a phone number":
        username = ANONYMOUS_PHONE
    elif phone_or_email == "an email address":
        username = ANONYMOUS_EMAIL
    else:
        pytest.fail("Unknown username type")
    selector = page.wait_for_selector('input[name=username]')
    assert selector is not None
    selector.fill(username)
    page.click('#form-passwordlogin button')
    return {'phone_or_email': phone_or_email, 'username': username}


@given("Twoflower is on the project page")
def given_twoflower_visits_project(
    user_twoflower_with_password_and_contact,
    published_project,
    db_session,
    live_server,
    page: Page,
) -> None:
    page.goto(published_project.absolute_url)


@given("the server uses Recaptcha")
def given_server_uses_recaptcha(
    user_twoflower_with_password_and_contact,
    published_project,
    db_session,
    live_server,
    funnel,
) -> None:
    assert funnel.app.config['RECAPTCHA_PRIVATE_KEY']


@when("twoflower visits the login page, Recaptcha is required")
def when_twoflower_visits_login_page_recaptcha(app, live_server, page: Page) -> None:
    page.goto(live_server.url + 'login')
    assert page.wait_for_selector(
        '#form-passwordlogin > div.g-recaptcha > div > div.grecaptcha-logo > iframe',
        timeout=10000,
    )


@then("they submit and Recaptcha validation passes")
def then_submit_recaptcha_validation_passes(live_server, page: Page) -> None:
    selector = page.wait_for_selector("input[name=username]")
    assert selector is not None
    selector.fill(TWOFLOWER_EMAIL)
    page.click('#use-password-login')
    selector = page.wait_for_selector('input[name=password]')
    assert selector is not None
    selector.fill(TWOFLOWER_PASSWORD)
    page.click('#login-btn')
