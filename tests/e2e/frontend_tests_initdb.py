# -*- coding: utf-8 -*-
from funnel import app
from funnel.models import Organization, User, db


def init_models():
    with app.test_request_context():
        db.drop_all()
        db.create_all()
        user_admin = User(username='admin-user', fullname='admin-user')
        user_admin._set_password('cypress129')
        user = User(username='member-user', fullname='member-user')
        user._set_password('cypress341')
        db.session.add_all([user_admin, user])
        test_org = Organization(name="testcypressproject", title="testcypressproject")
        test_org.owners.users.append(user_admin)
        db.session.add(test_org)
        test_org.profile.admin_team = test_org.owners
        test_org.profile.make_public()
        db.session.commit()


if __name__ == "__main__":
    init_models()
