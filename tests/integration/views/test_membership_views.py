from funnel.models import ProjectCrewMembership


def test_get_existing_members(
    client,
    db_session,
    new_user,
    new_user_owner,
    new_project,
    new_project2,
):
    with client.session_transaction() as session:
        session['userid'] = new_user.userid
    # new_user is new_project.profile's admin, so the page should load
    resp = client.get(new_project.url_for('crew'))
    assert resp.status_code == 200
    assert "Add a member" in resp.data.decode('utf-8')

    # but new_user is not new_project2.profile's admin, so it should not load
    resp2 = client.get(new_project2.url_for('crew'))
    assert resp2.status_code == 403  # forbidden
    assert "Add new member" not in resp2.data.decode('utf-8')
    assert "Access denied" in resp2.data.decode('utf-8')

    # let's add a member to the project
    new_membership = ProjectCrewMembership(
        parent=new_project, user=new_user, is_editor=True
    )
    db_session.add(new_membership)
    db_session.commit()

    # now the new member should show up in membership page
    resp3 = client.get(new_project.url_for('crew'))
    assert resp3.status_code == 200
    assert new_user.fullname in resp3.data.decode('utf-8')
    # membership record's edit/delete urls are in the page
    assert new_membership.url_for('edit') in resp3.data.decode('utf-8')
    assert new_membership.url_for('delete') in resp3.data.decode('utf-8')

    # let's revoke the membership
    new_membership.revoke(actor=new_user_owner)
    db_session.commit()
    # now the member should not show up in the page
    resp3 = client.get(new_project.url_for('crew'))
    assert resp3.status_code == 200
    assert new_user.fullname not in resp3.data.decode('utf-8')


def test_create_new_member(client, new_user_owner, new_project):
    with client.session_transaction() as session:
        session['userid'] = new_user_owner.userid
    # GET request should return a form
    resp = client.get(new_project.url_for('new_member'))
    assert resp.status_code == 200
    assert 'form' in resp.json
    assert new_project.url_for('new_member') in resp.json.get('form')

    # FIXME: Can't test new member creation because SelectUserField validation fails


def test_edit_member(client, db_session, new_user, new_user_owner, new_project):
    with client.session_transaction() as session:
        session['userid'] = new_user_owner.userid
    # let's add a member to the project
    new_membership = ProjectCrewMembership(
        parent=new_project, user=new_user, is_editor=True
    )
    db_session.add(new_membership)
    db_session.commit()

    # GET request should return a form
    resp = client.get(new_membership.url_for('edit'))
    assert resp.status_code == 200
    assert 'form' in resp.json
    assert new_membership.url_for('edit') in resp.json.get('form')

    new_membership.revoke(actor=new_user_owner)
    db_session.commit()

    # FIXME: Can't test member edit because SelectUserField validation fails


def test_delete_new_member(client, db_session, new_user, new_user_owner, new_project):
    with client.session_transaction() as session:
        session['userid'] = new_user.userid
    new_membership = ProjectCrewMembership(
        parent=new_project, user=new_user_owner, is_editor=True
    )
    db_session.add(new_membership)
    db_session.commit()

    assert new_membership in new_project.active_crew_memberships

    # GET request should return a form
    resp = client.get(new_membership.url_for('delete'))
    assert resp.status_code == 200
    assert 'form' in resp.json
    assert new_membership.url_for('delete') in resp.json.get('form')

    resp2 = client.post(new_membership.url_for('delete'))
    assert resp2.status_code == 200
    assert resp2.json.get('status') == 'ok'

    assert new_membership.is_active is not True
    assert new_membership not in new_project.active_crew_memberships
