import time

from pytest_bdd import given, parsers, scenarios, then, when
import pytest

scenarios('account_user/account_create.feature')
pytestmark = pytest.mark.usefixtures('live_server')


# @given(parsers.parse("the browser locale is {language}"))
# def given_browser_locale(browser, db_session, language):
#     browser.execute_script(f"window.navigator.language = {language}")


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
    assert browser.url == live_server.url
    #: This doesn't work, no clue why
    # browser.links.find_by_partial_href('/login').click()
    #: This does work, but it doesn't test if there's a Login link on screen
    # browser.visit(app.url_for('login', _external=True))
    #: This one is the working hack, asking browser to visit the found link
    browser.visit(browser.links.find_by_partial_href('/login')['href'])
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
    time.sleep(1)
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


@given("Twoflower visitor is on the home page")
def when_twoflower_visits_homepage(live_server, browser, db_session, user_twoflower):
    browser.visit(live_server.url)
    user_twoflower.password = 'te@pwd3289'  # nosec
    user_twoflower.add_phone('+12345678900')
    user_twoflower.add_email('twoflower@example.org')
    db_session.commit()


@when("they navigate to the login page")
def when_navigate_to_login_page(app, live_server, browser):
    browser.visit(app.url_for('login', _external=True))


@when("they submit the email address with password")
@when("submit an email address with password")
def when_submit_email_password(browser):
    time.sleep(1)
    browser.find_by_name('username').fill('twoflower@example.org')
    browser.find_by_id("use-password-login").click()
    browser.find_by_name('password').fill('te@pwd3289')
    browser.find_by_id("login-btn").click()


@then("they are logged in")
def then_logged_in(browser):
    assert browser.is_text_present("You are now logged in")
    browser.quit()


@when("they submit the phone number with password")
@when("submit a phone number with password")
def when_submit_phone_password(app, live_server, browser):
    time.sleep(1)
    browser.find_by_name('username').fill('+12345678900')
    browser.find_by_id("use-password-login").click()
    browser.find_by_name('password').fill('te@pwd3289')
    browser.find_by_id("login-btn").click()


@given("Anonymous visitor is on a project page")
def given_anonymous_project_page(live_server, browser, db_session, new_project):
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    browser.visit(live_server.url + new_project.profile.name + '/' + new_project.name)


@when("they click on follow")
def when_they_click_follow(browser):
    time.sleep(1)
    browser.find_by_id("follow-btn").click()
    # element = WebDriverWait(browser.driver, 10).until(
    #     EC.presence_of_element_located(
    #         (
    #             By.ID,
    #             "follow-btn",
    #         )
    #     )
    # )
    # element.click()


@then("a register modal appears")
def then_register_modal_appear(browser):
    time.sleep(1)
    assert browser.is_text_present("Tell us where you’d like to get updates.")


@when(
    parsers.re("they enter (?P<phone_or_email>a phone number|an email address)"),
    target_fixture='anon_username',
)
def when_they_enter_email(browser, phone_or_email):
    time.sleep(1)
    if phone_or_email == "a phone number":
        username = '8123456789'
    elif phone_or_email == "an email address":
        username = 'anon@example.com'
    else:
        pytest.fail("Unknown username type")
    browser.find_by_name('username').fill(username)
    browser.find_by_css('#form-passwordlogin button').click()
    return {'phone_or_email': phone_or_email, 'username': username}


@given("Twoflower is on the project page")
def given_twoflower_visits_project(
    live_server, browser, db_session, user_twoflower, new_project
):
    user_twoflower.password = 'te@pwd3289'  # nosec
    user_twoflower.add_phone('+12345678900')
    user_twoflower.add_email('twoflower@example.org')
    new_project.publish()
    db_session.add(new_project)
    db_session.commit()
    browser.visit(live_server.url + new_project.profile.name + '/' + new_project.name)
