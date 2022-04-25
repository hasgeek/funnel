def test_create_new_member(client, login, new_user_owner, new_project):
    login.as_(new_user_owner)
    # GET request should return a form
    resp = client.get(new_project.url_for('new_member'))
    assert resp.status_code == 200
    assert 'form' in resp.json
    assert new_project.url_for('new_member') in resp.json.get('form')

    # FIXME: Can't test new member creation because SelectUserField validation fails
