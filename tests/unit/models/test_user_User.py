from datetime import timedelta

import pytest

from coaster.utils import utcnow
import funnel.models as models

from .test_db import TestDatabaseFixture


def test_user(db_session):
    """Test for creation of user object from User model."""
    user = models.User(username='hrun', fullname="Hrun the Barbarian")
    db_session.add(user)
    db_session.commit()
    hrun = models.User.get(username='hrun')
    assert isinstance(hrun, models.User)
    assert user.username == 'hrun'
    assert user.fullname == "Hrun the Barbarian"
    assert user.state.ACTIVE
    assert hrun == user


def test_user_pickername(user_twoflower, user_rincewind):
    """Test to verify pickername contains fullname and optional username."""
    assert user_twoflower.pickername == "Twoflower"
    assert user_rincewind.pickername == "Rincewind (@rincewind)"


def test_user_is_profile_complete(db_session, user_twoflower, user_rincewind):
    """
    Test to check if user profile is complete.

    That is fullname, username and email are present.
    """
    # Both fixtures start out incomplete
    assert user_twoflower.is_profile_complete() is False
    assert user_rincewind.is_profile_complete() is False

    # Rincewind claims an email address, but it is not verified
    db_session.add(
        models.UserEmailClaim(user=user_rincewind, email='rincewind@example.org')
    )
    db_session.commit()
    assert user_rincewind.is_profile_complete() is False

    # Rincewind's profile is complete when a verified email address is added
    user_rincewind.add_email('rincewind@example.org')
    assert user_rincewind.is_profile_complete() is True

    # Email is insufficient for Twoflower
    user_twoflower.add_email('twoflower@example.org')
    assert user_twoflower.is_profile_complete() is False

    # Twoflower also needs a username
    user_twoflower.username = 'twoflower'
    assert user_twoflower.is_profile_complete() is True


def test_user_organization_owned(user_ridcully, org_uu):
    """Test for verifying organizations a user is a owner of."""
    assert list(user_ridcully.organizations_as_owner) == [org_uu]


