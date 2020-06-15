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

# TODO: Replace all `scope='module'` with `scope='session'` when lastuser tests have
# been migrated to pytest. Currently they do a db.drop_all(), breaking the
# test_db_structure fixture


@pytest.fixture(scope='module')
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


@pytest.fixture(scope='module')
def test_db_structure(test_client):
    # Create all database tables
    db.create_all()
    yield db
    # Drop all database tables
    db.drop_all()


@pytest.fixture(scope='function')
def test_db(test_db_structure):
    yield test_db_structure  # this is where the testing happens!
    # anything after yield is teardown code
    test_db_structure.session.rollback()
    test_db_structure.session.remove()


@pytest.fixture(scope='module')
def create_user(test_db_structure):
    user = User(**TEST_DATA['users']['testuser'])
    test_db_structure.session.add(user)
    test_db_structure.session.commit()
    return user


@pytest.fixture(scope='function')
def new_user(test_db_structure, create_user):
    user = test_db_structure.session.merge(create_user)
    return user


@pytest.fixture(scope='module')
def create_user_owner(test_db_structure):
    user = User(**TEST_DATA['users']['test-org-owner'])
    test_db_structure.session.add(user)
    test_db_structure.session.commit()
    return user


@pytest.fixture(scope='function')
def new_user_owner(test_db_structure, create_user_owner):
    user_owner = test_db_structure.session.merge(create_user_owner)
    return user_owner


@pytest.fixture(scope='module')
def create_user_admin(test_db_structure):
    user = User(**TEST_DATA['users']['test-org-admin'])
    test_db_structure.session.add(user)
    test_db_structure.session.commit()
    return user


@pytest.fixture(scope='function')
def new_user_admin(test_db_structure, create_user_admin):
    user_admin = test_db_structure.session.merge(create_user_admin)
    return user_admin


@pytest.fixture(scope='module')
def create_organization(test_db_structure, create_user_owner, create_user_admin):
    user_owner = test_db_structure.session.merge(create_user_owner)
    user_admin = test_db_structure.session.merge(create_user_admin)
    org = Organization(owner=user_owner, title="Test org", name='test-org')
    test_db_structure.session.add(org)

    admin_membership = OrganizationMembership(
        organization=org, user=user_admin, is_owner=False, granted_by=user_owner
    )
    test_db_structure.session.add(admin_membership)
    test_db_structure.session.commit()
    return org


@pytest.fixture(scope='function')
def new_organization(test_db_structure, create_organization):
    organization = test_db_structure.session.merge(create_organization)
    return organization


@pytest.fixture(scope='module')
def create_team(test_db_structure, create_user, create_organization):
    user = test_db_structure.session.merge(create_user)
    organization = test_db_structure.session.merge(create_organization)
    team = Team(title="Owners", organization=organization)
    test_db_structure.session.add(team)
    team.users.append(user)
    test_db_structure.session.commit()
    return team


@pytest.fixture(scope='function')
def new_team(test_db_structure, create_team):
    team = test_db_structure.session.merge(create_team)
    return team


@pytest.fixture(scope='module')
def create_project(test_db_structure, create_organization, create_user):
    user = test_db_structure.session.merge(create_user)
    organization = test_db_structure.session.merge(create_organization)
    project = Project(
        profile=organization.profile,
        user=user,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    test_db_structure.session.add(project)
    test_db_structure.session.commit()
    return project


@pytest.fixture(scope='function')
def new_project(test_db_structure, create_project):
    project = test_db_structure.session.merge(create_project)
    return project


@pytest.fixture(scope='module')
def create_project2(test_db_structure, create_organization, create_user_owner):
    user_owner = test_db_structure.session.merge(create_user_owner)
    organization = test_db_structure.session.merge(create_organization)
    project = Project(
        profile=organization.profile,
        user=user_owner,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    test_db_structure.session.add(project)
    test_db_structure.session.commit()
    return project


@pytest.fixture(scope='function')
def new_project2(test_db_structure, create_project2):
    project2 = test_db_structure.session.merge(create_project2)
    return project2


@pytest.fixture(scope='module')
def create_main_label(test_db_structure, create_project):
    project = test_db_structure.session.merge(create_project)
    main_label_a = Label(
        title="Parent Label A", project=project, description="A test parent label"
    )
    project.labels.append(main_label_a)
    test_db_structure.session.add(main_label_a)

    label_a1 = Label(title="Label A1", icon_emoji="👍", project=project)
    test_db_structure.session.add(label_a1)

    label_a2 = Label(title="Label A2", project=project)
    test_db_structure.session.add(label_a2)

    main_label_a.options.append(label_a1)
    main_label_a.options.append(label_a2)
    main_label_a.required = True
    main_label_a.restricted = True
    test_db_structure.session.commit()

    return main_label_a


@pytest.fixture(scope='function')
def new_main_label(test_db_structure, create_main_label):
    main_label = test_db_structure.session.merge(create_main_label)
    return main_label


@pytest.fixture(scope='module')
def create_main_label_unrestricted(test_db_structure, create_project):
    project = test_db_structure.session.merge(create_project)
    main_label_b = Label(
        title="Parent Label B", project=project, description="A test parent label"
    )
    project.labels.append(main_label_b)
    test_db_structure.session.add(main_label_b)

    label_b1 = Label(title="Label B1", icon_emoji="👍", project=project)
    test_db_structure.session.add(label_b1)

    label_b2 = Label(title="Label B2", project=project)
    test_db_structure.session.add(label_b2)

    main_label_b.options.append(label_b1)
    main_label_b.options.append(label_b2)
    main_label_b.required = False
    main_label_b.restricted = False
    test_db_structure.session.commit()

    return main_label_b


@pytest.fixture(scope='function')
def new_main_label_unrestricted(test_db_structure, create_main_label_unrestricted):
    main_label_unrestricted = test_db_structure.session.merge(
        create_main_label_unrestricted
    )
    return main_label_unrestricted


@pytest.fixture(scope='module')
def create_label(test_db_structure, create_project):
    project = test_db_structure.session.merge(create_project)
    label_b = Label(title="Label B", icon_emoji="🔟", project=project)
    project.labels.append(label_b)
    test_db_structure.session.add(label_b)
    test_db_structure.session.commit()
    return label_b


@pytest.fixture(scope='function')
def new_label(test_db_structure, create_label):
    label = test_db_structure.session.merge(create_label)
    return label


@pytest.fixture(scope='module')
def create_proposal(test_db_structure, create_user, create_project):
    user = test_db_structure.session.merge(create_user)
    project = test_db_structure.session.merge(create_project)
    proposal = Proposal(
        user=user,
        speaker=user,
        project=project,
        title="Test Proposal",
        outline="Test proposal description",
        location="Bangalore",
    )
    test_db_structure.session.add(proposal)
    test_db_structure.session.commit()
    return proposal


@pytest.fixture(scope='function')
def new_proposal(test_db_structure, create_proposal):
    proposal = test_db_structure.session.merge(create_proposal)
    return proposal
