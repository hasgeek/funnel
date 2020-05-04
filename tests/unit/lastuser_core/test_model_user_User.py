# -*- coding: utf-8 -*-

from datetime import timedelta

from sqlalchemy.orm.collections import InstrumentedList

import pytest

from coaster.utils import utcnow
from funnel import db
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestUser(TestDatabaseFixture):
    def test_user(self):
        """
        Test for creation of user object from User model
        """
        user = models.User(username='lena', fullname="Lena Audrey Dachshund")
        db.session.add_all([user])
        db.session.commit()
        lena = models.User.get(username='lena')
        assert isinstance(lena, models.User)
        assert user.username == 'lena'
        assert user.fullname == "Lena Audrey Dachshund"

    def test_user_is_valid_name(self):
        """
        Test to check if given is a valid username associated with the user
        """
        crusoe = models.User.get(username='crusoe')
        # scenario 1: not a valid username
        number_one = models.User(username='number1', fullname='Number One')
        assert number_one.is_valid_name('Number1') is False
        # scenario 2: a valid username but not the username of instance passed
        assert crusoe.is_valid_name("oakley") is False
        # scenario 3: a existing username
        crusoe.is_valid_name("crusoe") is True
        # scenario 4: a existing org
        batdog = models.Organization.get(name='batdog')
        assert crusoe.is_valid_name(batdog.name) is False

    def test_user_pickername(self):
        """
        Test to verify fullname and username (if any)
        """
        # scenario 1: when username exists
        crusoe = models.User.get(username='crusoe')
        result = crusoe.pickername
        expected_result = '{fullname} (@{username})'.format(
            fullname=crusoe.fullname, username=crusoe.username
        )
        assert result == expected_result
        # scenario 2: when username doesnt exist
        mr_fedrick = models.User(fullname='Mr. Fedrick')
        result = mr_fedrick.pickername
        expected_result = '{fullname}'.format(fullname=mr_fedrick.fullname)
        assert result == expected_result

    def test_user_is_profile_complete(self):
        """
        Test to check if user profile is complete that is fullname, username
        and email are present
        """
        crusoe = models.User.get(username='crusoe')
        assert crusoe.is_profile_complete() is True
        lena = models.User()
        db.session.add(lena)
        db.session.commit()
        assert lena.is_profile_complete() is False

    def test_user_organization_owned(self):
        """
        Test for verifying organizations a user is a owner of
        """
        crusoe = models.User.get(username='crusoe')
        batdog = models.Organization.get(name='batdog')
        result = crusoe.organizations_as_owner
        assert list(result) == [batdog]

    def test_user_organizations_as_owner(self):
        """
        Test for verifying list of organizations this user is an owner of
        """
        oakley = models.User.get(username='oakley')
        specialdachs = models.Organization.get(name='specialdachs')
        result = oakley.organizations_as_owner
        assert list(result) == [specialdachs]

    def test_user_username(self):
        """
        Test to retrieve User property username
        """
        crusoe = models.User.get(username='crusoe')
        result = crusoe.username
        assert isinstance(result, str)
        assert crusoe.username == result

    def test_user_email(self):
        """
        Test to retrieve UserEmail property email
        """
        # scenario 1: when there is primary email address
        crusoe = models.User.get(username='crusoe')
        assert isinstance(crusoe.email, models.UserEmail)
        assert crusoe.email == crusoe.email
        # scenario 2: when there is no primary email address
        mr_pilkington = models.User(username='pilkington')
        mr_pilkington_email = models.UserEmail(
            user=mr_pilkington, email='pilkington@animalfarm.co.uk'
        )
        db.session.add_all([mr_pilkington, mr_pilkington_email])
        db.session.commit()
        assert mr_pilkington.email.email == mr_pilkington_email.email
        assert mr_pilkington.email.primary is True
        # scenario 3: when no email address is on db
        clover = models.User(username='clover')
        db.session.add(clover)
        db.session.commit()
        assert clover.email == ''

    def test_user_del_email(self):
        """
        Test to delete email address for a user
        """
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
        db.session.add_all(
            [
                mr_jones,
                mr_jones_primary_email,
                mr_jones_secondary_email,
                mr_jones_spare_email,
            ]
        )
        db.session.commit()
        # scenario 1: when email requested to be deleted is primary
        primary_email = mr_jones_primary_email.email
        mr_jones.del_email(primary_email)
        db.session.commit()
        result1 = mr_jones.emails
        assert isinstance(result1, list)
        result1 == [mr_jones_secondary_email, mr_jones_spare_email]
        mr_jones_secondary_email.primary is True
        # scenario 2: when email requested to be delete is not primary
        spare_email = mr_jones_spare_email.email
        mr_jones.del_email(spare_email)
        db.session.commit()
        result2 = mr_jones.emails
        assert isinstance(result2, list)
        result2 == [mr_jones_secondary_email]
        mr_jones_secondary_email.primary is True

    def test_user_phone(self):
        """
        Test to retrieve UserPhone property phone
        """
        # scenario 1: when there is a phone set as primary
        crusoe = models.User.get(username='crusoe')
        crusoe_phone = (
            models.UserPhone.query.join(models.User)
            .filter(models.User.username == 'crusoe')
            .one()
        )
        assert isinstance(crusoe.phone, models.UserPhone)
        assert crusoe_phone == crusoe.phone
        crusoe.phone.primary is True
        # scenario 2: when there is a phone but not as primary
        snowball = models.User(username='snowball')
        snowball_phone = models.UserPhone(phone='+918574808032', user=snowball)
        db.session.add_all([snowball, snowball_phone])
        db.session.commit()
        assert isinstance(snowball.phone, models.UserPhone)
        assert snowball_phone == snowball.phone
        snowball.phone.primary is True
        # scenario 3: when there is no phone on db
        piglet = models.User.get(username='piglet')
        assert piglet.phone == ''

    def test_user_password(self):
        """
        Test to set user password
        """
        # Scenario 1: Set None as password
        castle = models.User(username='castle', fullname='Rick Castle')
        castle.password = None
        assert castle.pw_hash is None
        # Scenario 2: Set valid password
        kate = models.User(username='kate', fullname='Detective Kate Beckette')
        kate.password = '12thprecinct'
        db.session.add(kate)
        db.session.commit()
        result = models.User.get(buid=kate.buid)
        assert len(result.pw_hash) == 60
        assert result.password_is('12thprecinct') is True
        assert result.pw_expires_at > result.pw_set_at

    def test_user_password_has_expired(self):
        """
        Test to check if password for a user has expired
        """
        alexis = models.User(username='alexis', fullname='Alexis Castle')
        alexis.password = 'unfortunateincidents'
        alexis.pw_expires_at = utcnow() + timedelta(0, 0, 1)
        db.session.add(alexis)
        db.session.commit()
        result = models.User.get(buid=alexis.buid)
        assert result is not None
        assert alexis.password_has_expired() is True

    def test_user_password_is(self):
        """
        Test to retrieve hashed password for a user
        """
        # scenario 1: no password been set
        oldmajor = models.User(username='oldmajor')
        assert oldmajor.password_is('oinkoink') is False
        # scenario 3: if password has been set
        dumbeldore = models.User('dumbeldore', fullname='Albus Dumberldore')
        dumbeldore_password = 'dissendium'
        dumbeldore.password = dumbeldore_password
        assert dumbeldore.password_is(dumbeldore_password) is True

    def test_user_is_active(self):
        """
        Test for user's ACTIVE status
        where ACTIVE = 0 indicates a Regular, active user
        """
        crusoe = models.User.get(username='crusoe')
        assert crusoe.status == 0
        oakley = models.User.get(username='oakley')
        oakley.status = 1
        assert oakley.status == 1

    def test_user_autocomplete(self):
        """
        Test for User's autocomplete method
        """
        crusoe = models.User.get(username='crusoe')
        oakley = models.User.get(username='oakley')
        piglet = models.User.get(username='piglet')
        # lena = models.User.get(username=u'lena')
        # FIXME # scenario 1: when empty query passed
        # result1 = models.User.autocomplete(u'*')
        # self.assertEqual(result1 or lena)
        # scenario 2: when query passed
        queries = ["[oa]", "Pig", "crusoe@keepballin.ca"]
        result2 = []
        for each in queries:
            result2.append(models.User.autocomplete(each))
        for result in result2:
            assert isinstance(result, list)
            for each in result:
                assert isinstance(each, models.User)
        query_for_oakley = models.User.autocomplete(queries[0])
        assert query_for_oakley == [oakley]
        query_for_piglet = models.User.autocomplete(queries[1])
        assert query_for_piglet == [piglet]
        query_for_crusoe = models.User.autocomplete(queries[2])
        assert query_for_crusoe == [crusoe]

    def test_user_merged_user(self):
        """
        Test for checking if user had a old id
        """
        # ## Merge a user onto an older user ###
        crusoe = models.User.get(username='crusoe')
        crusoe2 = models.User(username="crusoe2", fullname="Crusoe2")
        db.session.add(crusoe2)
        db.session.commit()
        with self.app.test_request_context('/'):
            merged_user = models.merge_users(crusoe, crusoe2)
            db.session.commit()
            # ## DONE ###
            assert isinstance(merged_user, models.User)
            # because the logic is to merge into older account so merge status set on newer account
            assert crusoe.status == 0
            assert crusoe2.status == 2
            assert merged_user.username == "crusoe"
            assert isinstance(merged_user.oldids, InstrumentedList)
            assert crusoe.oldids == merged_user.oldids

    def test_user_get(self):
        """
        Test for User's get method
        """
        # scenario 1: if both username and buid not passed
        with pytest.raises(TypeError):
            models.User.get()
        crusoe = models.User.get(username='crusoe')
        piglet = models.User.get(username='piglet')
        # scenario 2: if buid is passed
        lookup_by_buid = models.User.get(buid=crusoe.buid)
        assert isinstance(lookup_by_buid, models.User)
        assert lookup_by_buid.buid == crusoe.buid
        # scenario 3: if username is passed
        lookup_by_username = models.User.get(username="crusoe")
        assert isinstance(lookup_by_username, models.User)
        assert lookup_by_username.username == "crusoe"
        # scenario 4: if defercols is set to True
        lookup_by_username = models.User.get(username="crusoe", defercols=True)
        assert isinstance(lookup_by_username, models.User)
        assert lookup_by_username.username == "crusoe"
        # scenario 5: when user.status is active
        lector = models.User()
        lector.status = models.USER_STATUS.ACTIVE
        db.session.add(lector)
        db.session.commit()
        lookup_by_buid_status = models.User.get(buid=lector.buid)
        assert isinstance(lookup_by_buid_status, models.User)
        assert lookup_by_buid_status.status == lector.status
        # scenario 6 : when user.status is USER_STATUS.MERGED
        piglet = models.User.get(username='piglet')
        piggy = models.User(username='piggy')
        db.session.add(piggy)
        db.session.commit()
        with self.app.test_request_context('/'):
            models.merge_users(piglet, piggy)
            db.session.commit()
            lookup_by_buid_merged = models.User.get(buid=piggy.buid)
            assert isinstance(lookup_by_buid_merged, models.User)
            assert lookup_by_buid_merged.username == piglet.username

    def test_user_all(self):
        """
        Test for User's all method
        """
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
        assert lookup_by_both == expected_result
        # scenario 3: when only buids are passed
        lookup_by_buids = models.User.all(buids=[crusoe.buid, oakley.buid])
        assert isinstance(lookup_by_buids, list)
        assert lookup_by_buids == expected_result
        # scenario 4: when only usernames are passed
        lookup_by_usernames = models.User.all(
            usernames=[crusoe.username, oakley.username]
        )
        assert isinstance(lookup_by_usernames, list)
        assert lookup_by_usernames == expected_result
        # scenario 5: when defercols is set to True
        lookup_by_usernames_defercols = models.User.all(
            usernames=[crusoe.username, oakley.username], defercols=True
        )
        lookup_by_usernames_defercols
        assert isinstance(lookup_by_usernames, list)
        assert lookup_by_usernames == expected_result
        # scenario 6: when user.status is active
        hannibal = models.User(username='hannibal')
        hannibal.status = models.USER_STATUS.ACTIVE
        db.session.add(hannibal)
        db.session.commit()
        lookup_by_buid_status = models.User.all(usernames=[hannibal.username])
        assert isinstance(lookup_by_buid_status, list)
        assert lookup_by_buid_status[0].status == hannibal.status
        # scenario 7 : when user.status is USER_STATUS.MERGED
        jykll = models.User()
        hyde = models.User()
        db.session.add_all([jykll, hyde])
        db.session.commit()
        with self.app.test_request_context('/'):
            models.merge_users(jykll, hyde)
            db.session.commit()
            lookup_by_buid_merged = models.User.all(buids=[hyde.buid])
            assert isinstance(lookup_by_buid_merged, list)
            assert lookup_by_buid_merged[0].username == jykll.username

    def test_user_add_email(self):
        """
        Test to add email address for a user
        """
        # scenario 1: if primary flag is True and user has no existing email
        mr_whymper = models.User(username='whymper')
        whymper_email = 'whmmm@animalfarm.co.uk'
        whymper_result = mr_whymper.add_email(whymper_email, primary=True)
        assert whymper_result.email == whymper_email
        # # scenario 2: when primary flag is True but user has existing primary email
        crusoe = models.User.get(username='crusoe')
        crusoe_new_email = 'crusoe@batdog.ca'
        crusoe_result = crusoe.add_email(email=crusoe_new_email, primary=True)
        assert crusoe_result.email == crusoe_new_email
        # # scenario 3: when primary flag is True but user has existing email same as one passed
        crusoe_existing_email = 'crusoe@keepballin.ca'
        crusoe_result = crusoe.add_email(crusoe_existing_email, primary=True)
        assert crusoe_result.email == crusoe_existing_email
        # scenario 4: when requested to adds an email with domain belonging to a team, add user to team
        gustav = models.User(username='gustav')
        gustav_email = 'g@keepballin.ca'
        gustav_result = gustav.add_email(gustav_email)
        db.session.add(gustav)
        db.session.commit()
        assert gustav_result.email == gustav_email

    def test_make_email_primary(self):
        """
        Test to make an email primary for a user
        """
        mr_whymper = models.User(username='whymmper')
        whymper_email = 'whmmmm@animalfarm.co.uk'
        whymper_result = mr_whymper.add_email(whymper_email)
        mr_whymper.primary_email = whymper_result
        assert whymper_result.email == whymper_email
        assert whymper_result.primary is True
