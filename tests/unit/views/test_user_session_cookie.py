from funnel import app


@app.route('/test/api/usertest')
def user_test():
    from coaster.auth import current_auth

    return current_auth.user.username if current_auth.user is not None else "<anon>"


def test_session_cookie_userid(client, login, new_user_owner, new_organization):
    login.as_(new_user_owner)
    rv = client.get('/test/api/usertest')
    assert rv.data.decode('utf-8') == new_user_owner.username
