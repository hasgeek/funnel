"""Tests for PhoneNumber model."""

from types import SimpleNamespace
from typing import Generator

from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa

import pytest

from funnel import models

# These numbers were obtained from libphonenumber with region codes 'IN' and 'US':
# >>> phonenumbers.example_number_for_type(region, phonenumbers.PhoneNumberType.MOBILE)
EXAMPLE_NUMBER_IN = '+918123456789'
EXAMPLE_NUMBER_US = '+12015550123'
EXAMPLE_NUMBER_IN_UNPREFIXED = '8123456789'
EXAMPLE_NUMBER_IN_FORMATTED = '+91 81234 56789'
EXAMPLE_NUMBER_US_FORMATTED = '+1 (201) 555-0123'

# This hash map should not be edited -- hashes are permanent
hash_map = {
    'not-a-valid-number': (
        b'\xd6\xac\xd6\x83\x8d\xbcu\xbf\x96ls\x9c\xe2\xda\xa2~?\xcd\x1c\x18'
    ),
    EXAMPLE_NUMBER_IN: (
        b'\x14\xc5\xed\xfe\xdb\xe3\xe6$\x0b\xd39\xab\x8d\x171\xe9\x83[\x1a\xce'
    ),
    EXAMPLE_NUMBER_US: (
        b'\xa0\x10\xe0w\xec\xa8\xecO\x04\r\xde\xb9\x7f>g\n\xf8\xae\xd0\xb0'
    ),
}


# This fixture must be session scope as it cannot be called twice in the same process.
# SQLAlchemy models must only be defined once. A model can theoretically be removed,
# but there is no formal API. Removal has at least three parts:
# 1. Remove class from mapper registry using ``db.Model.registry._dispose_cls(cls)``
# 2. Remove table from metadata using db.metadata.remove(cls.__table__)
# 3. Remove all relationships to other classes (unsolved)
@pytest.fixture(scope='session')
def phone_models(database, app) -> Generator:
    db = database

    class PhoneUser(models.BaseMixin, db.Model):  # type: ignore[name-defined]
        """Test model representing a user account."""

        __tablename__ = 'phoneuser'

    class PhoneLink(
        models.PhoneNumberMixin,
        models.BaseMixin,
        db.Model,  # type: ignore[name-defined]
    ):
        """Test model connecting PhoneUser to PhoneNumber."""

        __phone_optional__ = False
        __phone_unique__ = True
        __phone_for__ = 'phoneuser'
        __phone_is_exclusive__ = True

        phoneuser_id = sa.Column(
            sa.Integer, sa.ForeignKey('phoneuser.id'), nullable=False
        )
        phoneuser = sa.orm.relationship(PhoneUser)

    class PhoneDocument(
        models.PhoneNumberMixin,
        models.BaseMixin,
        db.Model,  # type: ignore[name-defined]
    ):
        """Test model unaffiliated to a user that has a phone number attached."""

    class PhoneLinkedDocument(
        models.PhoneNumberMixin,
        models.BaseMixin,
        db.Model,  # type: ignore[name-defined]
    ):
        """Test model that accepts an optional user and an optional phone."""

        __phone_for__ = 'phoneuser'

        phoneuser_id = sa.Column(
            sa.Integer, sa.ForeignKey('phoneuser.id'), nullable=True
        )
        phoneuser = sa.orm.relationship(PhoneUser)

    new_models = [PhoneUser, PhoneLink, PhoneDocument, PhoneLinkedDocument]

    # These models do not use __bind_key__ so no bind is provided to create_all/drop_all
    with app.app_context():
        database.metadata.create_all(
            bind=database.engine,
            tables=[
                model.__table__ for model in new_models  # type: ignore[attr-defined]
            ],
        )
    yield SimpleNamespace(**{model.__name__: model for model in new_models})
    with app.app_context():
        database.metadata.drop_all(
            bind=database.engine,
            tables=[
                model.__table__ for model in new_models  # type: ignore[attr-defined]
            ],
        )


@pytest.fixture()
def refcount_data(funnel) -> Generator:
    refcount_signal_fired = set()

    def refcount_signal_receiver(sender):
        refcount_signal_fired.add(sender)

    funnel.signals.phonenumber_refcount_dropping.connect(refcount_signal_receiver)
    yield refcount_signal_fired
    funnel.signals.phonenumber_refcount_dropping.disconnect(refcount_signal_receiver)


