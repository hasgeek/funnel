from pytest_bdd import given, parsers, scenarios, then, when
import pytest

scenarios('account_create.feature')
pytestmark = pytest.mark.usefixtures('live_server')


@given("Anonymous visitor is on the home page")
def given_anonuser_home_page(live_server, browser, db_session):
    browser.visit(live_server.url)


@when(
    parsers.re(
        "they navigate to the login page and submit"
        " (?P<phone_or_email>a phone number|an email address)"
    ),
    target_fixture='anon_username',
)
def when_anonuser_navigates_login_and_submits(
    app, live_server, browser, phone_or_email
):
    # browser.find_by_xpath("//a[contains(text(),'Login')]").click()
    assert browser.url == live_server.url
    browser.visit(app.url_for('login', _external=True))
    # browser.find_by_text("Login").click()
    if phone_or_email == "a phone number":
        username = '8123456789'
    elif phone_or_email == "an email address":
        username = 'anon@example.com'
    else:
        pytest.fail("Unknown username type")
    browser.find_by_name('username').fill(username)
    browser.find_by_css('#form-passwordlogin button').click()
    return {'phone_or_email': phone_or_email, 'username': username}


@then("they are prompted for their name and the OTP, which they provide")
def then_anonuser_prompted_name_and_otp(live_server, browser, anon_username):
    browser.find_by_name('fullname').fill("Twoflower")
    if anon_username['phone_or_email'] == "a phone number":
        otp = live_server.transport_calls.sms[-1].vars['otp']
    elif anon_username['phone_or_email'] == "an email address":
        otp = live_server.transport_calls.email[-1].subject.split(' ')[-1]
    else:
        pytest.fail("Unknown username type")
    browser.find_by_name('otp').fill(otp)
    browser.find_by_css('#form-otp button').click()


@then("they get an account and are logged in")
def then_they_are_logged_in(browser):
    assert browser.is_text_present("You are now one of us")
    browser.quit()
