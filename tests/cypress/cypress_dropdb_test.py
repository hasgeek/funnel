"""Drop database contents after Cypress tests."""

from funnel import app
from funnel.models import db


def drop_models():
    with app.test_request_context():
        db.drop_all()


if __name__ == "__main__":
    drop_models()
