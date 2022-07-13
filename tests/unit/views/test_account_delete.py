from pytest_bdd import given, scenario, then, when


@scenario('../../features/account_delete.feature', 'User visits the delete endpoint')
def test_delete():
    pass


@given("the user is logged in")
def user_logged_in(client, login, user_rincewind):
    login.as_(user_rincewind)
    client.get('/')


@when("the user hits the delete endpoint", target_fixture="rv")
def go_to_endpoint(client, login, user_rincewind):
    rv = client.get('/account/delete')
    return rv


@then("AccountDeleteForm is displayed")
def account_delete_form(rv):
    assert rv.form('form-account-delete') is not None
