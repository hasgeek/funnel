"""Test ProjectSponsorship views."""
# pylint: disable=redefined-outer-name

from typing import cast

import pytest
from flask import Flask

from funnel import models

from ...conftest import LoginFixtureProtocol, TestClient, scoped_session


@pytest.fixture()
def org_uu_sponsorship(
    db_session: scoped_session,
    user_vetinari: models.User,
    org_uu: models.Organization,
    project_expo2010: models.Project,
) -> models.ProjectSponsorMembership:
    sponsorship = models.ProjectSponsorMembership(
        granted_by=user_vetinari,
        member=org_uu,
        project=project_expo2010,
        is_promoted=True,
        label="Diamond",
    )
    db_session.add(sponsorship)
    db_session.commit()
    return sponsorship


@pytest.fixture()
def user_vetinari_site_editor(
    db_session: scoped_session, user_vetinari: models.User
) -> models.SiteMembership:
    site_editor = models.SiteMembership(
        member=user_vetinari, granted_by=user_vetinari, is_site_editor=True
    )
    db_session.add(site_editor)
    db_session.commit()
    return site_editor


@pytest.fixture()
def user_twoflower_not_site_editor(
    db_session: scoped_session, user_twoflower: models.User
) -> models.SiteMembership:
    not_site_editor = models.SiteMembership(
        member=user_twoflower, granted_by=user_twoflower, is_comment_moderator=True
    )
    db_session.add(not_site_editor)
    db_session.commit()
    return not_site_editor


@pytest.mark.parametrize(
    ('user_site_membership', 'status_code'),
    [('user_vetinari_site_editor', 200), ('user_twoflower_not_site_editor', 403)],
)
def test_check_site_editor_edit_sponsorship(
    request: pytest.FixtureRequest,
    app: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    org_uu_sponsorship: models.ProjectSponsorMembership,
    user_site_membership: str,
    status_code: int,
) -> None:
    login.as_(request.getfixturevalue(user_site_membership).member)
    endpoint = org_uu_sponsorship.url_for('edit')
    rv = client.get(endpoint)
    assert rv.status_code == status_code


@pytest.mark.parametrize(
    ('label', 'is_promoted'),
    [
        (None, False),
        (None, True),
        ('Test sponsor1', False),
        ('Test sponsor2', True),
    ],
)
def test_sponsorship_add(
    app: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    user_vetinari_site_editor: models.SiteMembership,
    org_uu: models.Organization,
    project_expo2010: models.Project,
    label: str | None,
    is_promoted: bool,
    csrf_token: str,
) -> None:
    login.as_(cast(models.User, user_vetinari_site_editor.member))
    endpoint = project_expo2010.url_for('add_sponsor')
    data: dict = {
        'member': org_uu.name,
        'label': label,
        'csrf_token': csrf_token,
    }
    if is_promoted:
        # Checkboxes are only included in HTML forms when they are checked
        data['is_promoted'] = True

    rv = client.post(endpoint, data=data)
    assert rv.status_code == 303

    added_sponsorship = models.ProjectSponsorMembership.query.filter(
        models.ProjectSponsorMembership.is_active,
        models.ProjectSponsorMembership.project == project_expo2010,
        models.ProjectSponsorMembership.member == org_uu,
    ).one_or_none()
    assert added_sponsorship is not None
    assert added_sponsorship.member == org_uu
    assert added_sponsorship.label == label
    assert added_sponsorship.is_promoted is is_promoted


def test_sponsorship_edit(
    app: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    org_uu_sponsorship: models.ProjectSponsorMembership,
    user_vetinari_site_editor: models.SiteMembership,
    csrf_token: str,
) -> None:
    assert org_uu_sponsorship.is_promoted is True
    login.as_(cast(models.User, user_vetinari_site_editor.member))
    endpoint = org_uu_sponsorship.url_for('edit')
    data = {
        'label': "Edited",
        'csrf_token': csrf_token,
        # Set is_promoted to False by excluding it from form data (how HTML forms work)
    }
    rv = client.post(endpoint, data=data)
    assert rv.status_code == 303

    edited_sponsorship = models.ProjectSponsorMembership.query.filter(
        models.ProjectSponsorMembership.is_active,
        models.ProjectSponsorMembership.project == org_uu_sponsorship.project,
        models.ProjectSponsorMembership.member == org_uu_sponsorship.member,
    ).one()
    assert edited_sponsorship.label == "Edited"
    assert edited_sponsorship.is_promoted is False


def test_sponsorship_remove(
    db_session: scoped_session,
    app: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    org_uu_sponsorship: models.ProjectSponsorMembership,
    user_vetinari: models.User,
    user_vetinari_site_editor: models.SiteMembership,
    csrf_token: str,
) -> None:
    db_session.add(user_vetinari_site_editor)
    db_session.commit()
    endpoint = org_uu_sponsorship.url_for('remove')
    login.as_(user_vetinari)
    data = {
        'csrf_token': csrf_token,
    }
    rv = client.post(endpoint, data=data)
    assert rv.status_code == 303

    no_sponsor = models.ProjectSponsorMembership.query.filter(
        models.ProjectSponsorMembership.is_active,
        models.ProjectSponsorMembership.project == org_uu_sponsorship.project,
        models.ProjectSponsorMembership.member == org_uu_sponsorship.member,
    ).one_or_none()
    assert no_sponsor is None
    assert org_uu_sponsorship.is_active is False
