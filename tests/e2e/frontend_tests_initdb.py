from funnel import app
from funnel.models import User, UserEmail, db


def init_models():
    with app.test_request_context():
        db.drop_all()
        db.create_all()

        user_admin = User(username='admin-user', fullname='admin-user')
        user_admin._set_password('cypress129_ftz')
        user_admin_email = UserEmail(email='adminuser@example.com', user=user_admin)

        user = User(username='member-user', fullname='member-user')
        user._set_password('cypress341_wer')
        user_email = UserEmail(email='memberuser@example.com', user=user)

        profile_owner = User(username='profile-cypress', fullname='profile-cypress')
        profile_owner._set_password('cypress123_st')
        profile_owner_email = UserEmail(
            email='profileowner@example.com', user=profile_owner
        )

        concierge = User(username='concierge-user', fullname='concierge-user')
        concierge._set_password('cypress341_qwe')
        concierge_email = UserEmail(email='concierge@example.com', user=concierge)

        usher = User(username='usher-cypress', fullname='usher-cypress')
        usher._set_password('cypress566_yut')
        usher_email = UserEmail(email='usher@example.com', user=usher)

        editor = User(username='editor-cypress', fullname='editor-cypress')
        editor._set_password('cypress900_ghy')
        editor_email = UserEmail(email='editor@example.com', user=editor)

        user2 = User(username='hg-user', fullname='hg-user')
        user2._set_password('cypress5678y9')

        db.session.add_all(
            [
                user_admin,
                user_admin_email,
                user,
                user_email,
                profile_owner,
                profile_owner_email,
                concierge,
                concierge_email,
                usher,
                usher_email,
                editor,
                editor_email,
                user2
            ]
        )
        db.session.commit()


if __name__ == "__main__":
    init_models()