class TestUser(TestDatabaseFixture):
    def test_user_email(self):
        """Test to retrieve UserEmail property email."""
        # scenario 1: when there is primary email address
        crusoe = models.User.get(username='crusoe')
        assert isinstance(crusoe.email, models.UserEmail)
        assert crusoe.email == crusoe.email
        # scenario 2: when there is no primary email address
        mr_pilkington = models.User(username='pilkington')
        mr_pilkington_email = models.UserEmail(
            user=mr_pilkington, email='pilkington@animalfarm.co.uk'
        )
        self.db_session.add_all([mr_pilkington, mr_pilkington_email])
        self.db_session.commit()
        assert mr_pilkington.email.email == mr_pilkington_email.email
        assert mr_pilkington.email.primary is True
        # scenario 3: when no email address is on db
        clover = models.User(username='clover')
        self.db_session.add(clover)
        self.db_session.commit()
        assert clover.email == ''

    def test_user_del_email(self):
        """Test to delete email address for a user."""
        mr_jones = models.User(username='mrjones')
        mr_jones_primary_email = models.UserEmail(
            email='mrjones@animalfarm.co.uk', user=mr_jones, primary=True
        )
        mr_jones_secondary_email = models.UserEmail(
            email='jones@animalfarm.co.uk', user=mr_jones
        )
        mr_jones_spare_email = models.UserEmail(
            email='j@animalfarm.co.uk', user=mr_jones
        )
        self.db_session.add_all(
            [
                mr_jones,
                mr_jones_primary_email,
                mr_jones_secondary_email,
                mr_jones_spare_email,
            ]
        )
        self.db_session.commit()
        # scenario 1: when email requested to be deleted is primary
        primary_email = mr_jones_primary_email.email
        mr_jones.del_email(primary_email)
        self.db_session.commit()
        result1 = mr_jones.emails
        assert isinstance(result1, list)
        assert set(result1) == {mr_jones_secondary_email, mr_jones_spare_email}
        assert mr_jones_secondary_email.primary is True
        # scenario 2: when email requested to be delete is not primary
        spare_email = mr_jones_spare_email.email
        mr_jones.del_email(spare_email)
        self.db_session.commit()
        result2 = mr_jones.emails
        assert isinstance(result2, list)
        assert result2 == [mr_jones_secondary_email]
        assert mr_jones_secondary_email.primary is True

    def test_user_phone(self):
        """Test to retrieve UserPhone property phone."""
        # scenario 1: when there is a phone set as primary
        crusoe = models.User.get(username='crusoe')
        crusoe_phone = (
            models.UserPhone.query.join(models.User)
            .filter(models.User.username == 'crusoe')
            .one()
        )
        assert isinstance(crusoe.phone, models.UserPhone)
        assert crusoe_phone == crusoe.phone
        assert crusoe.phone.primary is True
        # scenario 2: when there is a phone but not as primary
        snowball = models.User(username='snowball')
        snowball_phone = models.UserPhone(phone='+918574808032', user=snowball)
        self.db_session.add_all([snowball, snowball_phone])
        self.db_session.commit()
        assert isinstance(snowball.phone, models.UserPhone)
        assert snowball_phone == snowball.phone
        assert snowball.phone.primary is True
        # scenario 3: when there is no phone on db
        piglet = models.User.get(username='piglet')
        assert piglet.phone == ''

    def test_user_autocomplete(self):
        """
        Test for User's autocomplete method.

        Queries valid users defined in fixtures, as well as input that should not return
        a response.
        """
        crusoe = models.User.get(username='crusoe')
        oakley = models.User.get(username='oakley')
        piglet = models.User.get(username='piglet')
        # lena = models.User.get(username='lena')
        # FIXME # scenario 1: when empty query passed
        # result1 = models.User.autocomplete('*')
        # self.assertEqual(result1 or lena)
        # scenario 2: when query passed
        assert models.User.autocomplete('[oa]') == [oakley]
        assert models.User.autocomplete('Pig') == [piglet]
        assert models.User.autocomplete('crusoe@keepballin.ca') == [crusoe]
        assert models.User.autocomplete('[]cruso') == [crusoe]
        assert models.User.autocomplete('@[') == []  # Test for empty searches
        assert models.User.autocomplete('[[]]') == []

    def test_user_all(self):
        """Test for User's all method."""
        # scenario 1: when neither buids or usernames are passed
        with pytest.raises(Exception):
            models.User.all()
        crusoe = models.User.get(username='crusoe')
        oakley = models.User.get(username='oakley')
        expected_result = [oakley, crusoe]
        # scenario 2: when both buids and usernames are passed
        lookup_by_both = models.User.all(
            buids=[crusoe.buid], usernames=[oakley.username]
        )
        assert isinstance(lookup_by_both, list)
        assert set(lookup_by_both) == set(expected_result)
        # scenario 3: when only buids are passed
        lookup_by_buids = models.User.all(buids=[crusoe.buid, oakley.buid])
        assert isinstance(lookup_by_buids, list)
        assert set(lookup_by_buids) == set(expected_result)
        # scenario 4: when only usernames are passed
        lookup_by_usernames = models.User.all(
            usernames=[crusoe.username, oakley.username]
        )
        assert isinstance(lookup_by_usernames, list)
        assert set(lookup_by_usernames) == set(expected_result)
        # scenario 5: when defercols is set to True
        lookup_by_usernames = models.User.all(
            usernames=[crusoe.username, oakley.username], defercols=True
        )
        assert isinstance(lookup_by_usernames, list)
        assert set(lookup_by_usernames) == set(expected_result)
        # scenario 6: when user.state.ACTIVE
        hannibal = models.User(username='hannibal')
        assert hannibal.state.ACTIVE
        self.db_session.add(hannibal)
        self.db_session.commit()
        lookup_by_usernames = models.User.all(usernames=[hannibal.username])
        assert len(lookup_by_usernames) == 1
        assert lookup_by_usernames[0] == hannibal
        # scenario 7 : when user.state.MERGED
        jykll = models.User()
        hyde = models.User()
        self.db_session.add_all([jykll, hyde])
        self.db_session.commit()
        with self.app.test_request_context('/'):
            models.merge_users(jykll, hyde)
            self.db_session.commit()
            lookup_by_buid_merged = models.User.all(buids=[hyde.buid])
            assert isinstance(lookup_by_buid_merged, list)
            assert lookup_by_buid_merged[0].username == jykll.username


