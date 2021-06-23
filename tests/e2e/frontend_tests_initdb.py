from funnel import app
from funnel.models import SiteMembership, User, UserEmail, db


def init_models():
    with app.test_request_context():
        db.drop_all()
        db.create_all()

        user_admin = User(username='admin-user', fullname='admin-user')
        user_admin._set_password('admin-user129_Ftz')
        user_admin_email = UserEmail(email='adminuser@example.com', user=user_admin)

        user = User(username='member-user', fullname='member-user')
        user._set_password('member-user341_Wer')
        user_email = UserEmail(email='memberuser@example.com', user=user)

        profile_owner = User(username='profile-cypress', fullname='profile-cypress')
        profile_owner._set_password('profile-cypress123_St')
        profile_owner_email = UserEmail(
            email='profileowner@example.com', user=profile_owner
        )

        promoter = User(username='promoter-user', fullname='promoter-user')
        promoter._set_password('promoter-user34_qQE')
        promoter_email = UserEmail(email='promoter@example.com', user=promoter)

        usher = User(username='usher-cypress', fullname='usher-cypress')
        usher._set_password('usher-cypress566_YUt')
        usher_email = UserEmail(email='usher@example.com', user=usher)

        editor = User(username='editor-cypress', fullname='editor-cypress')
        editor._set_password('editor-cypress9_GH')
        editor_email = UserEmail(email='editor@example.com', user=editor)

        user2 = User(username='hg-user', fullname='hg-user')
        user2._set_password('hg-user5_HE')

        sm = SiteMembership(
            user=profile_owner, is_site_editor=True, granted_by=profile_owner
        )

        db.session.add_all(
            [
                user_admin,
                user_admin_email,
                user,
                user_email,
                profile_owner,
                profile_owner_email,
                promoter,
                promoter_email,
                usher,
                usher_email,
                editor,
                editor_email,
                user2,
                sm,
            ]
        )
        db.session.commit()


if __name__ == "__main__":
    init_models()
