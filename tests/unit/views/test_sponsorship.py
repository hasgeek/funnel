import pytest

from funnel.models import SiteMembership, SponsorMembership, db


@pytest.fixture
def sponsor(user_vetinari, org_ankhmorpork, project_expo2010):
    sponsor = SponsorMembership(
        granted_by=user_vetinari,
        profile=org_ankhmorpork.profile,
        project=project_expo2010,
        is_promoted=True,
        label="Diamond",
    )
    db.session.add(sponsor)
    db.session.commit()
    return sponsor


@pytest.fixture
def site_editor(user_vetinari):
    site_editor = SiteMembership(
        user=user_vetinari, granted_by=user_vetinari, is_site_editor=True
    )
    return site_editor


@pytest.mark.parametrize(['is_site_editor', 'code'], [(True, 200), (False, 403)])
def test_check_site_editor_edit_sponsor(
    site_editor, client, is_site_editor, sponsor, user_vetinari, code
):
    user_vetinari.is_site_editor = is_site_editor
    db.session.add(site_editor)
    db.session.commit()

    endpoint = sponsor.url_for('edit_sponsor')
    with client.session_transaction() as session:
        session['userid'] = user_vetinari.userid
    rv = client.get(endpoint)
    assert rv.status_code == code


def test_sponsor_edit(
    client,
    sponsor,
    user_vetinari,
    project_expo2010,
    org_ankhmorpork,
    new_user,
    site_editor,
):
    db.session.add(site_editor)
    db.session.commit()
    endpoint = sponsor.url_for('edit_sponsor')
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    with client.session_transaction() as session:
        session['userid'] = user_vetinari.userid
    data = {
        'profile': org_ankhmorpork.name,
        'label': 'diamond-edited',
        'is_promoted': False,
        'csrf_token': csrf_token,
    }
    resp_post = client.post(endpoint, data=data)
    assert resp_post.status_code == 302

    edited_sponsor = (
        SponsorMembership.query.filter(SponsorMembership.is_active)
        .filter_by(profile_id=sponsor.profile.id)
        .one_or_none()
    )
    assert edited_sponsor.label == 'diamond-edited'
    assert edited_sponsor.is_promoted is False


def test_sponsor_remove(
    client,
    sponsor,
    user_vetinari,
    project_expo2010,
    org_ankhmorpork,
    new_user,
    site_editor,
):
    db.session.add(site_editor)
    db.session.commit()
    endpoint = sponsor.url_for('remove_sponsor')
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    with client.session_transaction() as session:
        session['userid'] = user_vetinari.userid
    data = {
        'csrf_token': csrf_token,
    }
    resp_post = client.post(endpoint, data=data)
    assert resp_post.status_code == 302

    removed_sponsor = SponsorMembership.query.filter_by(
        profile_id=sponsor.profile.id
    ).one_or_none()
    assert removed_sponsor.is_active is False
