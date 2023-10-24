"""Tests for AuthClientPermissions model."""

from funnel import models

from .db_test import TestDatabaseFixture


class TestUserClientPermissions(TestDatabaseFixture):
    def test_userclientpermissions(self) -> None:
        """Test for verifying creation of UserClientPermissions instance."""
        gustav = models.User(username='gustav')
        auth_client = self.fixtures.auth_client
        access_permissions = 'siteadmin'
        result = models.AuthClientPermissions(
            account=gustav,
            auth_client=auth_client,
            access_permissions=access_permissions,
        )
        self.db_session.add(result)
        self.db_session.commit()
        assert isinstance(result, models.AuthClientPermissions)

    def test_userclientpermissions_pickername(self) -> None:
        """Test for UserClientPermissions' pickername."""
        finnick = models.User(username='finnick', fullname="Finnick Odair")
        district4 = models.AuthClient(title="District 4")
        access_permissions = 'siteadmin'
        result = models.AuthClientPermissions(
            account=finnick,
            auth_client=district4,
            access_permissions=access_permissions,
        )
        assert result.pickername == finnick.pickername


def test_userclientpermissions_migrate_account_move(
    db_session, user_twoflower, user_rincewind, client_hex
) -> None:
    """Migrating client permissions from old user to new user."""
    # Scenario 1: Twoflower has a permission and it is transferred to Rincewind
    userperms = models.AuthClientPermissions(
        account=user_twoflower,
        auth_client=client_hex,
        access_permissions='perm_for_twoflower',
    )
    db_session.add(userperms)

    # Transfer assets from Twoflower to Rincewind
    models.AuthClientPermissions.migrate_account(user_twoflower, user_rincewind)
    assert userperms.account == user_rincewind


def test_userclientpermissions_migrate_account_retain(
    db_session, user_twoflower, user_rincewind, client_hex
) -> None:
    """Retaining new user's client permissions when migrating assets from old user."""
    # Scenario 2: Rincewind has a permission, and keeps it after merging Twoflower
    userperms = models.AuthClientPermissions(
        account=user_rincewind,
        auth_client=client_hex,
        access_permissions='perm_for_rincewind',
    )
    db_session.add(userperms)

    # Transfer assets from Twoflower to Rincewind
    models.AuthClientPermissions.migrate_account(user_twoflower, user_rincewind)
    assert userperms.account == user_rincewind


def test_userclientpermissions_migrate_account_merge(
    db_session, user_twoflower, user_rincewind, client_hex
) -> None:
    """Merging permissions granted to two users when migrating from one to other."""
    # Scenario 3: Twoflower and Rincewind each have permissions, and they get merged
    userperms1 = models.AuthClientPermissions(
        account=user_twoflower,
        auth_client=client_hex,
        access_permissions='perm_for_twoflower',
    )
    userperms2 = models.AuthClientPermissions(
        account=user_rincewind,
        auth_client=client_hex,
        access_permissions='perm_for_rincewind',
    )
    db_session.add_all([userperms1, userperms2])
    db_session.commit()  # A commit is required since one of the two will be deleted

    # Transfer assets from Twoflower to Rincewind
    models.AuthClientPermissions.migrate_account(user_twoflower, user_rincewind)
    db_session.commit()  # Commit required or the db_session fixture will break

    assert len(user_twoflower.client_permissions) == 0
    assert len(user_rincewind.client_permissions) == 1
    assert len(client_hex.account_permissions) == 1
    assert client_hex.account_permissions[0].account == user_rincewind
    assert (
        client_hex.account_permissions[0].access_permissions
        == 'perm_for_rincewind perm_for_twoflower'
    )
