# -*- coding: utf-8 -*-


class TestUser(object):
    def test_admin_role(self, test_client, test_db, new_profile):
        with test_client as c:
            rv = c.get('/usertest')
            assert rv.data == u"testuser"
            assert new_profile.current_roles.admin
