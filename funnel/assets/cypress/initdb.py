# -*- coding: utf-8 -*-

import uuid

from funnel import app
from funnel.models import Profile, Team, User, db


def init_models():
    with app.app_context():
        db.drop_all()
        db.create_all()

        u = User(username="testuser", email="testuser@example.com")
        db.session.add(u)
        db.session.commit()

        team = Team(title=u"Owners", owners=True, org_uuid=uuid.uuid4())
        db.session.add(team)
        team.users.append(u)
        db.session.commit()

        profile = Profile(
            title=u"Test Profile", description=u"Test Description", admin_team=team
        )
        db.session.add(profile)
        db.session.commit()


if __name__ == "__main__":
    init_models()
