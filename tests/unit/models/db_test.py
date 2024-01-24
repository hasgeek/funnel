"""Fixtures for legacy tests."""
# pylint: disable=attribute-defined-outside-init,redefined-outer-name

import pytest

from funnel import models

from ...conftest import Flask, TestClient, scoped_session


class Fixtures:
    def make_fixtures(  # pylint: disable=too-many-locals
        self, db_session: scoped_session
    ) -> None:
        """
        Create fixtures.

        Create users, attach them to organizations. Create test client app, add test
        resource, action and message.
        """
        crusoe = models.User(username="crusoe", fullname="Crusoe Celebrity Dachshund")
        oakley = models.User(username="oakley")
        piglet = models.User(username="piglet")
        nameless = models.User(fullname="Nameless")

        db_session.add_all([crusoe, oakley, piglet, nameless])
        self.crusoe = crusoe
        self.oakley = oakley
        self.piglet = piglet
        self.nameless = nameless

        crusoe_email = models.AccountEmail(
            email="crusoe@keepballin.ca", account=crusoe, primary=True
        )
        crusoe_phone = models.AccountPhone(
            phone='+918123456789', account=crusoe, primary=True
        )
        oakley_email = models.AccountEmail(email="huh@keepballin.ca", account=oakley)
        db_session.add_all([crusoe_email, crusoe_phone, oakley_email])
        self.crusoe_email = crusoe_email
        self.crusoe_phone = crusoe_phone

        batdog = models.Organization(name='batdog', title='Batdog', owner=crusoe)
        db_session.add(batdog)
        self.batdog = batdog

        specialdachs = models.Organization(
            name="specialdachs", title="Special Dachshunds", owner=oakley
        )
        db_session.add(specialdachs)
        self.specialdachs = specialdachs

        auth_client = models.AuthClient(
            title="Batdog Adventures",
            account=batdog,
            confidential=True,
            website="http://batdogadventures.com",
        )
        db_session.add(auth_client)
        self.auth_client = auth_client

        dachshunds = models.Team(title="Dachshunds", account=batdog)
        db_session.add(dachshunds)
        self.dachshunds = dachshunds

        auth_client_team_permissions = models.AuthClientTeamPermissions(
            team=dachshunds, auth_client=auth_client, access_permissions="admin"
        )
        self.auth_client_team_permissions = auth_client_team_permissions
        db_session.add(auth_client_team_permissions)

        auth_client_permissions = models.AuthClientPermissions(
            account=crusoe, auth_client=auth_client
        )
        db_session.add(auth_client_permissions)
        self.auth_client_permissions = auth_client_permissions

        message = models.SmsMessage(
            phone=crusoe_phone.phone,
            transactionid="Ruff" * 5,
            message="Wuff Wuff",
        )
        db_session.add(message)
        db_session.commit()
        self.message = message


class TestDatabaseFixture:
    @pytest.fixture(autouse=True)
    def _pytest_fixtures(
        self, app: Flask, client: TestClient, db_session: scoped_session
    ) -> None:
        self.client = client
        self.db_session = db_session
        self.app = app
        self.fixtures = Fixtures()
        self.fixtures.make_fixtures(db_session)
