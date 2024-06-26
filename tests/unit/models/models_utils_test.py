"""Tests for model processing utilities."""

import pytest

from funnel import models

from ...conftest import scoped_session


def test_merge_accounts_older_newer(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test to verify merger of user accounts and return new user (older first)."""
    # Scenario 1: if first user's created_at date is older than second user's
    # created_at
    db_session.commit()
    merged = models.merge_accounts(user_death, user_rincewind)
    assert merged == user_death
    assert isinstance(merged, models.User)
    # because the logic is to merge into older account
    assert user_death.state.ACTIVE
    assert user_rincewind.state.MERGED


def test_merge_accounts_newer_older(
    db_session: scoped_session, user_death: models.User, user_rincewind: models.User
) -> None:
    """Test to verify merger of user accounts and return new user (newer first)."""
    # Scenario 2: if second user's created_at date is older than first user's
    # created_at
    db_session.commit()
    merged = models.merge_accounts(user_rincewind, user_death)
    assert merged == user_death
    assert isinstance(merged, models.User)
    # because the logic is to merge into older account
    assert user_death.state.ACTIVE
    assert user_rincewind.state.MERGED


@pytest.mark.filterwarnings("ignore:Object of type <AccountEmail> not in session")
def test_getuser(  # pylint: disable=too-many-statements
    db_session: scoped_session,
    user_twoflower: models.User,
    user_rincewind: models.User,
    user_mort: models.User,
    user_wolfgang: models.User,
) -> None:
    """Test for retrieving a user from a username, email address or phone number."""
    # Confirm fixtures are as we need them to be
    assert user_twoflower.username is None
    assert user_rincewind.username == 'rincewind'
    assert user_mort.username is None
    assert user_wolfgang.username == 'wolfgang'

    # Add additional fixtures

    # Email claim (not verified)
    # User Wolfgang is attempting to claim someone else's email address
    emailclaim1 = models.AccountEmailClaim(
        account=user_wolfgang, email='twoflower@example.org'
    )
    emailclaim2 = models.AccountEmailClaim(
        account=user_wolfgang, email='rincewind@example.org'
    )
    db_session.add_all([emailclaim1, emailclaim2])
    db_session.commit()

    # Verified email addresses:
    user_twoflower.add_email('twoflower@example.org')  # This does not remove the claim
    user_rincewind.add_email('rincewind@example.com')
    user_mort.add_email('mort@example.net')

    # Verified phone numbers
    user_twoflower.add_phone('+919999999999')
    user_rincewind.add_phone('+912345678901')
    user_mort.add_phone('+12345678901')

    # Now the tests

    # Twoflower has no username, so these calls don't find anyone
    assert models.getuser('twoflower') is None
    assert models.getuser('@twoflower') is None

    # Rincewind has a username, so both variations of the call work
    assert models.getuser('rincewind') == user_rincewind
    assert models.getuser('@rincewind') == user_rincewind
    assert models.getuser('~rincewind') == user_rincewind

    # Retrieval by email works
    assert models.getuser('rincewind@example.com') == user_rincewind
    assert models.getuser('mort@example.net') == user_mort

    # Retrival by email claim only works when there is no verified email address
    assert models.getuser('twoflower@example.org') != user_wolfgang  # Claim ignored
    assert models.getuser('twoflower@example.org') == user_twoflower  # Because verified
    assert models.getuser('rincewind@example.org') == user_wolfgang  # Claim works

    # Using an unknown email address retrieves nothing
    assert models.getuser('unknown@example.org') is None

    # Retrieval by unprefixed phone number works for Indian and US phone numbers
    assert models.getuser('9999999999') is user_twoflower
    assert models.getuser('2345678901') is user_rincewind
    assert models.getuser('+12345678901') is user_mort  # +1 prefix to distinguish
    assert models.getuser('99999 99999') is user_twoflower
    assert models.getuser('23456 78901') is user_rincewind
    assert models.getuser('+1 234 567 8901') is user_mort
    assert models.getuser('99999-99999') is user_twoflower
    assert models.getuser('23456-78901') is user_rincewind
    assert models.getuser('99999.99999') is user_twoflower
    assert models.getuser('23456.78901') is user_rincewind
    assert models.getuser('+1 (234) 567 8901') is user_mort

    # Retrieval by prefixed phone number works for all phone numbers
    assert models.getuser('+919999999999') is user_twoflower
    assert models.getuser('+912345678901') is user_rincewind
    assert models.getuser('+12345678901') is user_mort
    assert models.getuser('+91 99999 99999') is user_twoflower
    assert models.getuser('+91 23456 78901') is user_rincewind
    assert models.getuser('+1 234 567 8901') is user_mort
    assert models.getuser('+91-99999-99999') is user_twoflower
    assert models.getuser('+91-23456-78901') is user_rincewind
    assert models.getuser('+1-234-567-8901') is user_mort
    assert models.getuser('+91 99999.99999') is user_twoflower
    assert models.getuser('+91 23456.78901') is user_rincewind
    assert models.getuser('+1 (234) 567-8901') is user_mort
    assert models.getuser('00919999999999') is user_twoflower
    assert models.getuser('00912345678901') is user_rincewind
    assert models.getuser('0012345678901') is user_mort

    # Suspending an account causes lookup to fail
    user_rincewind.mark_suspended()
    assert models.getuser('rincewind') is None
    assert models.getuser('@rincewind') is None
    assert models.getuser('~rincewind') is None
    assert models.getuser('rincewind@example.com') is None
    assert models.getuser('+12345678901') is user_mort
    assert models.getuser('+912345678901') is None


@pytest.mark.filterwarnings("ignore:Object of type <AccountEmail> not in session")
def test_getuser_anchor(
    db_session: scoped_session,
    user_twoflower: models.User,
    user_rincewind: models.User,
    user_mort: models.User,
    user_wolfgang: models.User,
) -> None:
    """Test for retrieving a user from a username, email address or phone number."""
    # Confirm fixtures are as we need them to be
    assert user_twoflower.username is None
    assert user_rincewind.username == 'rincewind'
    assert user_mort.username is None
    assert user_wolfgang.username == 'wolfgang'

    # Add additional fixtures

    # Email claim (not verified)
    # User Wolfgang is attempting to claim someone else's email address
    emailclaim1 = models.AccountEmailClaim(
        account=user_wolfgang, email='twoflower@example.org'
    )
    emailclaim2 = models.AccountEmailClaim(
        account=user_wolfgang, email='rincewind@example.org'
    )
    db_session.add_all([emailclaim1, emailclaim2])
    db_session.commit()

    # Verified email addresses:
    user_twoflower.add_email('twoflower@example.org')  # This does not remove the claim
    user_rincewind.add_email('rincewind@example.com')
    user_mort.add_email('mort@example.net')

    # Verified phone numbers
    user_twoflower.add_phone('+919999999999')
    user_rincewind.add_phone('+912345678901')
    user_mort.add_phone('+12345678901')

    # Now the tests

    # Twoflower has no username, so these calls don't find anyone
    assert models.getuser('twoflower', True) == (None, None)
    assert models.getuser('@twoflower', True) == (None, None)

    # Rincewind has a username, so both variations of the call work
    assert models.getuser('rincewind', True) == (user_rincewind, user_rincewind.phone)
    assert models.getuser('@rincewind', True) == (user_rincewind, user_rincewind.phone)
    assert models.getuser('~rincewind', True) == (user_rincewind, user_rincewind.phone)

    # Retrieval by email works
    assert models.getuser('rincewind@example.com', True) == (
        user_rincewind,
        user_rincewind.email,
    )
    assert models.getuser('mort@example.net', True) == (user_mort, user_mort.email)

    # Retrieval by email claim only works when there is no verified email address
    assert models.getuser('twoflower@example.org', True) != (
        user_wolfgang,
        user_wolfgang.emailclaims[0],
    )  # Claim ignored
    assert models.getuser('twoflower@example.org', True) == (
        user_twoflower,
        user_twoflower.email,
    )  # Because verified
    assert models.getuser('rincewind@example.org', True) == (
        user_wolfgang,
        user_wolfgang.emailclaims[1],
    )  # Claim works

    # Using an unknown email address retrieves nothing
    assert models.getuser('unknown@example.org', True) == (None, None)

    # Retrieval by unprefixed phone number works for Indian phone numbers
    assert models.getuser('9999999999', True) == (user_twoflower, user_twoflower.phone)
    assert models.getuser('2345678901', True) == (user_rincewind, user_rincewind.phone)
    assert models.getuser('+12345678901', True) == (user_mort, user_mort.phone)

    # Retrieval by prefixed phone number works for all phone numbers
    assert models.getuser('+919999999999', True) == (
        user_twoflower,
        user_twoflower.phone,
    )
    assert models.getuser('+912345678901', True) == (
        user_rincewind,
        user_rincewind.phone,
    )
    assert models.getuser('+12345678901', True) == (user_mort, user_mort.phone)

    # Suspending an account causes lookup to fail
    user_rincewind.mark_suspended()
    assert models.getuser('rincewind', True) == (None, None)
    assert models.getuser('@rincewind', True) == (None, None)
    assert models.getuser('~rincewind', True) == (None, None)
    assert models.getuser('rincewind@example.com', True) == (None, None)
    assert models.getuser('+912345678901', True) == (None, None)


def test_getextid(db_session: scoped_session, user_rincewind: models.User) -> None:
    """Retrieve user given service and userid."""
    service = 'sample-service'
    userid = 'rincewind@sample-service'

    externalid = models.AccountExternalId(
        service=service,
        account=user_rincewind,
        userid=userid,
        username='rincewind',
        oauth_token='sample-service-token',  # noqa: S106
        oauth_token_type='Bearer',  # noqa: S106
    )

    db_session.add(externalid)
    db_session.commit()
    result = models.getextid(service, userid=userid)
    assert isinstance(result, models.AccountExternalId)
    assert result == externalid
