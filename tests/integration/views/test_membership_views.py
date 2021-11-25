def test_create_new_member(client, new_user_owner, new_project):
    with client.session_transaction() as session:
        session['userid'] = new_user_owner.userid
    # GET request should return a form
    resp = client.get(new_project.url_for('new_member'))
    assert resp.status_code == 200
    assert 'form' in resp.json
    assert new_project.url_for('new_member') in resp.json.get('form')

    # FIXME: Can't test new member creation because SelectUserField validation fails
