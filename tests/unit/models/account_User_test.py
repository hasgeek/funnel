"""Tests for User model."""

# pylint: disable=use-implicit-booleaness-not-comparison

from datetime import timedelta

import pytest

from coaster.utils import utcnow

from funnel import models

from ...conftest import scoped_session

pytestmark = pytest.mark.filterwarnings(
    "ignore:Object of type <AccountEmail> not in session",
    "ignore:Object of type <AccountPhone> not in session",
)


def test_user(db_session: scoped_session) -> None:
    """Test for creation of user object from User model."""
    user = models.User(username='hrun', fullname="Hrun the Barbarian")
    db_session.add(user)
    db_session.commit()
    hrun = models.User.get(name='hrun')
    assert isinstance(hrun, models.User)
    assert user.username == 'hrun'
    assert user.fullname == "Hrun the Barbarian"
    assert user.state.ACTIVE
    assert hrun == user


def test_user_pickername(
    user_twoflower: models.User, user_rincewind: models.User
) -> None:
    """Test to verify `pickername` contains fullname and optional username."""
    assert user_twoflower.pickername == "Twoflower"
    assert user_rincewind.pickername == "Rincewind (@rincewind)"


def test_user_is_profile_complete(
    db_session: scoped_session, user_twoflower: models.User, user_rincewind: models.User
) -> None:
    """
    Test to check if user profile is complete.

    That is fullname, username and email are present.
    """
    # Both fixtures start out incomplete
    assert user_twoflower.is_profile_complete() is False
    assert user_rincewind.is_profile_complete() is False

    # Rincewind claims an email address, but it is not verified
    db_session.add(
        models.AccountEmailClaim(account=user_rincewind, email='rincewind@example.org')
    )
    db_session.commit()
    assert user_rincewind.is_profile_complete() is False

    # Rincewind's profile is complete when a verified email address is added
    user_rincewind.add_email('rincewind@example.org')
    assert user_rincewind.is_profile_complete() is True

    # Email is insufficient for Twoflower
    user_twoflower.add_email('twoflower@example.org')
    assert user_twoflower.is_profile_complete() is False

    # Twoflower also needs a username
    user_twoflower.username = 'twoflower'
    assert user_twoflower.is_profile_complete() is True


def test_user_organization_owned(
    user_ridcully: models.User, org_uu: models.Organization
) -> None:
    """Test for verifying organizations a user is a owner of."""
    assert list(user_ridcully.organizations_as_owner) == [org_uu]


def test_user_email(db_session: scoped_session, user_twoflower: models.User) -> None:
    """Add and retrieve an email address."""
    assert user_twoflower.email == ''
    accountemail = user_twoflower.add_email('twoflower@example.org', primary=False)
    assert isinstance(accountemail, models.AccountEmail)
    db_session.commit()
    assert accountemail.primary is False
    # When there is no primary, accessing the `email` property will promote existing
    assert user_twoflower.email == accountemail
    assert accountemail.primary is True

    useremail2 = user_twoflower.add_email('twoflower@example.com', primary=True)
    db_session.commit()

    # The primary has changed
    assert user_twoflower.email == useremail2
    assert accountemail.primary is False
    assert useremail2.primary is True


def test_user_del_email(
    db_session: scoped_session, user_twoflower: models.User
) -> None:
    """Delete an email address from a user's account."""
    assert user_twoflower.primary_email is None
    assert len(user_twoflower.emails) == 0
    user_twoflower.add_email('twoflower@example.org', primary=True)
    user_twoflower.add_email('twoflower@example.com')
    user_twoflower.add_email('twoflower@example.net')
    db_session.commit()

    assert len(user_twoflower.emails) == 3
    assert user_twoflower.primary_email is not None
    assert str(user_twoflower.primary_email) == 'twoflower@example.org'
    assert {str(e) for e in user_twoflower.emails} == {
        'twoflower@example.org',
        'twoflower@example.com',
        'twoflower@example.net',
    }

    # Delete a non-primary email address. It will be removed
    user_twoflower.del_email('twoflower@example.net')
    db_session.commit()

    assert len(user_twoflower.emails) == 2
    assert user_twoflower.primary_email is not None
    assert str(user_twoflower.primary_email) == 'twoflower@example.org'
    assert {str(e) for e in user_twoflower.emails} == {
        'twoflower@example.org',
        'twoflower@example.com',
    }

    # Delete a primary email address. The next available address will be made primary
    user_twoflower.del_email('twoflower@example.org')
    db_session.commit()

    assert len(user_twoflower.emails) == 1
    assert user_twoflower.primary_email is not None
    assert str(user_twoflower.primary_email) == 'twoflower@example.com'
    assert {str(e) for e in user_twoflower.emails} == {
        'twoflower@example.com',
    }

    # Delete last remaining email address. Primary will be removed
    user_twoflower.del_email('twoflower@example.com')
    db_session.commit()

    assert len(user_twoflower.emails) == 0
    assert user_twoflower.primary_email is None
    assert user_twoflower.email == ''


