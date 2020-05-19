from funnel import db
from funnel.models import (
    AuthClient,
    AuthClientTeamPermissions,
    AuthClientUserPermissions,
    Organization,
    SMSMessage,
    Team,
    User,
    UserEmail,
    UserPhone,
)


class Fixtures(object):
    def make_fixtures(self):
        """
        Create users, attach them to organizations. Create test client app, add test
        resource, action and message.
        """
        crusoe = User(username="crusoe", fullname="Crusoe Celebrity Dachshund")
        oakley = User(username="oakley")
        piglet = User(username="piglet")
        nameless = User(fullname="Nameless")

        db.session.add_all([crusoe, oakley, piglet, nameless])
        self.crusoe = crusoe
        self.oakley = oakley
        self.piglet = piglet
        self.nameless = nameless

        crusoe_email = UserEmail(
            email="crusoe@keepballin.ca", user=crusoe, primary=True
        )
        crusoe_phone = UserPhone(phone="+8080808080", user=crusoe, primary=True)
        oakley_email = UserEmail(email="huh@keepballin.ca", user=oakley)
        db.session.add_all([crusoe_email, crusoe_phone, oakley_email])
        self.crusoe_email = crusoe_email
        self.crusoe_phone = crusoe_phone

        batdog = Organization(name='batdog', title='Batdog', owner=crusoe)
        db.session.add(batdog)
        self.batdog = batdog

        specialdachs = Organization(
            name="specialdachs", title="Special Dachshunds", owner=oakley
        )
        db.session.add(specialdachs)
        self.specialdachs = specialdachs

        auth_client = AuthClient(
            title="Batdog Adventures",
            organization=batdog,
            confidential=True,
            namespace='fun.batdogadventures.com',
            website="http://batdogadventures.com",
        )
        db.session.add(auth_client)
        self.auth_client = auth_client

        dachshunds = Team(title="Dachshunds", organization=batdog)
        db.session.add(dachshunds)
        self.dachshunds = dachshunds

        auth_client_team_permissions = AuthClientTeamPermissions(
            team=dachshunds, auth_client=auth_client, access_permissions="admin"
        )
        self.auth_client_team_permissions = auth_client_team_permissions
        db.session.add(auth_client_team_permissions)

        auth_client_user_permissions = AuthClientUserPermissions(
            user=crusoe, auth_client=auth_client
        )
        db.session.add(auth_client_user_permissions)
        self.auth_client_user_permissions = auth_client_user_permissions

        message = SMSMessage(
            phone_number=crusoe_phone.phone,
            transactionid="Ruff" * 5,
            message="Wuff Wuff",
        )
        db.session.add(message)
        db.session.commit()
        self.message = message
