class TestUser(object):
    def test_admin_role(self, test_client, test_db, new_user_owner, new_organization):
        with test_client.session_transaction() as session:
            session['userid'] = new_user_owner.userid
        with test_client as c:
            rv = c.get('/usertest')
            assert rv.data.decode('utf-8') == new_user_owner.username
            assert new_organization.profile.current_roles.admin