def test_user_phone(db_session: scoped_session, user_twoflower: models.User) -> None:
    """Test to retrieve AccountPhone property phone."""
    assert user_twoflower.phone == ''
    accountphone = user_twoflower.add_phone('+12345678900', primary=False)
    assert isinstance(accountphone, models.AccountPhone)
    db_session.commit()
    assert accountphone.primary is False
    # When there is no primary, accessing the `phone` property will promote existing
    assert user_twoflower.phone == accountphone
    assert accountphone.primary is True

    userphone2 = user_twoflower.add_phone('+12345678901', primary=True)
    db_session.commit()

    # The primary has changed
    assert user_twoflower.phone == userphone2
    assert accountphone.primary is False
    assert userphone2.primary is True


def test_user_del_phone(
    db_session: scoped_session, user_twoflower: models.User
) -> None:
    """Delete an phone address from a user's account."""
    assert user_twoflower.primary_phone is None
    assert len(user_twoflower.phones) == 0
    user_twoflower.add_phone('+12345678900', primary=True)
    user_twoflower.add_phone('+12345678901')
    user_twoflower.add_phone('+12345678902')
    db_session.commit()

    assert len(user_twoflower.phones) == 3
    assert user_twoflower.primary_phone is not None
    assert str(user_twoflower.primary_phone) == '+12345678900'
    assert {str(e) for e in user_twoflower.phones} == {
        '+12345678900',
        '+12345678901',
        '+12345678902',
    }

    # Delete a non-primary phone address. It will be removed
    user_twoflower.del_phone('+12345678902')
    db_session.commit()

    assert len(user_twoflower.phones) == 2
    assert user_twoflower.primary_phone is not None
    assert str(user_twoflower.primary_phone) == '+12345678900'
    assert {str(e) for e in user_twoflower.phones} == {
        '+12345678900',
        '+12345678901',
    }

    # Delete a primary phone address. The next available address will be made primary
    user_twoflower.del_phone('+12345678900')
    db_session.commit()

    assert len(user_twoflower.phones) == 1
    assert user_twoflower.primary_phone is not None
    assert str(user_twoflower.primary_phone) == '+12345678901'
    assert {str(e) for e in user_twoflower.phones} == {
        '+12345678901',
    }

    # Delete last remaining phone address. Primary will be removed
    user_twoflower.del_phone('+12345678901')
    db_session.commit()

    assert len(user_twoflower.phones) == 0
    assert user_twoflower.primary_phone is None
    assert user_twoflower.phone == ''


def test_phone_auto_primary(
    db_session: scoped_session, user_rincewind: models.User
) -> None:
    """Adding a phone without an existing primary automatically makes this primary."""
    accphone1 = user_rincewind.add_phone('+12345678900', primary=False)
    assert user_rincewind.primary_phone is None
    assert set(user_rincewind.phones) == {accphone1}
    accphone2 = user_rincewind.add_phone('+12345678901')  # Automatic primary
    assert user_rincewind.primary_phone == accphone2
    assert set(user_rincewind.phones) == {accphone1, accphone2}


def test_user_autocomplete(
    db_session: scoped_session,
    user_twoflower: models.User,
    user_rincewind: models.User,
    user_dibbler: models.User,
    user_librarian: models.User,
) -> None:
    """
    Test for User autocomplete method.

    Queries valid users defined in fixtures, as well as input that should not return
    a response.
    """
    user_rincewind.add_email('rincewind@example.org')
    db_session.commit()

    # A typical lookup with part of someone's name will find matches
    assert models.User.autocomplete('Dib') == [user_dibbler]

    # Spurious characters like `[` and `]` are ignored
    assert models.User.autocomplete('[tw]') == [user_twoflower]

    # Multiple users with the same starting character(s), sorted alphabetically
    # Both users with and without usernames are found
    assert user_librarian.fullname.startswith('The')  # The `The` prefix is tested here
    assert user_twoflower.username is None
    assert user_librarian.username is not None
    assert models.User.autocomplete('t') == [user_librarian, user_twoflower]

    # Lookup by email address
    assert models.User.autocomplete('rincewind@example.org') == [user_rincewind]

    # More spurious characters
    assert models.User.autocomplete('[]twofl') == [user_twoflower]

    # Empty searches
    assert models.User.autocomplete('@[') == []
    assert models.User.autocomplete('[[]]') == []
    assert models.User.autocomplete('[%') == []

    # TODO: Test for @username searches against external ids (requires fixtures)


