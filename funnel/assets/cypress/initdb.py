# -*- coding: utf-8 -*-


from funnel import app
from funnel.models import User, db


def init_models():
    with app.app_context():
        db.drop_all()
        db.create_all()

        u = User(username="admin-cypress", email="cypressuser1@gmail.com")
        db.session.add(u)
        db.session.commit()

        u = User(username="member-user", email="cypressmemberuser@gmail.com")
        db.session.add(u)
        db.session.commit()


if __name__ == "__main__":
    init_models()
