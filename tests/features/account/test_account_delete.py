from pytest_bdd import given, scenario, then, when
from pytest_splinter.webdriver_patches import patch_webdriver
import pytest


@pytest.fixture(scope="session")
def browser_patches():  # noqa : PT004
    patch_webdriver()


@pytest.fixture(scope='session')
def splinter_webdriver():
    """Override splinter webdriver name."""
    return 'chrome'


def test_some_browser_stuff(browser):
    url = "http://hasgeek.com"
    browser.visit(url)
    assert browser.is_text_present('Explore communities')


@scenario("account_delete.feature", "User Rincewind visits the delete endpoint")
def test_delete_rincewind():
    pass


@given("user Rincewind is logged in")
def rincewind_logged_in(client, login, user_rincewind):
    login.as_(user_rincewind)


@when(
    "user Rincewind visits the delete endpoint",
    target_fixture="rincewind_go_to_endpoint",
)
def rincewind_go_to_endpoint(client, login, user_rincewind):
    rv = client.get('/account/delete')
    return rv


@then("user Rincewind is prompter for delete confirmation")
def rincewind_account_delete_form(rincewind_go_to_endpoint):
    assert rincewind_go_to_endpoint.form('form-account-delete') is not None


@scenario("account_delete.feature", "User Ridcully visits the delete endpoint")
def test_delete_ridcully():
    pass


@given("user Ridcully is logged in")
@given("user Ridcully is the sole owner of Unseen University")
def ridcully_logged_in(client, login, user_ridcully, org_uu):
    login.as_(user_ridcully)


@when(
    "user Ridcully visits the delete endpoint", target_fixture="ridcully_go_to_endpoint"
)
def ridcully_go_to_endpoint(client, login, user_ridcully):
    rv = client.get('/account/delete')
    return rv


@then("'This account has organizations without co-owners' warning is shown to the user")
def ridcully_account_delete_form(ridcully_go_to_endpoint):
    assert ridcully_go_to_endpoint.form('form-account-delete') is None
    assert (
        'This account has organizations without co-owners'
        in ridcully_go_to_endpoint.data.decode()
    )


@scenario("account_delete.feature", "User Librarian visits the delete endpoint")
def test_delete_librarian():
    pass


@given("user Librarian is logged in")
def librarian_logged_in(client, login, org_uu, user_librarian):
    login.as_(user_librarian)


@given('user Librarian is a co-owner of Unseen University')
def librarian_coowner():
    pass


@when(
    "user Librarian hits the delete endpoint", target_fixture="librarian_go_to_endpoint"
)
def librarian_go_to_endpoint(client, login, user_librarian):
    rv = client.get('/account/delete')
    return rv


@then("user Librarian is prompted for delete confirmation")
def librarian_account_delete_form(librarian_go_to_endpoint):
    assert librarian_go_to_endpoint.form('form-account-delete') is not None


@scenario(
    "account_delete.feature",
    "User Librarian having a protected profile visits the delete endpoint",
)
def test_delete_protected_librarian():
    pass


@given("user librarian is logged in")
def protected_librarian_logged_in(client, login, org_uu, user_librarian, db_session):
    login.as_(user_librarian)


@given("user Librarian has a protected profile")
def librarian_protected_account(user_librarian, db_session):
    user_librarian.profile.is_protected = True
    db_session.add(user_librarian)


@when(
    "user Librarian visits the delete endpoint",
    target_fixture="protected_librarian_go_to_endpoint",
)
def protected_librarian_go_to_endpoint(client, login, user_librarian):
    rv = client.get('/account/delete')
    return rv


@then("'This account is protected' warning is shown to the user")
def protected_librarian_account_delete_form(
    protected_librarian_go_to_endpoint, user_librarian
):
    assert protected_librarian_go_to_endpoint.form('form-account-delete') is None
    assert (
        "This account is protected" in protected_librarian_go_to_endpoint.data.decode()
    )
