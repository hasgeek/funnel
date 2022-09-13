"""Test shortlink API views."""

from flask import url_for

from furl import furl
import pytest

from funnel import models


@pytest.fixture()
def create_shortlink(app_context):
    """URL for creating a shortlink."""
    return url_for('create_shortlink')


@pytest.fixture()
def user_rincewind_site_editor(db_session, user_rincewind):
    sm = models.SiteMembership(
        user=user_rincewind, granted_by=user_rincewind, is_site_editor=True
    )
    db_session.add(sm)
    db_session.commit()
    return sm


def test_create_invalid_shortlink(app, client, user_rincewind, create_shortlink):
    """Creating a shortlink via API with invalid data will fail."""
    # A GET request will fail
    rv = client.get(create_shortlink)
    assert rv.status_code == 405

    # An external URL will be rejected
    rv = client.post(create_shortlink, data={'url': 'https://example.com'})
    assert rv.status_code == 422
    assert rv.json['error'] == 'url_invalid'

    # A relative URL will be rejected
    rv = client.post(
        create_shortlink, data={'url': user_rincewind.profile.url_for(_external=False)}
    )
    assert rv.status_code == 422
    assert rv.json['error'] == 'url_invalid'

    # A full URL to a 404 path will be rejected
    rv = client.post(
        create_shortlink,
        data={'url': f'http://{app.config["SERVER_NAME"]}/this/is/not/a/valid/url'},
    )
    assert rv.status_code == 422
    assert rv.json['error'] == 'url_invalid'


def test_create_shortlink(app, client, user_rincewind, create_shortlink):
    """Creating a shortlink via API with valid data will pass."""
    # A valid URL to an app path will be accepted
    rv = client.post(
        create_shortlink, data={'url': user_rincewind.profile.url_for(_external=True)}
    )
    assert rv.status_code == 201
    sl1 = furl(rv.json['shortlink'])
    assert sl1.netloc == app.config['SHORTLINK_DOMAIN']
    assert len(str(sl1.path)) <= 5  # API defaults to the shorter form (max 4 chars)

    # Asking for it again will return the same link
    rv = client.post(
        create_shortlink, data={'url': user_rincewind.profile.url_for(_external=True)}
    )
    assert rv.status_code == 200
    sl2 = furl(rv.json['shortlink'])
    assert sl1 == sl2

    # A valid URL can include extra query parameters
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.profile.url_for(
                _external=True, utm_campaign='webshare'
            )
        },
    )
    assert rv.status_code == 201
    sl3 = furl(rv.json['shortlink'])
    assert sl3.netloc == app.config['SHORTLINK_DOMAIN']
    assert len(str(sl3.path)) <= 5  # API defaults to the shorter form (max 4 chars)
    assert sl3.path != sl1.path  # We got a different shortlink
    assert rv.json['url'] == user_rincewind.profile.url_for(
        _external=True, utm_campaign='webshare'
    )


def test_create_shortlink_longer(app, client, user_rincewind, create_shortlink):
    rv = client.post(
        create_shortlink,
        data={'url': user_rincewind.profile.url_for(_external=True), 'shorter': '0'},
    )
    assert rv.status_code == 201
    sl1 = furl(rv.json['shortlink'])
    assert sl1.netloc == app.config['SHORTLINK_DOMAIN']
    assert len(str(sl1.path)) > 5  # The shortlink is no longer limited to 4 chars


def test_create_shortlink_name_unauthorized(client, user_rincewind, create_shortlink):
    """Asking for a custom name will fail if the user is not a site editor."""
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.profile.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 403
    assert rv.json['error'] == 'unauthorized'


@pytest.mark.usefixtures('user_rincewind_site_editor')
def test_create_shortlink_name_authorized(  # pylint: disable=too-many-arguments
    shortlinkapp, client, login, user_rincewind, user_wolfgang, create_shortlink
):
    """Asking for a custom name will work for site editors."""
    login.as_(user_rincewind)
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.profile.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 201
    assert (
        rv.json['shortlink'] == f'http://{shortlinkapp.config["SERVER_NAME"]}/rincewind'
    )

    # Asking for it again will return the same short link
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.profile.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 200
    assert (
        rv.json['shortlink'] == f'http://{shortlinkapp.config["SERVER_NAME"]}/rincewind'
    )

    # But a custom name cannot be reused for another URL
    rv = client.post(
        create_shortlink,
        data={
            'url': user_wolfgang.profile.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 422
    assert rv.json['error'] == 'unavailable'
