"""Test ProjectSponsorship views."""

import pytest

from funnel.models import SiteMembership, SponsorMembership, db


@pytest.fixture()
def org_uu_sponsorship(user_vetinari, org_uu, project_expo2010):
    sponsorship = SponsorMembership(
        granted_by=user_vetinari,
        profile=org_uu.profile,
        project=project_expo2010,
        is_promoted=True,
        label="Diamond",
    )
    db.session.add(sponsorship)
    db.session.commit()
    return sponsorship


@pytest.fixture()
def user_vetinari_site_editor(db_session, user_vetinari):
    site_editor = SiteMembership(
        user=user_vetinari, granted_by=user_vetinari, is_site_editor=True
    )
    db_session.add(site_editor)
    db.session.commit()
    return site_editor


@pytest.fixture()
def user_twoflower_not_site_editor(db_session, user_twoflower):
    not_site_editor = SiteMembership(
        user=user_twoflower, granted_by=user_twoflower, is_comment_moderator=True
    )
    db_session.add(not_site_editor)
    db.session.commit()
    return not_site_editor


@pytest.mark.parametrize(
    ('user_site_membership', 'status_code'),
    [('user_vetinari_site_editor', 200), ('user_twoflower_not_site_editor', 403)],
)
def test_check_site_editor_edit_sponsorship(  # pylint: disable=too-many-arguments
    request, client, login, org_uu_sponsorship, user_site_membership, status_code
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

    added_sponsorship = SponsorMembership.query.filter(
        SponsorMembership.is_active,
        SponsorMembership.project == project_expo2010,
        SponsorMembership.profile == org_uu.profile,
    ).one_or_none()
    assert added_sponsorship is not None
    assert added_sponsorship.profile == org_uu.profile
    assert added_sponsorship.label == label
    assert added_sponsorship.is_promoted is is_promoted


def test_sponsorship_edit(
    client, login, org_uu_sponsorship, user_vetinari_site_editor, csrf_token
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

    edited_sponsorship = SponsorMembership.query.filter(
        SponsorMembership.is_active,
        SponsorMembership.project == org_uu_sponsorship.project,
        SponsorMembership.profile == org_uu_sponsorship.profile,
    ).one_or_none()
    assert edited_sponsorship.label == "Edited"
    assert edited_sponsorship.is_promoted is False


def test_sponsorship_remove(  # pylint: disable=too-many-arguments
    client,
    login,
    org_uu_sponsorship,
    user_vetinari,
    user_vetinari_site_editor,
    csrf_token,
):
    db.session.add(user_vetinari_site_editor)
    db.session.commit()
    endpoint = org_uu_sponsorship.url_for('remove')
    login.as_(user_vetinari)
    data = {
        'csrf_token': csrf_token,
    }
    rv = client.post(endpoint, data=data)
    assert rv.status_code == 303

    no_sponsor = SponsorMembership.query.filter(
        SponsorMembership.is_active,
        SponsorMembership.project == org_uu_sponsorship.project,
        SponsorMembership.profile == org_uu_sponsorship.profile,
    ).one_or_none()
    assert no_sponsor is None
    assert org_uu_sponsorship.is_active is False
