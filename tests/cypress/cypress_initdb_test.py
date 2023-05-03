"""Create database structure and fixtures for Cypress tests."""

from funnel import app
from funnel.models import AccountEmail, Organization, SiteMembership, User, db


def init_models():
    with app.test_request_context():
        db.drop_all()
        db.create_all()

        user_admin = User(username='admin-user', fullname='admin-user')
        user_admin.password = 'admin-user129_Ftz'  # nosec
        user_admin_email = AccountEmail(
            email='adminuser@example.com', account=user_admin
        )
        db.session.add(user_admin.add_phone('+918123456789', primary=True))

        user = User(username='member-user', fullname='member-user')
        user.password = 'member-user341_Wer'  # nosec
        user_email = AccountEmail(email='memberuser@example.com', account=user)
        db.session.add(user.add_phone('+12015550123', primary=True))

        profile_owner = User(
            username='profile-cypress',
            fullname='profile-cypress',
        )
        profile_owner.password = 'profile-cypress123_St'  # nosec
        profile_owner_email = AccountEmail(
            email='profileowner@example.com', account=profile_owner
        )
        db.session.add(profile_owner.add_phone('+15062345678', primary=True))

        promoter = User(username='promoter-user', fullname='promoter-user')
        promoter.password = 'promoter-user34_qQE'  # nosec
        promoter_email = AccountEmail(email='promoter@example.com', account=promoter)

        usher = User(username='usher-cypress', fullname='usher-cypress')
        usher.password = 'usher-cypress566_YUt'  # nosec
        usher_email = AccountEmail(email='usher@example.com', account=usher)

        editor = User(username='editor-cypress', fullname='editor-cypress')
        editor.password = 'editor-cypress9_GH'  # nosec
        editor_email = AccountEmail(email='editor@example.com', account=editor)
        db.session.add(editor.add_phone('+447400123456', primary=True))

        user2 = User(username='hg-user', fullname='hg-user')
        user2.password = 'hg-user5_HE'  # nosec

        user3 = User(username='new-user', fullname='new-user')
        user3.password = 'new-user11_EveryOne'  # nosec

        sm = SiteMembership(
            member=profile_owner, is_site_editor=True, granted_by=profile_owner
        )

        org = Organization(
            name='testcypressproject', title='testcypressproject', owner=profile_owner
        )
        org.is_verified = True

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
                user3,
                sm,
                org,
            ]
        )
        db.session.commit()


if __name__ == "__main__":
    init_models()
