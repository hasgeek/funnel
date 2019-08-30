# -*- coding: utf-8 -*-


from funnel.models import ProjectCrewMembership


class TestMembershipViews(object):
    def test_get_existing_members(
        self, test_client, test_db, new_user, new_user2, new_project, new_project2
    ):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            # new_user is new_project.profile's admin, so the page should load
            resp = c.get(new_project.url_for('membership'))
            assert resp.status_code == 200
            assert u"Add a member" in resp.data.decode('utf-8')

            # but new_user is not new_project2.profile's admin, so it should not load
            resp2 = c.get(new_project2.url_for('membership'))
            assert resp2.status_code == 403  # forbidden
            assert u"Add a member" not in resp2.data.decode('utf-8')
            assert u"Access denied" in resp2.data.decode('utf-8')

            # let's add a member to the project
            new_membership = ProjectCrewMembership(
                project=new_project, user=new_user, is_editor=True
            )
            test_db.session.add(new_membership)
            test_db.session.commit()

            # now the new member should show up in membership page
            resp3 = c.get(new_project.url_for('membership'))
            assert resp3.status_code == 200
            assert new_user.fullname in resp3.data.decode('utf-8')
            # membership record's edit/delete urls are in the page
            assert new_membership.url_for('edit') in resp3.data.decode('utf-8')
            assert new_membership.url_for('delete') in resp3.data.decode('utf-8')

            # let's revoke the membership
            new_membership.revoke(actor=new_user2)
            test_db.session.commit()
            # now the member should not show up in the page
            resp3 = c.get(new_project.url_for('membership'))
            assert resp3.status_code == 200
            assert new_user.fullname not in resp3.data.decode('utf-8')

    def test_create_new_member(self, test_client, new_user, new_project):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            # GET request should return a form
            resp = c.get(new_project.url_for('new_member'))
            assert resp.status_code == 200
            assert 'form' in resp.json
            assert new_project.url_for('new_member') in resp.json.get('form')

            # FIXME: Can't test new member creation because SelectUserField validation fails

    def test_edit_member(self, test_client, test_db, new_user, new_user2, new_project):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            # let's add a member to the project
            new_membership = ProjectCrewMembership(
                project=new_project, user=new_user2, is_editor=True
            )
            test_db.session.add(new_membership)
            test_db.session.commit()

            # GET request should return a form
            resp = c.get(new_membership.url_for('edit'))
            assert resp.status_code == 200
            assert 'form' in resp.json
            assert new_membership.url_for('edit') in resp.json.get('form')

            new_membership.revoke(actor=new_user)
            test_db.session.commit()

            # FIXME: Can't test member edit because SelectUserField validation fails

    def test_delete_new_member(
        self, test_client, test_db, new_user, new_user2, new_project
    ):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            new_membership = ProjectCrewMembership(
                project=new_project, user=new_user2, is_editor=True
            )
            test_db.session.add(new_membership)
            test_db.session.commit()

            assert new_membership in new_project.active_crew_memberships

            # GET request should return a form
            resp = c.get(new_membership.url_for('delete'))
            assert resp.status_code == 200
            assert 'form' in resp.json
            assert new_membership.url_for('delete') in resp.json.get('form')

            resp2 = c.post(new_membership.url_for('delete'))
            assert resp2.status_code == 200
            assert resp2.json.get('status') == 'ok'

            assert new_membership.active is not True
            assert new_membership not in new_project.active_crew_memberships
