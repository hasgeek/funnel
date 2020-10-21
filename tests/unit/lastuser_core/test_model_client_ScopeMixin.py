from funnel import db
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestScopeMixin(TestDatabaseFixture):
    def test_scopemixin_scope(self):
        """Retrieve scope on an ScopeMixin inherited class instance via `scope`."""
        scope = 'tricks'
        ginny = models.User(username='ginny', fullname='Ginny Weasley')
        auth_client = self.fixtures.auth_client
        ginny_token = models.AuthToken(
            auth_client=auth_client, user=ginny, scope=scope, validity=0
        )
        db.session.add_all([ginny, ginny_token])
        db.session.commit()
        self.assertEqual(ginny_token.scope, (scope,))

    def test_scopemixin_add_scope(self):
        """Test for adding scope to a ScopeMixin inherited class instance."""
        scope1 = 'spells'
        scope2 = 'charms'
        neville = models.User(username='neville', fullname='Neville Longbottom')
        auth_client = self.fixtures.auth_client
        neville_token = models.AuthToken(
            auth_client=auth_client, user=neville, validity=0, scope=scope1
        )
        db.session.add_all([neville, neville_token])
        neville_token.add_scope(scope2)
        self.assertEqual(neville_token.scope, (scope2, scope1))
