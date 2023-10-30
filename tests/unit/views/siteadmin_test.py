"""Test siteadmin endpoints."""
# pylint: disable=redefined-outer-name

from __future__ import annotations

import pytest

from funnel import models


@pytest.fixture()
def rq_dashboard():
    """Run tests for rq_dashboard only if it is installed."""
    return pytest.importorskip('rq_dashboard')


@pytest.fixture()
def user_vetinari_sysadmin(
    db_session, user_vetinari: models.User
) -> models.SiteMembership:
    if user_vetinari.active_site_membership:
        site_membership = user_vetinari.active_site_membership.replace(
            actor=user_vetinari, is_sysadmin=True
        )
    else:
        site_membership = models.SiteMembership(
            granted_by=user_vetinari, member=user_vetinari, is_sysadmin=True
        )
        db_session.add(site_membership)
    return site_membership


@pytest.mark.usefixtures('rq_dashboard')
def test_cant_access_rq_dashboard(
    app, client, login, user_rincewind: models.User
) -> None:
    """User who is not a sysadmin cannot access RQ dashboard."""
    login.as_(user_rincewind)
    rv = client.get(app.url_for('rq_dashboard.queues_overview'))
    assert rv.status_code == 403


@pytest.mark.usefixtures('rq_dashboard', 'user_vetinari_sysadmin')
def test_can_access_rq_dashboard(
    app, client, login, user_vetinari: models.User
) -> None:
    """User who is a sysadmin can access RQ dashboard."""
    login.as_(user_vetinari)
    rv = client.get(app.url_for('rq_dashboard.queues_overview'))
    assert rv.status_code == 200
