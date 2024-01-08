"""Create database structure and fixtures for Cypress tests."""

from flask.cli import load_dotenv
from flask.helpers import get_load_dotenv

if __name__ == '__main__' and get_load_dotenv():
    load_dotenv()

from funnel import app  # isort:skip
from funnel.models import (  # isort:skip
    AccountEmail,
    Organization,
    SiteMembership,
    User,
    db,
    Project,
    Venue,
    VenueRoom
)
from coaster.utils import utcnow
from datetime import datetime, timedelta
from pytz import utc


def init_models():
    with app.test_request_context():
        db.drop_all()
        db.create_all()

        owner = User(
            username='profile_cypress',
            fullname='profile-cypress',
        )
        owner.password = 'profile-cypress123_St'  # nosec
        owner_email = AccountEmail(
            email='profileowner@example.com', account=owner
        )
        db.session.add(owner.add_phone('+15062345678', primary=True))

        org1 = Organization(
            name='fifthelephant', title='Fifth elephant', owner=owner
        )
        org1.is_verified = True
        org1.make_profile_public()

        project1 = Project(
            name='summer-edition', title='Summer Edition', created_by=owner,
            account=org1, location='Online', tagline='Lorem Ipsum is simply dummy text of the printing and typesetting industry.',
            description='Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book'
        )

        admin = User(username='admin_user', fullname='admin-user')
        admin.password = 'admin-user129_Ftz'  # nosec
        admin_email = AccountEmail(
            email='adminuser@example.com', account=admin
        )
        db.session.add(admin.add_phone('+918123456789', primary=True))
        org2 = Organization(
            name='rootconf', title='Rootconf', owner=admin
        )
        org2.is_verified = True
        org2.make_profile_public()

        project2 = Project(
            name='autumn-edition', title='Autumn Edition', created_by=admin,
            account=org2, location='Online', tagline='Lorem Ipsum is simply dummy text of the printing and typesetting industry.',
            description='Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book'
        )

        editor = User(username='editor_cypress', fullname='editor-cypress')
        editor.password = 'editor-cypress9_GH'  # nosec
        editor_email = AccountEmail(email='editor@example.com', account=editor)
        db.session.add(editor.add_phone('+447400123456', primary=True))

        org3 = Organization(
            name='jsfoo', title='JSFoo', owner=editor
        )
        org3.is_verified = True
        org3.make_profile_public()

        project3 = Project(
            name='monsoon-edition', title='Monsoon Edition', created_by=editor,
            account=org3, location='Online', tagline='Lorem Ipsum is simply dummy text of the printing and typesetting industry.',
            description='Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book'
        )

        promoter = User(username='promoter_user', fullname='promoter-user')
        promoter.password = 'promoter-user34_qQE'  # nosec
        promoter_email = AccountEmail(email='promoter@example.com', account=promoter)
        db.session.add(promoter.add_phone('+919845012345', primary=True))

        org4 = Organization(
            name='metarefresh', title='Metarefresh', owner=promoter
        )
        org4.is_verified = True
        org4.make_profile_public()

        project4 = Project(
            name='winter-edition', title='Winter Edition', created_by=promoter,
            account=org4, location='Online', tagline='Lorem Ipsum is simply dummy text of the printing and typesetting industry.',
            description='Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book'
        )

        usher = User(username='usher_cypress', fullname='usher-cypress')
        usher.password = 'usher-cypress566_YUt'  # nosec
        usher_email = AccountEmail(email='usher@example.com', account=usher)
        db.session.add(usher.add_phone('+918123456788', primary=True))

        org5 = Organization(
            name='kilter', title='Kilter', owner=usher
        )
        org5.is_verified = True
        org5.make_profile_public()

        project5 = Project(
            name='spring-edition', title='Spring Edition', created_by=usher,
            account=org5, location='Online', tagline='Lorem Ipsum is simply dummy text of the printing and typesetting industry.',
            description='Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book'
        )

        user = User(username='member_user', fullname='member-user')
        user.password = 'member-user341_Wer'  # nosec
        user_email = AccountEmail(email='memberuser@example.com', account=user)
        db.session.add(user.add_phone('+12015550123', primary=True))

        hguser = User(username='hg_user', fullname='hg-user')
        hguser.password = 'hg-user5_HE'  # nosec

        newuser = User(username='new_user', fullname='new-user')
        newuser.password = 'new-user11_EveryOne'  # nosec

        sm = SiteMembership(
            member=owner, is_site_editor=True, granted_by=owner
        )

        db.session.add_all(
            [
                owner,
                owner_email,
                admin,
                admin_email,
                editor,
                editor_email,
                promoter,
                promoter_email,
                usher,
                usher_email,
                user,
                user_email,
                hguser,
                newuser,
                sm,
                org1,
                org2,
                org3,
                org4,
                org5,
                project1,
                project2,
                project3,
                project4,
                project5
            ]
        )
        db.session.commit()
        project1.publish()
        project2.publish()
        project3.publish()
        project4.publish()
        venue1 = Venue(name='hasgeek', title='Hasgeek House', description='Hasgeek House second floor', project=project4, seq=1)
        venue2 = Venue(name='online', title='Online', description='Zoom', project=project4, seq=2)
        room1 = VenueRoom(name='second-floor-room', title='Second floor room', description='Hasgeek House second floor', bgcolor='F7B89E', venue=venue1, seq=1)
        room2 = VenueRoom(name='zoom', title='Zoom', description='Zoom', bgcolor='6075B1', venue=venue2, seq=2)
        project5.publish()
        project5.cfp_start_at = datetime.now(utc)
        project5.cfp_end_at = datetime.now(utc) + timedelta(days=10)
        project5.instructions = 'If you are interested in speaking at The Fifth Elephant.Submit a description of your talk, explaining the problem that your talk covers, and one concrete takeaway for audience. Talks have to give at least one practical insight to the audience'
        project5.open_cfp()
        db.session.add_all(
            [
                venue1,
                venue2,
                room1,
                room2
            ]
        )
        db.session.commit()



if __name__ == '__main__':
    init_models()