@pytest.mark.parametrize(
    ('candidate', 'sms', 'expected'),
    [
        ('9845012345', True, '+919845012345'),
        ('98450-12345', True, '+919845012345'),
        ('+91 98450 12345', True, '+919845012345'),
        ('8022223333', False, '+918022223333'),
        ('junk', False, None),
    ],
)
def test_parse_phone_number(candidate, expected, sms) -> None:
    """Test that parse_phone_number is able to parse a number."""
    assert models.parse_phone_number(candidate, sms) == expected


def test_phone_hash_stability() -> None:
    """Safety test to ensure phone_blakeb160_hash doesn't change spec."""
    phash = models.phone_number.phone_blake2b160_hash
    with pytest.raises(ValueError, match="Not a valid phone number"):
        phash('not-a-valid-number')
    # However, insisting the number is pre-validated will generate a hash. This is only
    # useful when the number is actually pre-validated
    assert (
        phash('not-a-valid-number', _pre_validated_formatted=True)
        == hash_map['not-a-valid-number']
    )
    # Number formatting will be normalized before hashing
    assert (
        phash(EXAMPLE_NUMBER_IN)
        == phash(EXAMPLE_NUMBER_IN_FORMATTED)
        == hash_map[EXAMPLE_NUMBER_IN]
    )
    assert (
        phash(EXAMPLE_NUMBER_US)
        == phash(EXAMPLE_NUMBER_US_FORMATTED)
        == hash_map[EXAMPLE_NUMBER_US]
    )


def test_phone_number_refcount_drop(phone_models, db_session, refcount_data) -> None:
    """Test that PhoneNumber.refcount drop events are fired."""
    # The refcount changing signal handler will have received events for every phone
    # address in this test. A request teardown processor can use this to determine
    # which phone numberes need to be forgotten (preferably in a background job)

    # We have an empty set at the start of this test
    assert isinstance(refcount_data, set)
    assert refcount_data == set()

    pn = models.PhoneNumber.add(EXAMPLE_NUMBER_IN)
    assert refcount_data == set()

    user = phone_models.PhoneUser()
    doc = phone_models.PhoneDocument()
    link = phone_models.PhoneLink(phoneuser=user, phone_number=pn)
    db_session.add_all([pn, user, doc, link])

    assert refcount_data == set()

    doc.phone_number = pn
    assert refcount_data == set()
    assert pn.refcount() == 2

    doc.phone_number = None
    assert refcount_data == {pn}
    assert pn.refcount() == 1

    refcount_data.remove(pn)
    assert refcount_data == set()
    db_session.commit()  # Persist before deleting
    db_session.delete(link)
    db_session.commit()
    assert refcount_data == {pn}
    assert pn.refcount() == 0


def test_phone_number_init() -> None:
    """`PhoneNumber` instances can be created using a string phone number."""
    # A fully specced number is accepted and gets the correct hash
    pn1 = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    assert pn1.phone == EXAMPLE_NUMBER_IN
    assert pn1.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    # A visually formatted number also parses correctly and is re-formatted to E164
    pn2 = models.PhoneNumber(EXAMPLE_NUMBER_IN_FORMATTED)
    assert pn2.phone == EXAMPLE_NUMBER_IN
    assert pn1.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    # Any worldwide prefix is accepted as long as it's a valid phone number
    pn3 = models.PhoneNumber(EXAMPLE_NUMBER_US_FORMATTED)
    assert pn3.phone == EXAMPLE_NUMBER_US
    assert pn3.blake2b160 == hash_map[EXAMPLE_NUMBER_US]


