# -*- coding: utf-8 -*-
from funnel import app
from funnel.models import User, db


def init_models():
    with app.test_request_context():
        db.drop_all()
        db.create_all()
        user_admin = User(username='admin-user', fullname='admin-user')
        user_admin._set_password('cypress129_ftz')
        user = User(username='member-user', fullname='member-user')
        user._set_password('cypress341_wer')
        profile_owner = User(username='profile-cypress', fullname='profile-cypress')
        profile_owner._set_password('cypress123_st')
        concierge = User(username='concierge-user', fullname='concierge-user')
        concierge._set_password('cypress341_qwe')
        usher = User(username='usher-cypress', fullname='usher-cypress')
        usher._set_password('cypress566_yut')
        editor = User(username='editor-cypress', fullname='editor-cypress')
        editor._set_password('cypress900_ghy')
        db.session.add_all([user_admin, user, profile_owner, concierge, usher, editor])
        db.session.commit()


if __name__ == "__main__":
    init_models()
