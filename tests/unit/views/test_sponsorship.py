import pytest

from funnel.models import SiteMembership, SponsorMembership, db


@pytest.fixture
def org_uu_sponsor(user_vetinari, org_uu, project_expo2010):
    org_uu_sponsor = SponsorMembership(
        granted_by=user_vetinari,
        profile=org_uu.profile,
        project=project_expo2010,
        is_promoted=True,
        label="Diamond",
    )
    db.session.add(org_uu)
    db.session.commit()
    return org_uu_sponsor


@pytest.fixture
def user_vetinari_site_editor(user_vetinari):
    user_vetinari_site_editor = SiteMembership(
        user=user_vetinari, granted_by=user_vetinari, is_site_editor=True
    )
    return user_vetinari_site_editor


@pytest.fixture
def user_twoflower_not_site_editor(user_twoflower):
    user_twoflower_not_site_editor = SiteMembership(
        user=user_twoflower, granted_by=user_twoflower, is_comment_moderator=True
    )
    return user_twoflower_not_site_editor


@pytest.mark.parametrize(
    ['user', 'code'],
    [('user_vetinari_site_editor', 200), ('user_twoflower_not_site_editor', 403)],
)
def test_check_site_editor_edit_sponsor(client, org_uu_sponsor, code, user, request):
    db.session.add(request.getfixturevalue(user))
    db.session.commit()
    endpoint = org_uu_sponsor.url_for('edit')
    with client.session_transaction() as session:
        session['userid'] = request.getfixturevalue(user).user.userid
    rv = client.get(endpoint)
    assert rv.status_code == code


def test_sponsor_edit(
    client,
    org_uu_sponsor,
    user_vetinari,
    user_vetinari_site_editor,
):
    db.session.add(user_vetinari_site_editor)
    db.session.commit()
    endpoint = org_uu_sponsor.url_for('edit')
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    with client.session_transaction() as session:
        session['userid'] = user_vetinari_site_editor.user.userid
    data = {
        'profile': org_uu_sponsor.profile.name,
        'label': 'diamond-edited',
        'is_promoted': False,
        'csrf_token': csrf_token,
    }
    resp_post = client.post(endpoint, data=data)
    assert resp_post.status_code == 302

    edited_sponsor = (
        SponsorMembership.query.filter(SponsorMembership.is_active)
        .filter_by(profile_id=org_uu_sponsor.profile.id)
        .one_or_none()
    )
    assert edited_sponsor.label == 'diamond-edited'
    assert edited_sponsor.is_promoted is False


def test_sponsor_remove(
    client,
    org_uu_sponsor,
    user_vetinari,
    user_vetinari_site_editor,
):
    db.session.add(user_vetinari_site_editor)
    db.session.commit()
    endpoint = org_uu_sponsor.url_for('remove')
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    with client.session_transaction() as session:
        session['userid'] = user_vetinari.userid
    data = {
        'csrf_token': csrf_token,
    }
    resp_post = client.post(endpoint, data=data)
    assert resp_post.status_code == 302

    removed_sponsor = SponsorMembership.query.filter_by(
        profile_id=org_uu_sponsor.profile.id
    ).one_or_none()
    assert removed_sponsor.is_active is False
