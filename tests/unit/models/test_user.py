# -*- coding: utf-8 -*-


class TestUser(object):
    def test_admin_role(self, test_client, test_db, new_user, new_profile):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            rv = c.get('/usertest')
            assert rv.data == new_user.username
            assert new_profile.current_roles.admin
            assert new_profile.current_roles.profile_admin
