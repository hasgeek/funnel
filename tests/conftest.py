import pytest
from funnel import app as hasgeekapp, db
from funnel.models import Profile


@pytest.fixture(scope='module')
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


@pytest.fixture(scope='module')
def test_db():
    # Create the database and the database table
    db.create_all()

    yield db  # this is where the testing happens!

    db.drop_all()


@pytest.fixture(scope='module')
def new_profile(test_db):
    profile = Profile(title=u"Test Profile", description=u"Test Description")
    test_db.session.add(profile)
    test_db.session.commit()
    return profile
