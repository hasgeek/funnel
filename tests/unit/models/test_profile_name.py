from sqlalchemy.exc import IntegrityError

import pytest

from funnel import db
import funnel.models as models

from .test_db import TestDatabaseFixture


class TestName(TestDatabaseFixture):
    def test_is_available_name(self):
        """Names are only available if valid and unused."""
        assert models.Profile.is_available_name('invalid_name') is False
        # 'piglet' is a name taken in the fixtures
        piglet = models.User.get(username='piglet')
        assert piglet.profile.state.AUTO
        # even though profile is not public, username is still unavailable
        assert models.Profile.is_available_name('piglet') is False
        # any other random usernames are available
        assert models.Profile.is_available_name('peppa') is True

    def test_validate_name_candidate(self):
        """The name validator returns error codes as expected."""
        assert models.Profile.validate_name_candidate(None) == 'blank'
        assert models.Profile.validate_name_candidate('') == 'blank'
        assert models.Profile.validate_name_candidate('invalid_name') == 'invalid'
        assert models.Profile.validate_name_candidate('0123456789' * 7) == 'long'
        assert models.Profile.validate_name_candidate('0123456789' * 6) is None
        assert models.Profile.validate_name_candidate('ValidName') is None
        assert models.Profile.validate_name_candidate('test-reserved') is None
        db.session.add(models.Profile(name='test-reserved', reserved=True))
        db.session.commit()
        assert models.Profile.validate_name_candidate('test-reserved') == 'reserved'
        assert models.Profile.validate_name_candidate('Test-Reserved') == 'reserved'
        assert models.Profile.validate_name_candidate('TestReserved') is None
        assert models.Profile.validate_name_candidate('piglet') == 'user'
        assert models.Profile.validate_name_candidate('batdog') == 'org'

    def test_reserved_name(self):
        """Names can be reserved, with no user or organization."""
        reserved_name = models.Profile(name='reserved-name', reserved=True)
        db.session.add(reserved_name)
        db.session.commit()
        # Profile.get() no longer works for non-public profiles
        retrieved_name = models.Profile.query.filter(
            db.func.lower(models.Profile.name) == db.func.lower('reserved-name')
        ).first()
        assert retrieved_name is reserved_name
        assert reserved_name.user is None
        assert reserved_name.user_id is None
        assert reserved_name.organization is None
        assert reserved_name.organization_id is None

        reserved_name.name = 'Reserved-Name'
        db.session.commit()
        retrieved_name = models.Profile.query.filter(
            db.func.lower(models.Profile.name) == db.func.lower('Reserved-Name')
        ).first()
        assert retrieved_name is reserved_name

    def test_unassigned_name(self):
        """Names must be assigned to a user or organization if not reserved."""
        unassigned_name = models.Profile(name='unassigned')
        db.session.add(unassigned_name)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_double_assigned_name(self):
        """Names cannot be assigned to a user and an organization simultaneously."""
        user = models.User(username="double-assigned", fullname="User")
        org = models.Organization(
            name="double-assigned", title="Organization", owner=self.fixtures.piglet
        )
        db.session.add_all([user, org])
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_user_two_names(self):
        """A user cannot have two names."""
        piglet = self.fixtures.piglet
        db.session.add(piglet)
        assert piglet.profile.name == 'piglet'
        peppa = models.Profile(name='peppa', user=piglet)
        db.session.add(peppa)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_org_two_names(self):
        """An organization cannot have two names."""
        batdog = self.fixtures.batdog
        db.session.add(batdog)
        assert batdog.profile.name == 'batdog'
        bathound = models.Profile(name='bathound', organization=batdog)
        db.session.add(bathound)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_remove_name(self):
        """Removing a name from a user or org also removes it from the Name table."""
        # assert self.fixtures.oakley.username == 'oakley'
        # assert models.Profile.get('oakley') is not None
        # self.fixtures.oakley.username = None
        # db.session.commit()
        # assert models.Profile.get('oakley') is None

        # assert self.fixtures.specialdachs.name == 'specialdachs'
        # assert models.Profile.get('specialdachs') is not None
        # self.fixtures.specialdachs.name = None
        # db.session.commit()
        # assert models.Profile.get('specialdachs') is None

        # FIXME: Need clarity on how this works

    def test_name_transfer(self):
        """Merging user accounts will transfer the name."""
        assert self.fixtures.nameless.username is None
        assert models.User.get(username='newname') is None
        newname = models.User(name='newname', fullname="New Name")
        db.session.add(newname)
        db.session.commit()
        assert models.User.get(username='newname') is not None
        assert newname.username == 'newname'

        with self.app.test_request_context('/'):
            merged = models.merge_users(self.fixtures.nameless, newname)

            assert merged is not newname
            assert merged is self.fixtures.nameless
            assert newname.status == models.USER_STATUS.MERGED
            assert merged.username == 'newname'
