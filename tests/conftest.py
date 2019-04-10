# -*- coding: utf-8 -*-

from flask import Flask
import pytest
import uuid
import coaster.app
from coaster.auth import add_auth_attribute
from flask_lastuser import Lastuser
from flask_lastuser.sqlalchemy import UserManager
from funnel.models import db, Profile, Project, User, Label, Labelset, Proposal, Team


class UserManagerMock(UserManager):
    def __init__(self, db, usermodel, teammodel=None):
        """
        This is a mocked usermanager that does no actual work but to just
        send back the test user so that the test user appears logged in
        without any actual authentication taking place.
        """
        super(UserManagerMock, self).__init__(db, usermodel, teammodel)
        self._user = None

    def load_user(self, userid, uuid=None, create=False):
        if self._user is None:
            self._user = self.usermodel.query.filter_by(username=u"testuser").first()
        return self._user

    def login_listener(self, userinfo, token):
        return self.load_user('testuserid')

    def update_teams(self, user):
        pass

    def before_request(self):
        add_auth_attribute('user', self.load_user('testuserid'))


flask_app = Flask(__name__, instance_relative_config=True)
lastuser = Lastuser()
# this sets the mock usermanager up for use
lastuser.init_usermanager(UserManagerMock(db, User, Team))
coaster.app.init_app(flask_app)
db.init_app(flask_app)
lastuser.init_app(flask_app)


@flask_app.route('/usertest')
def user_test():
    from coaster.auth import current_auth
    return current_auth.user.username if current_auth.user is not None else "anon"

# Scope: session
# These fixtures are run before every test session

@pytest.fixture(scope='session')
def test_client():
    # Flask provides a way to test your application by exposing the Werkzeug test Client
    # and handling the context locals for you.
    testing_client = flask_app.test_client()

    # Establish an application context before running the tests.
    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    # anything after yield is teardown code
    ctx.pop()


@pytest.fixture(scope='session')
def test_db(test_client):
    # Create the database and the database table
    db.create_all()

    yield db  # this is where the testing happens!

    # anything after yield is teardown code
    db.session.rollback()
    db.session.remove()
    db.drop_all()

# Scope: module
# These fixtures are executed before every test module

@pytest.fixture(scope='module')
def new_user(test_db):
    user = User(username=u"testuser", email=u"test@example.com")
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope='module')
def new_team(test_db, new_user):
    team = Team(title=u"Owners", owners=True, org_uuid=uuid.uuid4())
    test_db.session.add(team)
    team.users.append(new_user)
    test_db.session.commit()
    return team


@pytest.fixture(scope='module')
def new_profile(test_db, new_team):
    profile = Profile(title=u"Test Profile", description=u"Test Description",
    admin_team=new_team)
    test_db.session.add(profile)
    test_db.session.commit()
    return profile


@pytest.fixture(scope='module')
def new_project(test_db, new_profile, new_user, new_team):
    project = Project(
        profile=new_profile, user=new_user, title=u"Test Project",
        tagline=u"Test tagline", description=u"Test description",
        admin_team=new_team, review_team=new_team, checkin_team=new_team)
    test_db.session.add(project)
    test_db.session.commit()
    return project

# Scope: function
# These fixtures are run before every test function,
# so that changes made to the objects they return in one test function
# doesn't affect another test function.

@pytest.fixture(scope='function')
def new_labelset(test_db, new_project):
    labelset_a = Labelset(
        title=u"Labelset A", project=new_project,
        description=u"A test labelset", radio_mode=False,
        restricted=False, required=False
    )
    new_project.labelsets.append(labelset_a)
    test_db.session.add(labelset_a)
    test_db.session.commit()

    label_a1 = Label(
        title=u"Label A1", icon_emoji=u"👍", labelset=labelset_a
    )
    labelset_a.labels.append(label_a1)
    test_db.session.add(label_a1)
    test_db.session.commit()

    label_a2 = Label(
        title=u"Label A2", labelset=labelset_a
    )
    labelset_a.labels.append(label_a2)
    test_db.session.add(label_a2)
    test_db.session.commit()

    return labelset_a


@pytest.fixture(scope='function')
def new_proposal(test_db, new_user, new_project, new_labelset):
    proposal = Proposal(
        user=new_user, speaker=new_user, project=new_project,
        title=u"Test Proposal", description=u"Test proposal description",
        location=u"Bangalore"
    )
    test_db.session.add(proposal)
    test_db.session.commit()
    return proposal
