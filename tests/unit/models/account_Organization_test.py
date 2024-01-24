"""Tests for UserExternalId model."""


import pytest

from coaster.sqlalchemy import StateTransitionError

from funnel import models

from ...conftest import scoped_session


def test_organization_init(user_twoflower: models.User) -> None:
    """Test for initializing a Organization instance."""
    name = 'inn_sewer_ants'
    title = 'Inn-sewer-ants-polly-sea'
    org = models.Organization(name=name, title=title, owner=user_twoflower)
    assert isinstance(org, models.Organization)
    assert org.title == title
    assert org.name == name


def test_organization_get(
    db_session: scoped_session, user_twoflower: models.User
) -> None:
    """Test for retrieving an organization."""
    name = 'inn_sewer_ants'
    title = 'Inn-sewer-ants-polly-sea'
    org = models.Organization(name=name, title=title, owner=user_twoflower)
    db_session.add(org)
    db_session.commit()
    # scenario 1: when neither name or buid are passed
    with pytest.raises(TypeError):
        models.Organization.get()  # type: ignore[call-overload]
    # scenario 2: when buid is passed
    buid = org.buid
    get_by_buid = models.Organization.get(buid=buid)
    assert get_by_buid == org
    # scenario 3: when username is passed
    get_by_name = models.Organization.get(name=name)
    assert get_by_name == org
    # scenario 4: when defercols is set to True
    get_by_name_with_defercols = models.Organization.get(name=name, defercols=True)
    assert get_by_name_with_defercols == org


def test_organization_all(
    db_session: scoped_session,
    org_ankhmorpork: models.Organization,
    org_citywatch: models.Organization,
    org_uu: models.Organization,
) -> None:
    """Test for getting all organizations (takes buid or name optionally)."""
    db_session.commit()
    # scenario 1: when neither buids nor names are given
    assert not models.Organization.all()
    # scenario 2: when buids are passed
    orglist = {org_ankhmorpork, org_citywatch}
    all_by_buids = models.Organization.all(buids=[_org.buid for _org in orglist])
    org_names = [_org.name for _org in orglist if _org.name is not None]
    assert set(all_by_buids) == orglist
    # scenario 3: when org names are passed
    all_by_names = models.Organization.all(names=org_names)
    assert set(all_by_names) == orglist
    # scenario 4: when defercols is set to True for names
    all_by_names_with_defercols = models.Organization.all(names=org_names)
    assert set(all_by_names_with_defercols) == orglist
    # scenario 5: when defercols is set to True for buids
    all_by_buids_with_defercols = models.Organization.all(
        buids=[_org.buid for _org in orglist]
    )
    assert set(all_by_buids_with_defercols) == orglist


def test_organization_pickername(org_uu: models.Organization) -> None:
    """Test for checking Organization's pickername."""
    assert isinstance(org_uu.pickername, str)
    assert org_uu.pickername == f'{org_uu.title} (@{org_uu.name})'


def test_organization_name(org_ankhmorpork: models.Organization) -> None:
    """Test for retrieving and setting an Organization's name."""
    with pytest.raises(ValueError, match='Invalid account name'):
        org_ankhmorpork.name = '35453496*%&^$%^'
    with pytest.raises(ValueError, match='Invalid account name'):
        org_ankhmorpork.name = '-Insurgent'
    org_ankhmorpork.name = 'anky'
    assert org_ankhmorpork.name == 'anky'
    org_ankhmorpork.name = 'AnkhMorpork'
    assert org_ankhmorpork.name == 'AnkhMorpork'


def test_organization_suspend_restore(
    db_session: scoped_session, org_citywatch: models.Organization
) -> None:
    """Test for an organization being suspended and restored."""
    db_session.commit()
    assert org_citywatch.state.ACTIVE
    assert not org_citywatch.state.SUSPENDED

    org_citywatch.mark_suspended()
    db_session.commit()
    assert not org_citywatch.state.ACTIVE
    assert org_citywatch.state.SUSPENDED

    org_citywatch.mark_active()
    db_session.commit()
    assert org_citywatch.state.ACTIVE
    assert not org_citywatch.state.SUSPENDED

    with pytest.raises(StateTransitionError):
        org_citywatch.mark_active()

    org_citywatch.mark_suspended()
    with pytest.raises(StateTransitionError):
        org_citywatch.mark_suspended()
