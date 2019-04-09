# -*- coding: utf-8 -*-

import pytest
from funnel import app as hasgeekapp, db
from funnel.models import Profile, Project, User, Label, Labelset, Proposal

# Scope: session
# These fixtures are run before every test session

@pytest.fixture(scope='session')
def test_client():
    flask_app = hasgeekapp

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
def test_db():
    # Create the database and the database table
    db.create_all()

    yield db  # this is where the testing happens!

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
def new_profile(test_db):
    profile = Profile(title=u"Test Profile", description=u"Test Description")
    test_db.session.add(profile)
    test_db.session.commit()
    return profile


@pytest.fixture(scope='module')
def new_project(test_db, new_profile, new_user):
    project = Project(
        profile=new_profile, user=new_user, title=u"Test Project",
        tagline=u"Test tagline", description=u"Test description")
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
