# -*- coding: utf-8 -*-


import pytest

from funnel import app
from funnel.models import (
    Label,
    Organization,
    OrganizationMembership,
    Project,
    Proposal,
    Team,
    User,
    db,
)


@app.route('/usertest')
def user_test():
    from coaster.auth import current_auth

    return current_auth.user.username if current_auth.user is not None else "<anon>"


TEST_DATA = {
    'users': {
        'testuser': {
            'name': "testuser",
            'fullname': "Test User",
            'email': "testuser@example.com",
        },
        'test-org-owner': {
            'name': "test-org-owner",
            'fullname': "Test User 2",
            'email': "testorgowner@example.com",
        },
        'test-org-admin': {
            'name': "test-org-admin",
            'fullname': "Test User 3",
            'email': "testorgadmin@example.com",
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
def new_user_owner(test_db):
    user = User(**TEST_DATA['users']['test-org-owner'])
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope='session')
def new_user_admin(test_db):
    user = User(**TEST_DATA['users']['test-org-admin'])
    test_db.session.add(user)
    test_db.session.commit()
    return user


@pytest.fixture(scope='session')
def new_organization(test_db, new_user_owner, new_user_admin):
    org = Organization(
        owner=new_user_owner, title="Test org", name='test-org', is_public_profile=True
    )
    test_db.session.add(org)

    admin_membership = OrganizationMembership(organization=org, user=new_user_admin)
    test_db.session.add(admin_membership)
    test_db.session.commit()
    return org


@pytest.fixture(scope='session')
def new_team(test_db, new_user, new_organization):
    team = Team(title="Owners", organization=new_organization)
    test_db.session.add(team)
    team.users.append(new_user)
    test_db.session.commit()
    return team


@pytest.fixture(scope='session')
def new_project(test_db, new_organization, new_user):
    project = Project(
        profile=new_organization.profile,
        user=new_user,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    test_db.session.add(project)
    test_db.session.commit()
    return project


@pytest.fixture(scope='session')
def new_project2(test_db, new_organization, new_user_owner):
    project = Project(
        profile=new_organization.profile,
        user=new_user_owner,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    test_db.session.add(project)
    test_db.session.commit()
    return project


@pytest.fixture(scope='class')
def new_main_label(test_db, new_project):
    main_label_a = Label(
        title="Parent Label A", project=new_project, description="A test parent label"
    )
    new_project.labels.append(main_label_a)
    test_db.session.add(main_label_a)

    label_a1 = Label(title="Label A1", icon_emoji="👍", project=new_project)
    test_db.session.add(label_a1)

    label_a2 = Label(title="Label A2", project=new_project)
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
        title="Parent Label B", project=new_project, description="A test parent label"
    )
    new_project.labels.append(main_label_b)
    test_db.session.add(main_label_b)

    label_b1 = Label(title="Label B1", icon_emoji="👍", project=new_project)
    test_db.session.add(label_b1)

    label_b2 = Label(title="Label B2", project=new_project)
    test_db.session.add(label_b2)

    main_label_b.options.append(label_b1)
    main_label_b.options.append(label_b2)
    main_label_b.required = False
    main_label_b.restricted = False
    test_db.session.commit()

    return main_label_b


@pytest.fixture(scope='class')
def new_label(test_db, new_project):
    label_b = Label(title="Label B", icon_emoji="🔟", project=new_project)
    new_project.labels.append(label_b)
    test_db.session.add(label_b)
    test_db.session.commit()
    return label_b


@pytest.fixture(scope='class')
def new_proposal(test_db, new_user, new_project):
    proposal = Proposal(
        user=new_user,
        speaker=new_user,
        project=new_project,
        title="Test Proposal",
        outline="Test proposal description",
        location="Bangalore",
    )
    test_db.session.add(proposal)
    test_db.session.commit()
    return proposal