@pytest.mark.parametrize('defercols', [False, True])
def test_user_all(
    db_session: scoped_session,
    user_twoflower: models.User,
    user_rincewind: models.User,
    user_ridcully: models.User,
    user_dibbler: models.User,
    user_death: models.User,
    user_mort: models.User,
    defercols: bool,
) -> None:
    """Retrieve all users matching specified criteria."""
    # Some fixtures are not used in the tests because the test determines that they
    # won't show up in the query unless specifically asked for

    # A parameter is required
    assert models.User.all() == []
    assert models.User.all(defercols=True) == []

    # Scenario 1: Lookup by buids only
    assert set(
        models.User.all(
            buids=[user_twoflower.buid, user_rincewind.buid], defercols=defercols
        )
    ) == {
        user_twoflower,
        user_rincewind,
    }

    # Scenario 2: lookup by buid or username
    assert user_ridcully.username is not None
    assert user_dibbler.username is not None
    assert set(
        models.User.all(
            buids=[user_twoflower.buid, user_rincewind.buid],
            names=[user_ridcully.username, user_dibbler.username],
            defercols=defercols,
        )
    ) == {user_twoflower, user_rincewind, user_ridcully, user_dibbler}

    # Scenario 3: lookup by usernames only
    assert set(
        models.User.all(
            names=[user_ridcully.username, user_dibbler.username],
            defercols=defercols,
        )
    ) == {user_ridcully, user_dibbler}

    # Scenario 4: querying for a merged user buid
    models.merge_accounts(user_death, user_rincewind)
    db_session.commit()

    assert set(
        models.User.all(
            buids=[user_twoflower.buid, user_rincewind.buid], defercols=defercols
        )
    ) == {
        user_twoflower,
        user_death,
    }


def test_user_add_email(
    db_session: scoped_session, user_rincewind: models.User
) -> None:
    """Test to add email address for a user."""
    # scenario 1: if primary flag is True and user has no existing email
    email1 = 'rincewind@example.org'
    useremail1 = user_rincewind.add_email(email1, primary=True)
    db_session.commit()
    assert user_rincewind.email == useremail1
    assert useremail1.email == email1
    assert useremail1.primary is True
    # scenario 2: when primary flag is True but user has existing primary email
    email2 = 'rincewind@example.com'
    useremail2 = user_rincewind.add_email(email2, primary=True)
    db_session.commit()
    assert useremail2.email == email2
    assert useremail2.primary is True
    assert useremail1.primary is False
    assert user_rincewind.email == useremail2

    # scenario 3: when primary flag is True but user has that existing email
    useremail3 = user_rincewind.add_email(email1, primary=True)
    db_session.commit()
    assert useremail3 == useremail1
    assert useremail3.primary is True
    assert useremail2.primary is False


def test_email_auto_primary(
    db_session: scoped_session, user_rincewind: models.User
) -> None:
    """Adding an email without an existing primary automatically makes this primary."""
    accemail1 = user_rincewind.add_email('rincewind@example.org', primary=False)
    assert user_rincewind.primary_email is None
    assert set(user_rincewind.emails) == {accemail1}
    accemail2 = user_rincewind.add_email('rincewind@example.com')  # Automatic primary
    assert user_rincewind.primary_email == accemail2
    assert set(user_rincewind.emails) == {accemail1, accemail2}


def test_make_email_primary(
    db_session: scoped_session, user_rincewind: models.User
) -> None:
    """Test to make an email primary for a user."""
    email = 'rincewind@example.org'
    accountemail = user_rincewind.add_email(email, primary=False)
    assert accountemail.email == email
    assert accountemail.primary is False
    assert user_rincewind.primary_email is None
    user_rincewind.primary_email = accountemail
    assert accountemail.primary is True


def test_user_password(user_twoflower: models.User) -> None:
    """Test to set user password."""
    # User account starts out with no password
    assert user_twoflower.pw_hash is None
    # User account can set a password
    user_twoflower.password = 'test-password'  # noqa: S105
    assert user_twoflower.password_is('test-password') is True
    assert user_twoflower.password_is('wrong-password') is False


def test_user_password_has_expired(
    db_session: scoped_session, user_twoflower: models.User
) -> None:
    """Test to check if password for a user has expired."""
    assert user_twoflower.pw_hash is None
    user_twoflower.password = 'test-password'  # noqa: S105
    db_session.commit()  # Required to set pw_expires_at and pw_set_at
    assert user_twoflower.pw_expires_at is not None
    assert user_twoflower.pw_set_at is not None
    assert user_twoflower.pw_expires_at > user_twoflower.pw_set_at
    assert user_twoflower.password_has_expired() is False
    user_twoflower.pw_expires_at = utcnow() - timedelta(seconds=1)
    assert user_twoflower.password_has_expired() is True


