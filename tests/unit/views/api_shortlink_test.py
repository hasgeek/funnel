"""Test shortlink API views."""

# pylint: disable=redefined-outer-name

import pytest
from flask import url_for
from furl import furl

from funnel import models

from ...conftest import (
    AppContext,
    Flask,
    LoginFixtureProtocol,
    TestClient,
    scoped_session,
)

SHORT_SHORTLINK_WITH_PATH = 5


@pytest.fixture
def create_shortlink(app_context: AppContext) -> str:
    """URL for creating a shortlink."""
    return url_for('create_shortlink')


@pytest.fixture
def user_rincewind_site_editor(
    db_session: scoped_session, user_rincewind: models.User
) -> models.SiteMembership:
    sm = models.SiteMembership(
        member=user_rincewind, granted_by=user_rincewind, is_site_editor=True
    )
    db_session.add(sm)
    db_session.commit()
    return sm


def test_create_invalid_shortlink(
    app: Flask, client: TestClient, user_rincewind: models.User, create_shortlink: str
) -> None:
    """Creating a shortlink via API with invalid data will fail."""
    # A GET request will fail
    rv = client.get(create_shortlink)
    assert rv.status_code == 405

    # An external URL will be rejected
    rv = client.post(create_shortlink, data={'url': 'https://example.com'})
    assert rv.status_code == 422
    assert rv.json is not None
    assert rv.json['error'] == 'url_invalid'

    # A relative URL will be rejected
    rv = client.post(
        create_shortlink, data={'url': user_rincewind.url_for(_external=False)}
    )
    assert rv.status_code == 422
    assert rv.json is not None
    assert rv.json['error'] == 'url_invalid'

    # A full URL to a 404 path will be rejected
    rv = client.post(
        create_shortlink,
        data={'url': f'http://{app.config["SERVER_NAME"]}/this/is/not/a/valid/url'},
    )
    assert rv.status_code == 422
    assert rv.json is not None
    assert rv.json['error'] == 'url_invalid'


def test_create_shortlink(
    app: Flask, client: TestClient, user_rincewind: models.User, create_shortlink: str
) -> None:
    """Creating a shortlink via API with valid data will pass."""
    # A valid URL to an app path will be accepted
    rv = client.post(
        create_shortlink, data={'url': user_rincewind.url_for(_external=True)}
    )
    assert rv.status_code == 201
    assert rv.json is not None
    sl1 = furl(rv.json['shortlink'])
    assert sl1.netloc == app.config['SHORTLINK_DOMAIN']
    # API defaults to the shorter form (max 4 chars)
    assert len(str(sl1.path)) <= SHORT_SHORTLINK_WITH_PATH

    # Asking for it again will return the same link
    rv = client.post(
        create_shortlink, data={'url': user_rincewind.url_for(_external=True)}
    )
    assert rv.status_code == 200
    assert rv.json is not None
    sl2 = furl(rv.json['shortlink'])
    assert sl1 == sl2

    # A valid URL can include extra query parameters
    rv = client.post(
        create_shortlink,
        data={'url': user_rincewind.url_for(_external=True, utm_campaign='webshare')},
    )
    assert rv.status_code == 201
    assert rv.json is not None
    sl3 = furl(rv.json['shortlink'])
    assert sl3.netloc == app.config['SHORTLINK_DOMAIN']
    # API defaults to the shorter form (max 4 chars)
    assert len(str(sl3.path)) <= SHORT_SHORTLINK_WITH_PATH
    assert sl3.path != sl1.path  # We got a different shortlink
    assert rv.json['url'] == user_rincewind.url_for(
        _external=True, utm_campaign='webshare'
    )


def test_create_shortlink_longer(
    app: Flask, client: TestClient, user_rincewind: models.User, create_shortlink: str
) -> None:
    rv = client.post(
        create_shortlink,
        data={'url': user_rincewind.url_for(_external=True), 'shorter': '0'},
    )
    assert rv.status_code == 201
    assert rv.json is not None
    sl1 = furl(rv.json['shortlink'])
    assert sl1.netloc == app.config['SHORTLINK_DOMAIN']
    # The shortlink is no longer limited to 4 chars
    assert len(str(sl1.path)) > SHORT_SHORTLINK_WITH_PATH


def test_create_shortlink_name_unauthorized(
    client: TestClient, user_rincewind: models.User, create_shortlink: str
) -> None:
    """Asking for a custom name will fail if the user is not a site editor."""
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 403
    assert rv.json is not None
    assert rv.json['error'] == 'unauthorized'


@pytest.mark.filterwarnings("ignore:New instance.*conflicts with persistent instance")
@pytest.mark.usefixtures('user_rincewind_site_editor')
def test_create_shortlink_name_authorized(
    shortlinkapp: Flask,
    client: TestClient,
    login: LoginFixtureProtocol,
    user_rincewind: models.User,
    user_wolfgang: models.User,
    create_shortlink: str,
) -> None:
    """Asking for a custom name will work for site editors."""
    login.as_(user_rincewind)
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 201
    assert rv.json is not None
    assert (
        rv.json['shortlink'] == f'http://{shortlinkapp.config["SERVER_NAME"]}/rincewind'
    )

    # Asking for it again will return the same short link
    rv = client.post(
        create_shortlink,
        data={
            'url': user_rincewind.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 200
    assert rv.json is not None
    assert (
        rv.json['shortlink'] == f'http://{shortlinkapp.config["SERVER_NAME"]}/rincewind'
    )

    # But a custom name cannot be reused for another URL
    rv = client.post(
        create_shortlink,
        data={
            'url': user_wolfgang.url_for(_external=True),
            'name': 'rincewind',
        },
    )
    assert rv.status_code == 422
    assert rv.json is not None
    assert rv.json['error'] == 'unavailable'
