# -*- coding: utf-8 -*-
from funnel import app
from funnel.models import Organization, Profile, User, db


def init_models():
    with app.test_request_context():
        db.create_all()
        profile_admin = User(username='admin-cypress', fullname='admin-cypress')
        profile_admin._set_password('cypress129')
        user = User(username='member-user', fullname='member-user')
        user._set_password('cypress341')
        db.session.add_all([profile_admin, user])
        test_profile = Organization(
            name="testcypressproject", title="testcypressproject"
        )
        test_profile.owners.users.append(profile_admin)
        db.session.add(test_profile)
        profile = Profile(
            name='testcypressproject',
            title="testcypressproject",
            userid=test_profile.buid,
            admin_team=test_profile.teams[0],
        )
        db.session.add(profile)
        db.session.commit()


if __name__ == "__main__":
    init_models()