def test_password_hash_upgrade(user_twoflower: models.User) -> None:
    """Test for password hash upgrade."""
    # pw_hash contains bcrypt.hash('password')
    user_twoflower.pw_hash = (
        '$2b$12$q/TiZH08kbgiUk2W0I99sOaW5hKQ1ETgJxoAv8TvV.5WxB3dYQINO'
    )
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert not user_twoflower.password_is('incorrect')
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert not user_twoflower.password_is('incorrect', upgrade_hash=True)
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert user_twoflower.password_is('password')
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert user_twoflower.password_is('password', upgrade_hash=True)
    # Transparent upgrade to Argon2 after a successful password validation
    assert user_twoflower.pw_hash.startswith('$argon2id$')


def test_password_not_truncated(user_twoflower: models.User) -> None:
    """Argon2 passwords are not truncated at up to 1000 characters."""
    # Bcrypt passwords are truncated at 72 characters, making larger length limits
    # pointless. Argon2 passwords are not truncated for a very large size. Passlib has
    # a default max size of 4096 chars.
    # https://passlib.readthedocs.io/en/stable/lib/passlib.exc.html#passlib.exc.PasswordSizeError
    user_twoflower.password = '1' * 999 + 'a'
    assert user_twoflower.password_is('1' * 999 + 'a')
    assert not user_twoflower.password_is('1' * 999 + 'b')


def test_user_merged_user(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test for checking if user had a old id."""
    db_session.commit()
    assert user_death.state.ACTIVE
    assert user_rincewind.state.ACTIVE
    models.merge_accounts(user_death, user_rincewind)
    assert user_death.state.ACTIVE
    assert user_rincewind.state.MERGED
    assert {o.uuid for o in user_death.oldids} == {user_rincewind.uuid}


def test_user_get(
    db_session: scoped_session,
    user_twoflower: models.User,
    user_rincewind: models.User,
    user_death: models.User,
) -> None:
    """Test for User's get method."""
    # scenario 1: if both username and buid not passed
    db_session.commit()
    with pytest.raises(TypeError):
        models.User.get()  # type: ignore[call-overload]

    # scenario 2: if buid is passed
    lookup_by_buid = models.User.get(buid=user_twoflower.buid)
    assert lookup_by_buid == user_twoflower

    # scenario 3: if username is passed
    lookup_by_username = models.User.get(name='rincewind')
    assert lookup_by_username == user_rincewind

    # scenario 4: if defercols is set to True
    lookup_by_username = models.User.get(name='rincewind', defercols=True)
    assert lookup_by_username == user_rincewind

    # scenario 5: when user.state.MERGED
    assert user_rincewind.state.ACTIVE
    models.merge_accounts(user_death, user_rincewind)
    assert user_rincewind.state.MERGED

    lookup_by_buid = models.User.get(buid=user_rincewind.buid)
    assert lookup_by_buid == user_death


def test_merge_username_delete1(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test for discarding merged account username."""
    db_session.commit()  # Add SQL timestamps
    assert user_death.username
    username_death = user_death.username
    assert user_rincewind.username
    user_kept = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert user_kept is user_death
    assert user_death.username == username_death
    assert user_rincewind.username is None


def test_merge_username_delete2(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test for discarding merged account username (reversed order)."""
    db_session.commit()  # Add SQL timestamps
    assert user_death.username
    username_death = user_death.username
    assert user_rincewind.username
    user_kept = models.merge_accounts(user_rincewind, user_death)
    db_session.commit()
    assert user_kept is user_death
    assert user_death.username == username_death
    assert user_rincewind.username is None


def test_merge_username_transfer1(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test for transferring merged account username."""
    user_death.username = None  # Remove username for transfer
    db_session.commit()  # Add SQL timestamps
    assert user_death.username is None
    assert user_rincewind.username
    username_rincewind = user_rincewind.username
    user_kept = models.merge_accounts(user_death, user_rincewind)
    db_session.commit()
    assert user_kept is user_death
    assert user_death.username == username_rincewind
    assert user_rincewind.username is None


def test_merge_username_transfer2(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test for transferring merged account username (reversed order)."""
    user_death.username = None  # Remove username for transfer
    db_session.commit()  # Add SQL timestamps
    assert user_death.username is None
    assert user_rincewind.username
    username_rincewind = user_rincewind.username
    user_kept = models.merge_accounts(user_rincewind, user_death)
    db_session.commit()
    assert user_kept is user_death
    assert user_death.username == username_rincewind
    assert user_rincewind.username is None
