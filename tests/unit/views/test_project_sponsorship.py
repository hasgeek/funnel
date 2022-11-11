"""Test ProjectSponsorship views."""
# pylint: disable=too-many-arguments

import pytest

from funnel import models


@pytest.fixture()
def org_uu_sponsorship(db_session, user_vetinari, org_uu, project_expo2010):
    sponsorship = models.ProjectSponsorMembership(
        granted_by=user_vetinari,
        profile=org_uu.profile,
        project=project_expo2010,
        is_promoted=True,
        label="Diamond",
    )
    db_session.add(sponsorship)
    db_session.commit()
    return sponsorship


@pytest.fixture()
def user_vetinari_site_editor(db_session, user_vetinari):
    site_editor = models.SiteMembership(
        user=user_vetinari, granted_by=user_vetinari, is_site_editor=True
    )
    db_session.add(site_editor)
    db_session.commit()
    return site_editor


@pytest.fixture()
def user_twoflower_not_site_editor(db_session, user_twoflower):
    not_site_editor = models.SiteMembership(
        user=user_twoflower, granted_by=user_twoflower, is_comment_moderator=True
    )
    db_session.add(not_site_editor)
    db_session.commit()
    return not_site_editor


@pytest.mark.parametrize(
    ('user_site_membership', 'status_code'),
    [('user_vetinari_site_editor', 200), ('user_twoflower_not_site_editor', 403)],
)
def test_check_site_editor_edit_sponsorship(  # pylint: disable=too-many-arguments
    request, app, client, login, org_uu_sponsorship, user_site_membership, status_code
):
    login.as_(request.getfixturevalue(user_site_membership).user)
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
def test_sponsorship_add(  # pylint: disable=too-many-arguments
    app,
    client,
    login,
    user_vetinari_site_editor,
    org_uu,
    project_expo2010,
    label,
    is_promoted,
    csrf_token,
):
    login.as_(user_vetinari_site_editor.user)
    endpoint = project_expo2010.url_for('add_sponsor')
    data = {
        'profile': org_uu.name,
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
        models.ProjectSponsorMembership.profile == org_uu.profile,
    ).one_or_none()
    assert added_sponsorship is not None
    assert added_sponsorship.profile == org_uu.profile
    assert added_sponsorship.label == label
    assert added_sponsorship.is_promoted is is_promoted


def test_sponsorship_edit(
    app,
    client,
    login,
    org_uu_sponsorship,
    user_vetinari_site_editor,
    csrf_token,
):
    assert org_uu_sponsorship.is_promoted is True
    login.as_(user_vetinari_site_editor.user)
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
        models.ProjectSponsorMembership.profile == org_uu_sponsorship.profile,
    ).one_or_none()
    assert edited_sponsorship.label == "Edited"
    assert edited_sponsorship.is_promoted is False


def test_sponsorship_remove(  # pylint: disable=too-many-arguments
    db_session,
    app,
    client,
    login,
    org_uu_sponsorship,
    user_vetinari,
    user_vetinari_site_editor,
    csrf_token,
):
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
        models.ProjectSponsorMembership.profile == org_uu_sponsorship.profile,
    ).one_or_none()
    assert no_sponsor is None
    assert org_uu_sponsorship.is_active is False