def test_phone_number_init_error() -> None:
    """`PhoneNumber` instances cannot be created without a valid phone number."""
    with pytest.raises(ValueError, match="A string phone number is required"):
        # Must be a string
        models.PhoneNumber(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Not a valid phone number"):
        # Must not be blank
        models.PhoneNumber('')
    with pytest.raises(ValueError, match="Not a valid phone number"):
        # Must not be garbage input
        models.PhoneNumber('garbage')
    with pytest.raises(ValueError, match="Not a valid phone number"):
        # Must be fully specced; no unprefixed numbers
        models.PhoneNumber(EXAMPLE_NUMBER_IN_UNPREFIXED)


def test_phone_number_mutability() -> None:
    """`PhoneNumber` can be mutated to delete or restore the number only."""
    pn = models.PhoneNumber(EXAMPLE_NUMBER_IN_FORMATTED)
    assert pn.phone == EXAMPLE_NUMBER_IN
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]

    # Setting it to the same value again is allowed
    pn.phone = EXAMPLE_NUMBER_IN
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]

    # Nulling is allowed, and hash remains intact
    pn.phone = None
    assert pn.phone is None
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]

    # Restoring is allowed (with any formatting)
    pn.phone = EXAMPLE_NUMBER_IN_FORMATTED
    assert pn.phone == EXAMPLE_NUMBER_IN
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]

    # However, reformatting when not restoring is not allowed
    with pytest.raises(ValueError, match="Phone number cannot be changed"):
        pn.phone = EXAMPLE_NUMBER_IN_FORMATTED

    # But changing it to another value is not allowed
    with pytest.raises(ValueError, match="Phone number cannot be changed"):
        pn.phone = EXAMPLE_NUMBER_US

    # Changing after nulling is not allowed as hash won't match
    pn.phone = None
    with pytest.raises(ValueError, match="Phone number does not match"):
        pn.phone = EXAMPLE_NUMBER_US


def test_phone_number_md5() -> None:
    """`PhoneNumber` has an MD5 method for legacy applications."""
    pn = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    assert pn.md5() == '889ccfeb3234c4b90516a3dd4406a0e6'
    pn.phone = None
    assert pn.md5() is None


@pytest.mark.usefixtures('db_session')
def test_phone_number_is_blocked_flag() -> None:
    """`PhoneNumber` has a read-only is_blocked flag that is normally False."""
    pn = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    assert pn.is_blocked is False
    with pytest.raises(AttributeError):
        pn.is_blocked = True  # type: ignore[misc]


def test_phone_number_can_commit(db_session) -> None:
    """A `PhoneNumber` can be committed to db."""
    pn = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    db_session.add(pn)
    db_session.commit()


def test_phone_number_conflict_integrity_error(db_session) -> None:
    """A conflicting `PhoneNumber` cannot be committed to db."""
    pn1 = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    db_session.add(pn1)
    db_session.commit()
    # Conflicts with pn1 as phone numbers use normalized formatting in storage
    pn2 = models.PhoneNumber(EXAMPLE_NUMBER_IN_FORMATTED)
    db_session.add(pn2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    pn3 = models.PhoneNumber(EXAMPLE_NUMBER_US)
    db_session.add(pn3)
    db_session.commit()

    # Conflicts with pn3 over normalization
    pn4 = models.PhoneNumber(EXAMPLE_NUMBER_US_FORMATTED)
    db_session.add(pn4)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_phone_number_get(db_session) -> None:
    """Phone numbers can be loaded using PhoneNumber.get."""
    pn1 = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    pn2 = models.PhoneNumber(EXAMPLE_NUMBER_US)
    db_session.add_all([pn1, pn2])
    db_session.commit()

    get1 = models.PhoneNumber.get(EXAMPLE_NUMBER_IN)
    assert get1 == pn1
    get1a = models.PhoneNumber.get(EXAMPLE_NUMBER_IN_FORMATTED)
    assert get1a == pn1
    get2 = models.PhoneNumber.get(EXAMPLE_NUMBER_US)
    assert get2 == pn2
    get2a = models.PhoneNumber.get(EXAMPLE_NUMBER_US_FORMATTED)
    assert get2a == pn2
    # Can also get by hash
    get3 = models.PhoneNumber.get(blake2b160=hash_map[EXAMPLE_NUMBER_IN])
    assert get3 == pn1
    # Or by Base58 representation of hash
    get4 = models.PhoneNumber.get(phone_hash='HnZQM2nFuPbxoBgyPoBmP1k6wrd')
    assert get4 == pn1

    # Will return nothing if given garbage input, or a non-existent phone number
    assert models.PhoneNumber.get('invalid') is None
    assert models.PhoneNumber.get('+91984512345') is None

    # Get works on blocked addresses
    pn1.mark_blocked()
    assert pn1.is_blocked is True
    assert models.PhoneNumber.get(EXAMPLE_NUMBER_IN) == pn1
