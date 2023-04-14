"""Test ProjectSponsorMembership."""
import pytest

from coaster.sqlalchemy import ImmutableColumnError
from funnel import models


@pytest.fixture()
def citywatch_sponsor(db_session, project_expo2010, org_citywatch, user_vetinari):
    """Add City Watch as a sponsor of Expo 2010."""
    sponsor = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=org_citywatch.profile,
        granted_by=user_vetinari,
        is_promoted=False,
        seq=1,
    )
    db_session.add(sponsor)
    return sponsor


@pytest.fixture()
def uu_sponsor(db_session, project_expo2010, org_uu, user_vetinari):
    """Add Unseen University as a sponsor of Expo 2010."""
    sponsor = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=org_uu.profile,
        granted_by=user_vetinari,
        is_promoted=False,
        seq=2,
    )
    db_session.add(sponsor)
    return sponsor


@pytest.fixture()
def dibbler_sponsor(db_session, project_expo2010, user_dibbler, user_vetinari):
    """Add CMOT Dibbler as a promoted sponsor of Expo 2010."""
    sponsor = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=user_dibbler.profile,
        granted_by=user_vetinari,
        is_promoted=True,
        label="Snack Stand",
        seq=3,
    )
    db_session.add(sponsor)
    return sponsor


def test_auto_seq(
    db_session,
    project_expo2010,
    org_citywatch,
    org_uu,
    user_dibbler,
    user_vetinari,
) -> None:
    """Sequence numbers are auto-issued in commit order."""
    sponsor1 = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=org_citywatch.profile,
        granted_by=user_vetinari,
        is_promoted=False,
    )
    db_session.add(sponsor1)
    db_session.commit()

    sponsor2 = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=org_uu.profile,
        granted_by=user_vetinari,
        is_promoted=False,
    )
    db_session.add(sponsor2)
    db_session.commit()

    sponsor3 = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=user_dibbler.profile,
        granted_by=user_vetinari,
        is_promoted=True,
        label="Snack Stand",
    )
    db_session.add(sponsor3)
    db_session.commit()

    # We have sponsors in sequence
    assert sponsor1.seq == 1
    assert sponsor2.seq == 2
    assert sponsor3.seq == 3


def test_expo_has_sponsors(
    db_session,
    project_expo2010,
    dibbler_sponsor,
    uu_sponsor,
    citywatch_sponsor,
    org_citywatch,
    org_uu,
    user_dibbler,
) -> None:
    """Project Expo 2010 has sponsors in a specific order."""
    db_session.commit()
    assert list(project_expo2010.sponsors) == [
        org_citywatch.profile,
        org_uu.profile,
        user_dibbler.profile,
    ]


def test_expo_sponsor_reorder(
    db_session, project_expo2010, citywatch_sponsor, uu_sponsor, dibbler_sponsor
) -> None:
    """Sponsors can be re-ordered."""
    db_session.commit()

    # We have sponsors in sequence
    assert citywatch_sponsor.seq == 1
    assert uu_sponsor.seq == 2
    assert dibbler_sponsor.seq == 3

    dibbler_sponsor.reorder_before(citywatch_sponsor)
    db_session.commit()

    assert citywatch_sponsor.seq == 2
    assert uu_sponsor.seq == 3
    assert dibbler_sponsor.seq == 1


def test_expo_sponsor_seq_reissue(
    db_session,
    project_expo2010,
    citywatch_sponsor,
    uu_sponsor,
    dibbler_sponsor,
    user_dibbler,
    user_wolfgang,
) -> None:
    """If the the last sponsor is dropped, the next sponsor gets their spot."""
    db_session.commit()

    # We have sponsors in sequence
    assert citywatch_sponsor.seq == 1
    assert uu_sponsor.seq == 2
    assert dibbler_sponsor.seq == 3

    # Dibbler removes self and introduces Wolfgang
    dibbler_sponsor.revoke(actor=user_dibbler)
    wolfgang_sponsor = models.ProjectSponsorMembership(
        project=project_expo2010,
        profile=user_wolfgang.profile,
        granted_by=user_dibbler,
        is_promoted=True,
        label="Bite Stand",
    )
    db_session.add(wolfgang_sponsor)
    db_session.commit()
    # Wolfgang gets the same last position in the sequence, and can reorder
    assert wolfgang_sponsor.seq == 3
    wolfgang_sponsor.reorder_before(uu_sponsor)
    db_session.commit()
    assert citywatch_sponsor.seq == 1
    assert wolfgang_sponsor.seq == 2
    assert uu_sponsor.seq == 3
    # Dibbler's old record is untouched as it's revoked
    assert dibbler_sponsor.seq == 3
    assert dibbler_sponsor.is_active is False
    assert list(project_expo2010.sponsors) == [
        citywatch_sponsor.profile,
        wolfgang_sponsor.profile,
        uu_sponsor.profile,
    ]


def test_change_promoted_flag(db_session, project_expo2010, citywatch_sponsor) -> None:
    """Change sponsor is_promoted flag."""
    assert citywatch_sponsor.is_promoted is False
    # Flag can be changed with a revision
    new_record = citywatch_sponsor.replace(
        actor=citywatch_sponsor.granted_by, is_promoted=True
    )
    assert new_record != citywatch_sponsor
    assert new_record.is_promoted is True

    noop_record = new_record.replace(actor=new_record.granted_by, is_promoted=True)
    assert noop_record == new_record

    with pytest.raises(ImmutableColumnError):
        new_record.is_promoted = False


def test_change_label(db_session, project_expo2010, citywatch_sponsor) -> None:
    """Change sponsor label."""
    assert citywatch_sponsor.label is None
    # Flag can be changed with a revision
    new_record = citywatch_sponsor.replace(
        actor=citywatch_sponsor.granted_by, label="Guards! Guards!"
    )
    assert new_record != citywatch_sponsor
    assert new_record.label == "Guards! Guards!"

    noop_record = new_record.replace(
        actor=new_record.granted_by, label="Guards! Guards!"
    )
    assert noop_record == new_record

    with pytest.raises(ImmutableColumnError):
        new_record.label = None


def test_sponsor_offered_roles(db_session, project_expo2010, citywatch_sponsor) -> None:
    """Sponsors don't get a role from the sponsor membership."""
    assert citywatch_sponsor.offered_roles == set()


def test_sponsor_subject_role(
    db_session, citywatch_sponsor, user_vimes, user_rincewind
) -> None:
    """Sponsor account admins get subject role on the membership."""
    assert 'subject' in citywatch_sponsor.roles_for(user_vimes)
    assert 'subject' not in citywatch_sponsor.roles_for(user_rincewind)
