# -*- coding: utf-8 -*-
from funnel import app
from funnel.models import db


def init_models():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_models()
