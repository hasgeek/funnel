"""Drop database contents after Cypress tests."""

from flask.cli import load_dotenv
from flask.helpers import get_load_dotenv

if __name__ == '__main__' and get_load_dotenv():
    load_dotenv()

from funnel import app  # isort:skip
from funnel.models import db  # isort:skip


def drop_models():
    with app.test_request_context():
        db.drop_all()


if __name__ == '__main__':
    drop_models()
