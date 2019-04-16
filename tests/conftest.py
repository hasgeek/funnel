import pytest
from funnel import app as hasgeekapp, db
from funnel.models import Profile, Project, User


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
