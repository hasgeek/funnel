from funnel import models

from .test_db import TestDatabaseFixture


class TestUserOldId(TestDatabaseFixture):
    def test_useroldid_get(self) -> None:
        """Test for verifying creation and retrieval of UserOldId instance."""
        crusoe = self.fixtures.crusoe
        bathound = models.User(username="bathound", fullname="Bathound")
        self.db_session.add(bathound)
        self.db_session.commit()
        with self.app.test_request_context('/'):
            merged = models.merge_users(crusoe, bathound)
            if merged == crusoe:
                other = bathound
            else:
                other = crusoe
            query_for_olduser = models.UserOldId.get(other.uuid)
            assert isinstance(query_for_olduser, models.UserOldId)
            assert query_for_olduser.olduser == other
