"""Tests for Account name."""

import pytest
from sqlalchemy.exc import IntegrityError

from funnel import models

from ...conftest import scoped_session


def test_is_available_name(
    db_session: scoped_session, user_rincewind: models.User
) -> None:
    """Names are only available if valid and unused."""
    assert models.Account.is_available_name('invalid-name') is False
    # Rincewind has an account (nee profile) in default 'auto' status (not public, not
    # private even)
    assert user_rincewind.profile_state.AUTO
    # even though account is not public, username is still unavailable
    assert models.Account.is_available_name('rincewind') is False
    # any other random usernames are available
    assert models.Account.is_available_name('wizzard') is True


@pytest.mark.usefixtures('user_rincewind', 'org_uu')
@pytest.mark.parametrize('model', ['A', 'U', 'O', 'P'])
def test_validate_name_candidate(db_session: scoped_session, model: str) -> None:
    """The name validator returns error codes as expected."""
    modelref: dict[str, type[models.Account]] = {
        'A': models.Account,
        'U': models.User,
        'O': models.Organization,
        'P': models.Placeholder,
    }
    cls = modelref[model]
    assert (
        cls.validate_name_candidate(None)  # type: ignore[arg-type]
        is models.AccountNameProblem.BLANK
    )
    assert cls.validate_name_candidate('') is models.AccountNameProblem.BLANK
    assert (
        cls.validate_name_candidate('invalid-name') is models.AccountNameProblem.INVALID
    )
    assert (
        cls.validate_name_candidate('0123456789' * 7) is models.AccountNameProblem.LONG
    )
    assert cls.validate_name_candidate('0123456789' * 6) is None
    assert cls.validate_name_candidate('ValidName') is None
    assert cls.validate_name_candidate('test_reserved') is None
    assert cls.validate_name_candidate('account') is models.AccountNameProblem.RESERVED
    db_session.add(models.Placeholder(name='test_reserved'))
    assert (
        cls.validate_name_candidate('test_reserved')
        is models.AccountNameProblem.PLACEHOLDER
    )
    assert (
        cls.validate_name_candidate('Test_Reserved')
        is models.AccountNameProblem.PLACEHOLDER
    )
    assert cls.validate_name_candidate('TestReserved') is None
    assert cls.validate_name_candidate('rincewind') is models.AccountNameProblem.USER
    assert cls.validate_name_candidate('uu') is models.AccountNameProblem.ORG
    assert cls.validate_name_candidate('UU') is models.AccountNameProblem.ORG


def test_reserved_name(db_session: scoped_session) -> None:
    """Names can be reserved, with no user or organization."""
    reserved_name = models.Placeholder(name='reserved_name')
    db_session.add(reserved_name)
    retrieved_name = models.Account.query.filter(
        models.Account.name_is('reserved_name')
    ).first()
    assert retrieved_name is reserved_name
    assert isinstance(retrieved_name, models.Placeholder)

    reserved_name.name = 'Reserved_Name'
    retrieved_name = models.Account.query.filter(
        models.Account.name_is('Reserved_Name')
    ).first()
    assert retrieved_name is reserved_name


def test_unassigned_name(db_session: scoped_session) -> None:
    """Names must be assigned to a user or organization if not reserved."""
    unassigned_name = models.Account(name='unassigned')
    db_session.add(unassigned_name)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_double_assigned_name(
    db_session: scoped_session, user_rincewind: models.User
) -> None:
    """Names cannot be assigned to a user and an organization simultaneously."""
    user = models.User(username="double_assigned", fullname="User")
    org = models.Organization(
        name="double_assigned", title="Organization", owner=user_rincewind
    )
    db_session.add_all([user, org])
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cant_remove_username(
    db_session: scoped_session, user_twoflower: models.User
) -> None:
    """A user's username can be set or renamed but not removed."""
    assert user_twoflower.username is None
    user_twoflower.username = 'username'
    assert user_twoflower.username == 'username'
    user_twoflower.username = 'twoflower'
    assert user_twoflower.username == 'twoflower'

    # Can't be a blank value
    with pytest.raises(ValueError, match='Account name cannot be blank'):
        user_twoflower.username = ' '

    with pytest.raises(ValueError, match='Account name cannot be blank'):
        user_twoflower.username = ''

    # Can't be an invalid value
    with pytest.raises(ValueError, match='Account name must be a string'):
        user_twoflower.username = []  # type: ignore[assignment]

    with pytest.raises(ValueError, match='Account name must be a string'):
        user_twoflower.username = False  # type: ignore[assignment]

    with pytest.raises(ValueError, match='Account name must be a string'):
        user_twoflower.username = True  # type: ignore[assignment]


def test_cant_remove_orgname(
    db_session: scoped_session, org_uu: models.Organization
) -> None:
    """An org's name can be renamed but not removed."""
    assert org_uu.name == 'UU'
    org_uu.name = 'unseen'
    assert org_uu.name == 'unseen'


def test_name_transfer(
    db_session: scoped_session, user_mort: models.User, user_rincewind: models.User
) -> None:
    """Merging user accounts will transfer the name."""
    assert user_mort.username is None
    assert user_rincewind.username == 'rincewind'
    db_session.commit()  # Commit because merge_accounts requires created_at set
    merged = models.merge_accounts(user_mort, user_rincewind)
    assert merged == user_mort
    assert user_mort.username == 'rincewind'
    assert user_rincewind.username is None


def test_urlname(user_twoflower: models.User, user_rincewind: models.User) -> None:
    """An Account has a URL name even if there's no name."""
    assert user_twoflower.name is None
    assert user_rincewind.name == 'rincewind'
    assert user_twoflower.urlname is not None
    assert user_rincewind.urlname is not None
    assert user_twoflower.urlname == f'~{user_twoflower.uuid_zbase32}'
    assert user_rincewind.urlname == 'rincewind'
    assert (
        models.Account.query.filter(
            models.Account.name_is(user_twoflower.urlname)
        ).one()
        == user_twoflower
    )
    assert (
        models.Account.query.filter(
            models.Account.name_is(user_rincewind.urlname)
        ).one()
        == user_rincewind
    )
