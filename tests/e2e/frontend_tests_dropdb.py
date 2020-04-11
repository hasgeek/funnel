# -*- coding: utf-8 -*-
from funnel import app
from funnel.models import db


def drop_models():
    with app.app_context():
        db.drop_all()


if __name__ == "__main__":
    drop_models()