def test_user_add_email(db_session, user_rincewind):
    """Test to add email address for a user."""
    # scenario 1: if primary flag is True and user has no existing email
    email1 = 'rincewind@example.org'
    useremail1 = user_rincewind.add_email(email1, primary=True)
    db_session.commit()
    assert user_rincewind.email == useremail1
    assert useremail1.email == email1
    assert useremail1.primary is True
    # scenario 2: when primary flag is True but user has existing primary email
    email2 = 'rincewind@example.com'
    useremail2 = user_rincewind.add_email(email2, primary=True)
    db_session.commit()
    assert useremail2.email == email2
    assert useremail2.primary is True
    assert useremail1.primary is False
    assert user_rincewind.email == useremail2  # type: ignore[unreachable]

    # scenario 3: when primary flag is True but user has that existing email
    useremail3 = user_rincewind.add_email(email1, primary=True)  # type: ignore[unreachable]
    db_session.commit()
    assert useremail3 == useremail1
    assert useremail3.primary is True
    assert useremail2.primary is False


def test_make_email_primary(user_rincewind):
    """Test to make an email primary for a user."""
    email = 'rincewind@example.org'
    useremail = user_rincewind.add_email(email)
    assert useremail.email == email
    assert useremail.primary is False
    assert user_rincewind.primary_email is None
    user_rincewind.primary_email = useremail
    assert useremail.primary is True


def test_user_password(user_twoflower):
    """Test to set user password."""
    # User account starts out with no password
    assert user_twoflower.pw_hash is None
    # User account can set a password
    user_twoflower.password = 'test-password'
    assert user_twoflower.password_is('test-password') is True
    assert user_twoflower.password_is('wrong-password') is False


def test_user_password_has_expired(db_session, user_twoflower):
    """Test to check if password for a user has expired."""
    assert user_twoflower.pw_hash is None
    user_twoflower.password = 'test-password'
    db_session.commit()  # Required to set pw_expires_at and pw_set_at
    assert user_twoflower.pw_expires_at > user_twoflower.pw_set_at
    assert user_twoflower.password_has_expired() is False
    user_twoflower.pw_expires_at = utcnow() - timedelta(seconds=1)
    assert user_twoflower.password_has_expired() is True


def test_password_hash_upgrade(user_twoflower):
    """Test for password hash upgrade."""
    # pw_hash contains bcrypt.hash('password')
    user_twoflower.pw_hash = (
        '$2b$12$q/TiZH08kbgiUk2W0I99sOaW5hKQ1ETgJxoAv8TvV.5WxB3dYQINO'
    )
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert not user_twoflower.password_is('incorrect')
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert not user_twoflower.password_is('incorrect', upgrade_hash=True)
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert user_twoflower.password_is('password')
    assert user_twoflower.pw_hash.startswith('$2b$')
    assert user_twoflower.password_is('password', upgrade_hash=True)
    # Transparent upgrade to Argon2 after a successful password validation
    assert user_twoflower.pw_hash.startswith('$argon2id$')


def test_user_merged_user(db_session, user_death, user_rincewind):
    """Test for checking if user had a old id."""
    db_session.commit()
    assert user_death.state.ACTIVE
    assert user_rincewind.state.ACTIVE
    models.merge_users(user_death, user_rincewind)
    assert user_death.state.ACTIVE
    assert user_rincewind.state.MERGED
    assert {o.uuid for o in user_death.oldids} == {user_rincewind.uuid}


def test_user_get(db_session, user_twoflower, user_rincewind, user_death):
    """Test for User's get method."""
    # scenario 1: if both username and buid not passed
    db_session.commit()
    with pytest.raises(TypeError):
        models.User.get()

    # scenario 2: if buid is passed
    lookup_by_buid = models.User.get(buid=user_twoflower.buid)
    assert lookup_by_buid == user_twoflower

    # scenario 3: if username is passed
    lookup_by_username = models.User.get(username='rincewind')
    assert lookup_by_username == user_rincewind

    # scenario 4: if defercols is set to True
    lookup_by_username = models.User.get(username='rincewind', defercols=True)
    assert lookup_by_username == user_rincewind

    # scenario 5: when user.state.MERGED
    assert user_rincewind.state.ACTIVE
    models.merge_users(user_death, user_rincewind)
    assert user_rincewind.state.MERGED

    lookup_by_buid = models.User.get(buid=user_rincewind.buid)
    assert lookup_by_buid == user_death
