# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import pytest
import uuid
from funnel import app
from funnel.models import db, Profile, Project, User, Label, Proposal, Team


@app.route('/usertest')
def user_test():
    from coaster.auth import current_auth
    return current_auth.user.username if current_auth.user is not None else "<anon>"


TEST_DATA = {
    'users': {
        'testuser': {
            'username': u"testuser",
            'email': u"testuser@example.com",
            },
        'testuser2': {
            'username': u"testuser2",
            'email': u"testuser2@example.com",
            },
        'testuser3': {
            'username': u"testuser3",
            'email': u"testuser3@example.com",
            },
        }
    }
# Scope: session
# These fixtures are run before every test session


@pytest.fixture(scope='session')
def test_client():
    # Flask provides a way to test your application by exposing the Werkzeug test Client
    # and handling the context locals for you.
    testing_client = app.test_client()

    # Establish an application context before running the tests.
    ctx = app.app_context()
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


@pytest.fixture(scope='session')
def new_user(test_db):
    user = User(**TEST_DATA['users']['testuser'])
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope='session')
def new_user2(test_db):
    user = User(**TEST_DATA['users']['testuser2'])
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope='session')
def new_user3(test_db):
    user = User(**TEST_DATA['users']['testuser3'])
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope='session')
def new_team(test_db, new_user):
    team = Team(title=u"Owners", owners=True, org_uuid=uuid.uuid4())
    test_db.session.add(team)
    team.users.append(new_user)
    test_db.session.commit()
    return team


@pytest.fixture(scope='session')
def new_profile(test_db, new_team):
    profile = Profile(title=u"Test Profile", description=u"Test Description",
    admin_team=new_team)
    test_db.session.add(profile)
    test_db.session.commit()
    return profile


@pytest.fixture(scope='session')
def new_project(test_db, new_profile, new_user, new_team):
    project = Project(
        profile=new_profile, user=new_user, title=u"Test Project",
        tagline=u"Test tagline", description=u"Test description",
        admin_team=new_team, review_team=new_team, checkin_team=new_team)
    test_db.session.add(project)
    test_db.session.commit()
    return project


@pytest.fixture(scope='class')
def new_main_label(test_db, new_project):
    main_label_a = Label(
        title=u"Parent Label A", project=new_project,
        description=u"A test parent label"
        )
    new_project.labels.append(main_label_a)
    test_db.session.add(main_label_a)

    label_a1 = Label(title=u"Label A1", icon_emoji=u"👍", project=new_project)
    test_db.session.add(label_a1)

    label_a2 = Label(title=u"Label A2", project=new_project)
    test_db.session.add(label_a2)

    main_label_a.options.append(label_a1)
    main_label_a.options.append(label_a2)
    main_label_a.required = True
    main_label_a.restricted = True
    test_db.session.commit()

    return main_label_a


@pytest.fixture(scope='class')
def new_main_label_unrestricted(test_db, new_project):
    main_label_b = Label(
        title=u"Parent Label B", project=new_project,
        description=u"A test parent label"
        )
    new_project.labels.append(main_label_b)
    test_db.session.add(main_label_b)

    label_b1 = Label(title=u"Label B1", icon_emoji=u"👍", project=new_project)
    test_db.session.add(label_b1)

    label_b2 = Label(title=u"Label B2", project=new_project)
    test_db.session.add(label_b2)

    main_label_b.options.append(label_b1)
    main_label_b.options.append(label_b2)
    main_label_b.required = False
    main_label_b.restricted = False
    test_db.session.commit()

    return main_label_b


@pytest.fixture(scope='class')
def new_label(test_db, new_project):
    label_b = Label(title=u"Label B", icon_emoji=u"🔟", project=new_project)
    new_project.labels.append(label_b)
    test_db.session.add(label_b)
    test_db.session.commit()
    return label_b


@pytest.fixture(scope='class')
def new_proposal(test_db, new_user, new_project):
    proposal = Proposal(
        user=new_user, speaker=new_user, project=new_project,
        title=u"Test Proposal", outline=u"Test proposal description",
        location=u"Bangalore"
        )
    test_db.session.add(proposal)
    test_db.session.commit()
    return proposal
