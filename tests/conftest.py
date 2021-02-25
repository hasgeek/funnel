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

# --- New fixtures, to replace the legacy tests below as tests are updated


@pytest.fixture(scope='session')
def database(request):
    """Provide a database structure."""
    with app.app_context():
        db.create_all()

    @request.addfinalizer
    def drop_tables():
        with app.app_context():
            db.drop_all()

    return db


@pytest.fixture(scope='session')
def _db(database):
    """Dependency for db_session and db_engine fixtures."""
    return database


# Enable autouse to guard against tests that have implicit database access, or assume
# app context without a fixture
@pytest.fixture(autouse=True)
def client(db_session):
    """Provide a test client."""
    with app.app_context():  # Not required for test_client, but required for autouse
        with app.test_client() as test_client:
            yield test_client


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# --- Old fixtures, to be removed when tests are updated -------------------------------


TEST_DATA = {
    'users': {
        'testuser': {
            'name': "testuser",
            'fullname': "Test User",
            'email': "testuser@example.com",
        },
        'testuser2': {
            'name': "testuser2",
            'fullname': "Test User 2",
            'email': "testuser2@example.com",
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


@pytest.fixture
def new_user(db_session):
    user = User(**TEST_DATA['users']['testuser'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_user2(db_session):
    user = User(**TEST_DATA['users']['testuser2'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_user_owner(db_session):
    user = User(**TEST_DATA['users']['test-org-owner'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_user_admin(db_session):
    user = User(**TEST_DATA['users']['test-org-admin'])
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def new_organization(db_session, new_user_owner, new_user_admin):
    org = Organization(owner=new_user_owner, title="Test org", name='test-org')
    db_session.add(org)

    admin_membership = OrganizationMembership(
        organization=org, user=new_user_admin, is_owner=False, granted_by=new_user_owner
    )
    db_session.add(admin_membership)
    db_session.commit()
    return org


@pytest.fixture
def new_team(db_session, new_user, new_organization):
    team = Team(title="Owners", organization=new_organization)
    db_session.add(team)
    team.users.append(new_user)
    db_session.commit()
    return team


@pytest.fixture
def new_project(db_session, new_organization, new_user):
    project = Project(
        profile=new_organization.profile,
        user=new_user,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def new_project2(db_session, new_organization, new_user_owner):
    project = Project(
        profile=new_organization.profile,
        user=new_user_owner,
        title="Test Project",
        tagline="Test tagline",
        description="Test description",
        location="Test Location",
    )
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def new_main_label(db_session, new_project):
    main_label_a = Label(
        title="Parent Label A", project=new_project, description="A test parent label"
    )
    new_project.labels.append(main_label_a)
    db_session.add(main_label_a)

    label_a1 = Label(title="Label A1", icon_emoji="👍", project=new_project)
    db_session.add(label_a1)

    label_a2 = Label(title="Label A2", project=new_project)
    db_session.add(label_a2)

    main_label_a.options.append(label_a1)
    main_label_a.options.append(label_a2)
    main_label_a.required = True
    main_label_a.restricted = True
    db_session.commit()

    return main_label_a


@pytest.fixture
def new_main_label_unrestricted(db_session, new_project):
    main_label_b = Label(
        title="Parent Label B", project=new_project, description="A test parent label"
    )
    new_project.labels.append(main_label_b)
    db_session.add(main_label_b)

    label_b1 = Label(title="Label B1", icon_emoji="👍", project=new_project)
    db_session.add(label_b1)

    label_b2 = Label(title="Label B2", project=new_project)
    db_session.add(label_b2)

    main_label_b.options.append(label_b1)
    main_label_b.options.append(label_b2)
    main_label_b.required = False
    main_label_b.restricted = False
    db_session.commit()

    return main_label_b


@pytest.fixture
def new_label(db_session, new_project):
    label_b = Label(title="Label B", icon_emoji="🔟", project=new_project)
    new_project.labels.append(label_b)
    db_session.add(label_b)
    db_session.commit()
    return label_b


@pytest.fixture
def new_proposal(db_session, new_user, new_project):
    proposal = Proposal(
        user=new_user,
        speaker=new_user,
        project=new_project,
        title="Test Proposal",
        outline="Test proposal description",
        location="Bangalore",
    )
    db_session.add(proposal)
    db_session.commit()
    return proposal
