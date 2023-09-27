"""Tests for AccountOldId model."""

import pytest

from funnel import models

from .db_test import TestDatabaseFixture


class TestAccountOldId(TestDatabaseFixture):
    @pytest.mark.usefixtures('app_context')  # merge_accounts logs progress
    def test_accountoldid_get(self) -> None:
        """Test for verifying creation and retrieval of AccountOldId instance."""
        crusoe = self.fixtures.crusoe
        bathound = models.User(username="bathound", fullname="Bathound")
        self.db_session.add(bathound)
        self.db_session.commit()
        with self.app.test_request_context('/'):
            merged = models.merge_accounts(crusoe, bathound)
            if merged == crusoe:
                other = bathound
            else:
                other = crusoe
            old_account = models.AccountOldId.get(other.uuid)
            assert isinstance(old_account, models.AccountOldId)
            assert old_account.old_account == other
