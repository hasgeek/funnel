"""Fixtures for legacy tests."""
# pylint: disable=attribute-defined-outside-init

from funnel import models


class Fixtures:
    def make_fixtures(self, db_session):  # pylint: disable=too-many-locals
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

        crusoe_email = models.UserEmail(
            email="crusoe@keepballin.ca", user=crusoe, primary=True
        )
        crusoe_phone = models.UserPhone(phone="+8080808080", user=crusoe, primary=True)
        oakley_email = models.UserEmail(email="huh@keepballin.ca", user=oakley)
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
            organization=batdog,
            confidential=True,
            website="http://batdogadventures.com",
        )
        db_session.add(auth_client)
        self.auth_client = auth_client

        dachshunds = models.Team(title="Dachshunds", organization=batdog)
        db_session.add(dachshunds)
        self.dachshunds = dachshunds

        auth_client_team_permissions = models.AuthClientTeamPermissions(
            team=dachshunds, auth_client=auth_client, access_permissions="admin"
        )
        self.auth_client_team_permissions = auth_client_team_permissions
        db_session.add(auth_client_team_permissions)

        auth_client_user_permissions = models.AuthClientUserPermissions(
            user=crusoe, auth_client=auth_client
        )
        db_session.add(auth_client_user_permissions)
        self.auth_client_user_permissions = auth_client_user_permissions

        message = models.SMSMessage(
            phone_number=crusoe_phone.phone,
            transactionid="Ruff" * 5,
            message="Wuff Wuff",
        )
        db_session.add(message)
        db_session.commit()
        self.message = message
