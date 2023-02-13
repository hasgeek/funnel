from pytest_bdd import given, scenarios, then, when
import pytest

PATCH_SMS_SEND = 'funnel.transports.sms.send'

scenarios('account_login.feature')
pytestmark = pytest.mark.usefixtures('live_server')


# pytest-bdd loads fixtures by looping through the function arguments of the step.
# Hence, db_session should be placed after live_server in all BDD steps.
@given("Twoflower visits the login page")
def given_twoflower_visits_login_page(app, browser):
    browser.visit(app.url_for('login', _external=True))


@given("they enter the phone number")
def given_twoflower_enters_phone_number(browser):
    # TODO: Create `sample_data` fixture for sample phone numbers
    # This number borrowed from tests/unit/models/test_phone_number.py
    browser.find_by_name('username').fill('8123456789')


@when("they click on get otp")
def when_click_get_otp(browser):
    browser.find_by_xpath('//*[@id="form-passwordlogin"]/div[4]/button').click()


@when("enter their name with correct otp")
def when_enter_name_and_otp():
    pass


@then("they get \"You are now logged in\" flash message")
def then_get_flash_message():
    pass


@given("they enter the email")
def given_twoflower_enters_email(browser):
    browser.find_by_name('username').fill('test@example.com')
