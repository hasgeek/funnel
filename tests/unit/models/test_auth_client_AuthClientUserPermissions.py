from funnel import models

from .test_db import TestDatabaseFixture


class TestUserClientPermissions(TestDatabaseFixture):
    def test_userclientpermissions(self) -> None:
        """Test for verifying creation of UserClientPermissions instance."""
        gustav = models.User(username='gustav')
        auth_client = self.fixtures.auth_client
        access_permissions = 'siteadmin'
        result = models.AuthClientUserPermissions(
            user=gustav, auth_client=auth_client, access_permissions=access_permissions
        )
        self.db_session.add(result)
        self.db_session.commit()
        assert isinstance(result, models.AuthClientUserPermissions)

    def test_userclientpermissions_pickername(self) -> None:
        """Test for UserClientPermissions' pickername."""
        finnick = models.User(username='finnick', fullname="Finnick Odair")
        district4 = models.AuthClient(title="District 4")
        access_permissions = 'siteadmin'
        result = models.AuthClientUserPermissions(
            user=finnick, auth_client=district4, access_permissions=access_permissions
        )
        assert result.pickername == finnick.pickername


def test_userclientpermissions_migrate_user_move(
    db_session, user_twoflower, user_rincewind, client_hex
):
    """Migrating client permissions from old user to new user."""
    # Scenario 1: Twoflower has a permission and it is transferred to Rincewind
    userperms = models.AuthClientUserPermissions(
        user=user_twoflower,
        auth_client=client_hex,
        access_permissions='perm_for_twoflower',
    )
    db_session.add(userperms)

    # Transfer assets from Twoflower to Rincewind
    models.AuthClientUserPermissions.migrate_user(user_twoflower, user_rincewind)
    assert userperms.user == user_rincewind


def test_userclientpermissions_migrate_user_retain(
    db_session, user_twoflower, user_rincewind, client_hex
):
    """Retaining new user's client permissions when migrating assets from old user."""
    # Scenario 2: Rincewind has a permission, and keeps it after merging Twoflower
    userperms = models.AuthClientUserPermissions(
        user=user_rincewind,
        auth_client=client_hex,
        access_permissions='perm_for_rincewind',
    )
    db_session.add(userperms)

    # Transfer assets from Twoflower to Rincewind
    models.AuthClientUserPermissions.migrate_user(user_twoflower, user_rincewind)
    assert userperms.user == user_rincewind


def test_userclientpermissions_migrate_user_merge(
    db_session, user_twoflower, user_rincewind, client_hex
):
    """Merging permissions granted to two users when migrating from one to other."""
    # Scenario 3: Twoflower and Rincewind each have permissions, and they get merged
    userperms1 = models.AuthClientUserPermissions(
        user=user_twoflower,
        auth_client=client_hex,
        access_permissions='perm_for_twoflower',
    )
    userperms2 = models.AuthClientUserPermissions(
        user=user_rincewind,
        auth_client=client_hex,
        access_permissions='perm_for_rincewind',
    )
    db_session.add_all([userperms1, userperms2])
    db_session.commit()  # A commit is required since one of the two will be deleted

    # Transfer assets from Twoflower to Rincewind
    models.AuthClientUserPermissions.migrate_user(user_twoflower, user_rincewind)
    db_session.commit()  # Commit required or the db_session fixture will break

    assert len(user_twoflower.client_permissions) == 0
    assert len(user_rincewind.client_permissions) == 1
    assert len(client_hex.user_permissions) == 1
    assert client_hex.user_permissions[0].user == user_rincewind
    assert (
        client_hex.user_permissions[0].access_permissions
        == 'perm_for_rincewind perm_for_twoflower'
    )
