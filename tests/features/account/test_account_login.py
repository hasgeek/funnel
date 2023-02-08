from pytest_bdd import given, scenarios, then, when

PATCH_SMS_SEND = 'funnel.transports.sms.send'


scenarios('account_login.feature')


@given("Twoflower visits the login page")
def given_twoflower_visits_login_page(browser, db_session, live_server, user_twoflower):
    browser.visit(live_server.url + 'login')


@given("they enter the phone number")
def given_twoflower_enters_phone_number(
    browser, db_session, live_server, user_twoflower
):
    browser.find_by_name('username').fill('9663462919')


@when("they click on get otp")
def when_click_get_otp(
    browser, db_session, live_server, user_twoflower, client, csrf_token
):
    browser.find_by_xpath('//*[@id="form-passwordlogin"]/div[4]/button').click()


@when("enter their name with correct otp")
def when_enter_name_and_otp(browser, db_session, live_server, user_twoflower):
    pass


@then("they get 'You are now logged in' flash message")
def then_get_flash_message():
    pass


@given("they enter the email")
def given_twoflower_enters_email(browser, db_session, live_server, user_twoflower):
    browser.find_by_name('username').fill('test@example.com')
