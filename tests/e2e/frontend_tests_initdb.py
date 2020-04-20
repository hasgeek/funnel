# -*- coding: utf-8 -*-
from funnel import app
from funnel.models import User, db


def init_models():
    with app.app_context():
        db.drop_all()
        db.create_all()
        user_admin = User(username='admin-user', fullname='admin-user')
        user_admin._set_password('cypress129')
        db.session.add(user_admin)
        db.session.commit()
        user1 = User(username='member-user', fullname='member-user')
        user1._set_password('cypress341')
        db.session.add(user1)
        db.session.commit()


if __name__ == "__main__":
    init_models()
