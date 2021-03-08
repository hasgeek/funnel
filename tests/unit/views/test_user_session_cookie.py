from funnel import app


@app.route('/test/api/usertest')
def user_test():
    from coaster.auth import current_auth

    return current_auth.user.username if current_auth.user is not None else "<anon>"


def test_session_cookie_userid(client, new_user_owner, new_organization):
    with client.session_transaction() as session:
        session['userid'] = new_user_owner.userid
    rv = client.get('/test/api/usertest')
    assert rv.data.decode('utf-8') == new_user_owner.username
