"""Tests for PhoneNumber model."""
# pylint: disable=redefined-outer-name

from contextlib import nullcontext as does_not_raise
from types import SimpleNamespace
from typing import Generator

from sqlalchemy.exc import IntegrityError
import phonenumbers
import pytest
import sqlalchemy as sa

from funnel import models

# These numbers were obtained from libphonenumber with region codes 'IN' and 'US':
# >>> phonenumbers.example_number_for_type(region, phonenumbers.PhoneNumberType.MOBILE)
EXAMPLE_NUMBER_IN = '+918123456789'
EXAMPLE_NUMBER_US = '+12015550123'
EXAMPLE_NUMBER_CA = '+15062345678'
EXAMPLE_NUMBER_GB = '+447400123456'
EXAMPLE_NUMBER_DE = '+4915123456789'
EXAMPLE_NUMBER_IN_UNPREFIXED = '8123456789'
EXAMPLE_NUMBER_IN_FORMATTED = '+91 81234 56789'
EXAMPLE_NUMBER_US_FORMATTED = '+1 201-555-0123'

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
# 1. Remove class from mapper registry using ``Model.registry._dispose_cls(cls)``
# 2. Remove table from metadata using Model.metadata.remove(cls.__table__)
# 3. Remove all relationships to other classes (unsolved)
@pytest.fixture(scope='session')
def phone_models(database, app) -> Generator:
    class PhoneUser(models.BaseMixin, models.Model):
        """Test model representing a user account."""

        __tablename__ = 'test_phone_user'

    class PhoneLink(models.PhoneNumberMixin, models.BaseMixin, models.Model):
        """Test model connecting PhoneUser to PhoneNumber."""

        __tablename__ = 'test_phone_link'
        __phone_optional__ = False
        __phone_unique__ = True
        __phone_for__ = 'phoneuser'
        __phone_is_exclusive__ = True

        phoneuser_id = sa.orm.mapped_column(
            sa.Integer, sa.ForeignKey('test_phone_user.id'), nullable=False
        )
        phoneuser = models.relationship(PhoneUser)

    class PhoneDocument(models.PhoneNumberMixin, models.BaseMixin, models.Model):
        """Test model unaffiliated to a user that has a phone number attached."""

        __tablename__ = 'test_phone_document'

    class PhoneLinkedDocument(models.PhoneNumberMixin, models.BaseMixin, models.Model):
        """Test model that accepts an optional user and an optional phone."""

        __tablename__ = 'test_phone_linked_document'
        __phone_for__ = 'phoneuser'

        phoneuser_id = sa.orm.mapped_column(
            sa.Integer, sa.ForeignKey('test_phone_user.id'), nullable=True
        )
        phoneuser = models.relationship(PhoneUser)

    new_models = [PhoneUser, PhoneLink, PhoneDocument, PhoneLinkedDocument]

    sa.orm.configure_mappers()
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
    ('candidate', 'sms', 'parsed', 'expected'),
    [
        ('9845012345', True, False, '+919845012345'),
        ('98450-12345', True, False, '+919845012345'),
        ('+91 98450 12345', True, False, '+919845012345'),
        ('8022223333', False, False, '+918022223333'),
        ('+918022223333', True, False, False),
        ('junk', False, False, None),
        (
            '9845012345',
            True,
            True,
            phonenumbers.PhoneNumber(country_code=91, national_number=9845012345),
        ),
        (
            '98450-12345',
            True,
            True,
            phonenumbers.PhoneNumber(country_code=91, national_number=9845012345),
        ),
        (
            '+91 98450 12345',
            True,
            True,
            phonenumbers.PhoneNumber(country_code=91, national_number=9845012345),
        ),
        (
            '8022223333',
            False,
            True,
            phonenumbers.PhoneNumber(country_code=91, national_number=8022223333),
        ),
    ],
)
def test_parse_phone_number(candidate, sms, parsed, expected) -> None:
    """Test that parse_phone_number is able to parse a number."""
    assert models.parse_phone_number(candidate, sms, parsed) == expected


@pytest.mark.parametrize(
    ('candidate', 'expected', 'raises'),
    [
        (
            EXAMPLE_NUMBER_IN_UNPREFIXED,
            None,
            pytest.raises(models.PhoneNumberInvalidError),
        ),
        (EXAMPLE_NUMBER_IN, EXAMPLE_NUMBER_IN, does_not_raise()),
        (EXAMPLE_NUMBER_IN_FORMATTED, EXAMPLE_NUMBER_IN, does_not_raise()),
        (
            phonenumbers.PhoneNumber(country_code=91, national_number=123456789),
            None,
            pytest.raises(models.PhoneNumberInvalidError),
        ),
        (
            phonenumbers.PhoneNumber(country_code=91, national_number=9845012345),
            '+919845012345',
            does_not_raise(),
        ),
    ],
)
def test_validate_phone_number(candidate, expected, raises) -> None:
    with raises:
        assert models.validate_phone_number(candidate) == expected


@pytest.mark.parametrize(
    ('candidate', 'expected', 'raises'),
    [
        (
            EXAMPLE_NUMBER_IN_UNPREFIXED,
            None,
            pytest.raises(models.PhoneNumberInvalidError),
        ),
        (EXAMPLE_NUMBER_IN, EXAMPLE_NUMBER_IN, does_not_raise()),
        (EXAMPLE_NUMBER_IN_FORMATTED, EXAMPLE_NUMBER_IN, does_not_raise()),
        (
            phonenumbers.PhoneNumber(country_code=91, national_number=123456789),
            '+91123456789',  # This output differs from validate_phone_number
            does_not_raise(),
        ),
        (
            phonenumbers.PhoneNumber(country_code=91, national_number=9845012345),
            '+919845012345',
            does_not_raise(),
        ),
    ],
)
def test_canonical_phone_number(candidate, expected, raises) -> None:
    with raises:
        assert models.canonical_phone_number(candidate) == expected


def test_phone_hash_stability() -> None:
    """Safety test to ensure phone_blakeb160_hash doesn't change spec."""
    phash = models.phone_blake2b160_hash
    with pytest.raises(ValueError, match="Not a phone number"):
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


def test_phone_number_init() -> None:
    """`PhoneNumber` instances can be created using a string phone number."""
    # A fully specced number is accepted and gets the correct hash
    pn1 = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    assert pn1.number == EXAMPLE_NUMBER_IN
    assert pn1.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn1) == EXAMPLE_NUMBER_IN
    assert pn1.formatted == EXAMPLE_NUMBER_IN_FORMATTED
    # A visually formatted number also parses correctly and is re-formatted to E164
    pn2 = models.PhoneNumber(EXAMPLE_NUMBER_IN_FORMATTED)
    assert pn2.number == EXAMPLE_NUMBER_IN
    assert pn2.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn2) == EXAMPLE_NUMBER_IN
    assert pn2.formatted == EXAMPLE_NUMBER_IN_FORMATTED
    # Any worldwide prefix is accepted as long as it's a valid phone number
    pn3 = models.PhoneNumber(EXAMPLE_NUMBER_US_FORMATTED)
    assert pn3.number == EXAMPLE_NUMBER_US
    assert pn3.blake2b160 == hash_map[EXAMPLE_NUMBER_US]
    assert str(pn3) == EXAMPLE_NUMBER_US
    assert pn3.formatted == EXAMPLE_NUMBER_US_FORMATTED


def test_phone_number_init_error() -> None:
    """`PhoneNumber` instances cannot be created without a valid phone number."""
    with pytest.raises(ValueError, match="A string phone number is required"):
        # Must be a string
        models.PhoneNumber(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Not a phone number"):
        # Must not be blank
        models.PhoneNumber('')
    with pytest.raises(ValueError, match="Not a phone number"):
        # Must not be garbage input
        models.PhoneNumber('garbage')
    with pytest.raises(ValueError, match="Not a phone number"):
        # Must be fully specced; no unprefixed numbers (this will not be recognised)
        models.PhoneNumber(EXAMPLE_NUMBER_IN_UNPREFIXED)
    with pytest.raises(ValueError, match="Not a valid phone number"):
        # Must be a valid number even if syntax is correct
        models.PhoneNumber('+910123456789')


@pytest.mark.usefixtures('db_session')
def test_phone_number_mutability() -> None:
    """`PhoneNumber` can be mutated to delete or restore the number only."""
    pn = models.PhoneNumber(EXAMPLE_NUMBER_IN_FORMATTED)
    assert pn.number == EXAMPLE_NUMBER_IN
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn) == EXAMPLE_NUMBER_IN
    assert pn.formatted == EXAMPLE_NUMBER_IN_FORMATTED

    # Setting it to the same value again is allowed
    pn.number = EXAMPLE_NUMBER_IN
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn) == EXAMPLE_NUMBER_IN
    assert pn.formatted == EXAMPLE_NUMBER_IN_FORMATTED

    # Nulling is allowed, and hash remains intact
    pn.number = None
    assert pn.number is None
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn) == ''
    assert pn.formatted == '[removed]'

    # Restoring is allowed (with any formatting)
    pn.number = EXAMPLE_NUMBER_IN_FORMATTED
    assert pn.number == EXAMPLE_NUMBER_IN
    assert pn.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn) == EXAMPLE_NUMBER_IN
    assert pn.formatted == EXAMPLE_NUMBER_IN_FORMATTED

    # Reformatting when not restoring is not allowed
    with pytest.raises(ValueError, match="Phone number cannot be changed"):
        pn.number = EXAMPLE_NUMBER_IN_FORMATTED

    # Changing it to another value is not allowed
    with pytest.raises(ValueError, match="Phone number cannot be changed"):
        pn.number = EXAMPLE_NUMBER_US
    with pytest.raises(ValueError, match="A phone number is required"):
        pn.number = ''
    with pytest.raises(ValueError, match="A phone number is required"):
        pn.number = False  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Phone number cannot be changed"):
        pn.number = [1, 2, 3]  # type: ignore[assignment]

    # Changing after nulling is not allowed as hash won't match
    pn.number = None
    with pytest.raises(ValueError, match="Phone number does not match"):
        pn.number = EXAMPLE_NUMBER_US
    with pytest.raises(ValueError, match="A phone number is required"):
        pn.number = ''
    with pytest.raises(ValueError, match="A phone number is required"):
        pn.number = False  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Invalid value for phone number"):
        pn.number = [1, 2, 3]  # type: ignore[assignment]


def test_phone_number_md5() -> None:
    """`PhoneNumber` has an MD5 method for legacy applications."""
    pn = models.PhoneNumber(EXAMPLE_NUMBER_IN)
    assert pn.md5() == '889ccfeb3234c4b90516a3dd4406a0e6'
    pn.number = None
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

    # Get works on blocked numbers
    pn1.mark_blocked()
    assert pn1.is_blocked is True
    assert models.PhoneNumber.get(EXAMPLE_NUMBER_IN) == pn1

    # Get can be passed an explicit `is_blocked` parameter
    assert models.PhoneNumber.get(EXAMPLE_NUMBER_IN, is_blocked=False) is None
    assert models.PhoneNumber.get(EXAMPLE_NUMBER_IN, is_blocked=True) == pn1
    assert models.PhoneNumber.get(EXAMPLE_NUMBER_US, is_blocked=False) == pn2
    assert models.PhoneNumber.get(EXAMPLE_NUMBER_US, is_blocked=True) is None


@pytest.mark.usefixtures('db_session')
def test_phone_number_invalid_hash_raises_error() -> None:
    """Retrieving a phone number with an invalid hash will raise ValueError."""
    with pytest.raises(ValueError, match='Invalid character'):
        models.PhoneNumber.get(phone_hash='invalid')


@pytest.mark.usefixtures('db_session')
def test_phone_number_add() -> None:
    """Using PhoneNumber.add will auto-add to session and return existing instances."""
    pn1 = models.PhoneNumber.add(EXAMPLE_NUMBER_IN)
    assert isinstance(pn1, models.PhoneNumber)
    assert pn1.number == EXAMPLE_NUMBER_IN

    pn2 = models.PhoneNumber.add(EXAMPLE_NUMBER_US)
    pn3 = models.PhoneNumber.add(EXAMPLE_NUMBER_IN_FORMATTED)
    pn4 = models.PhoneNumber.add(EXAMPLE_NUMBER_US_FORMATTED)

    assert pn2 is not None
    assert pn3 is not None
    assert pn4 is not None

    assert pn2 != pn1
    assert pn3 == pn1
    assert pn4 == pn2

    assert pn1.number == EXAMPLE_NUMBER_IN
    assert pn2.number == EXAMPLE_NUMBER_US

    # A forgotten phone number will be restored by calling PhoneNumber.add
    pn2.mark_forgotten()
    assert pn2.number is None
    pn5 = models.PhoneNumber.add(EXAMPLE_NUMBER_US_FORMATTED)
    assert pn5 == pn2
    assert pn5.number == pn2.number == EXAMPLE_NUMBER_US

    # Adding an invalid phone number will raise an error
    with pytest.raises(models.PhoneNumberInvalidError):
        models.PhoneNumber.add('invalid')

    with pytest.raises(models.PhoneNumberInvalidError):
        models.PhoneNumber.add(None)  # type: ignore[arg-type]


@pytest.mark.usefixtures('db_session')
@pytest.mark.parametrize('sms', [True, False])
@pytest.mark.parametrize('wa', [True, False])
def test_phone_number_active(sms, wa) -> None:
    """A phone number can be marked as currently active, optionally with an app."""
    pn = models.PhoneNumber.add(EXAMPLE_NUMBER_IN)
    assert pn.active_at is None
    pn.mark_active(sms=sms, wa=wa)
    assert str(pn.active_at) == str(sa.func.utcnow())
    if sms:
        assert pn.has_sms is True
        assert str(pn.has_sms_at) == str(sa.func.utcnow())
    else:
        assert pn.has_sms is None
        assert pn.has_sms_at is None
    if wa:
        assert pn.has_wa is True
        assert str(pn.has_wa_at) == str(sa.func.utcnow())
    else:
        assert pn.has_wa is None
        assert pn.has_wa_at is None


@pytest.mark.usefixtures('db_session')
def test_phone_number_blocked() -> None:
    """A blocked phone number cannot be used via PhoneNumber.add."""
    pn1 = models.PhoneNumber.add(EXAMPLE_NUMBER_IN)
    pn2 = models.PhoneNumber.add(EXAMPLE_NUMBER_US)

    pn1.mark_has_sms(True)
    pn1.mark_has_wa(False)

    assert pn1.is_blocked is False
    assert pn1.number is not None
    assert pn1.number == EXAMPLE_NUMBER_IN
    assert pn1.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn1) == EXAMPLE_NUMBER_IN
    assert pn1.formatted == EXAMPLE_NUMBER_IN_FORMATTED
    assert pn1.has_sms is True
    assert str(pn1.has_sms_at) == str(sa.func.utcnow())
    assert pn1.has_wa is False
    assert str(pn1.has_wa_at) == str(sa.func.utcnow())

    assert models.PhoneNumber.query.filter(models.PhoneNumber.is_blocked).all() == []

    pn1.mark_blocked()

    assert pn1.is_blocked is True
    assert pn1.number is None  # type: ignore[unreachable]
    assert pn1.blake2b160 is not None
    assert pn1.is_blocked is True
    assert pn2.is_blocked is False
    assert str(pn1) == ''
    assert pn1.formatted == '[blocked]'
    assert pn1.has_sms is None
    assert pn1.has_sms_at is None
    assert pn1.has_wa is None
    assert pn1.has_wa_at is None

    assert models.PhoneNumber.query.filter(models.PhoneNumber.is_blocked).all() == [pn1]

    # A blocked number cannot be added again
    with pytest.raises(models.PhoneNumberBlockedError):
        models.PhoneNumber.add(EXAMPLE_NUMBER_IN)

    # Unblocking requires the correct phone number
    with pytest.raises(ValueError, match="Phone number does not match"):
        pn1.mark_unblocked(EXAMPLE_NUMBER_US)
    pn1.mark_unblocked(EXAMPLE_NUMBER_IN_FORMATTED)
    assert pn1.is_blocked is False
    assert pn1.number == EXAMPLE_NUMBER_IN
    assert pn1.blake2b160 == hash_map[EXAMPLE_NUMBER_IN]
    assert str(pn1) == EXAMPLE_NUMBER_IN
    assert pn1.formatted == EXAMPLE_NUMBER_IN_FORMATTED


def test_phone_number_mixin(  # pylint: disable=too-many-locals,too-many-statements
    phone_models, db_session
) -> None:
    """The PhoneNumberMixin class adds safety checks for using a phone number."""
    blocked_phone = models.PhoneNumber(EXAMPLE_NUMBER_CA)
    blocked_phone.mark_blocked()

    user1 = phone_models.PhoneUser()
    user2 = phone_models.PhoneUser()

    doc1 = phone_models.PhoneDocument()
    doc2 = phone_models.PhoneDocument()

    db_session.add_all([user1, user2, doc1, doc2, blocked_phone])

    # Mixin-based classes can simply specify a 'phone' parameter to link to n
    # PhoneNumber instance
    link1 = phone_models.PhoneLink(phoneuser=user1, phone=EXAMPLE_NUMBER_IN)
    db_session.add(link1)
    pn1 = models.PhoneNumber.get(EXAMPLE_NUMBER_IN)
    assert link1.phone == EXAMPLE_NUMBER_IN
    assert link1.phone_number == pn1
    assert link1.transport_hash == pn1.transport_hash
    assert bool(link1.transport_hash)

    # Link an unrelated phone number to another user to demonstrate that it works
    link2 = phone_models.PhoneLink(phoneuser=user2, phone=EXAMPLE_NUMBER_US)
    db_session.add(link2)
    pn2 = models.PhoneNumber.get(EXAMPLE_NUMBER_US)
    assert link2.phone == EXAMPLE_NUMBER_US
    assert link2.phone_number == pn2
    assert link2.transport_hash == pn2.transport_hash
    assert bool(link1.transport_hash)

    db_session.commit()

    # EXAMPLE_NUMBER_US is now exclusive to user2. Attempting it to assign it to
    # user1 will raise an exception, even if the case is changed.
    with pytest.raises(models.PhoneNumberInUseError):
        phone_models.PhoneLink(phoneuser=user1, phone=EXAMPLE_NUMBER_US)

    # This safety catch works even if the phone_number column is used:
    with pytest.raises(models.PhoneNumberInUseError):
        phone_models.PhoneLink(phoneuser=user1, phone_number=pn2)

    db_session.rollback()

    # Blocked numbers cannot be used either
    with pytest.raises(models.PhoneNumberBlockedError):
        phone_models.PhoneLink(phoneuser=user1, phone=EXAMPLE_NUMBER_CA)

    with pytest.raises(models.PhoneNumberBlockedError):
        phone_models.PhoneLink(phoneuser=user1, phone_number=blocked_phone)

    db_session.rollback()

    # Attempting to assign EXAMPLE_NUMBER_US to user2 a second time will cause a
    # SQL integrity error because PhoneLink.__phone_unique__ is True.
    link3 = phone_models.PhoneLink(phoneuser=user2, phone=EXAMPLE_NUMBER_US)
    db_session.add(link3)
    with pytest.raises(IntegrityError):
        db_session.commit()

    del link3  # skipcq: PTC-W0043
    db_session.rollback()

    # The PhoneDocument model, in contrast, has no requirement of availability to a
    # specific user, so it won't be blocked here despite being exclusive to user1
    assert doc1.phone is None
    assert doc2.phone is None
    assert doc1.phone_number is None
    assert doc2.phone_number is None

    doc1.phone = EXAMPLE_NUMBER_IN
    doc2.phone = EXAMPLE_NUMBER_IN

    assert doc1.phone == EXAMPLE_NUMBER_IN
    assert doc2.phone == EXAMPLE_NUMBER_IN
    assert doc1.phone_number == pn1
    assert doc2.phone_number == pn1

    # pn1 now has three references, while pn2 has 1
    assert pn1.refcount() == 3
    assert pn2.refcount() == 1

    # Setting the phone property on PhoneDocument will mutate
    # PhoneDocument.phone_number and not PhoneDocument.phone_number.number
    assert pn1.number == EXAMPLE_NUMBER_IN
    doc1.phone = None
    assert pn1.number == EXAMPLE_NUMBER_IN
    assert doc1.phone_number is None
    doc2.phone = EXAMPLE_NUMBER_US
    assert pn1.number == EXAMPLE_NUMBER_IN
    assert doc2.phone_number == pn2

    # PhoneLinkedDocument takes the complexity up a notch

    # A document linked to a user can use any phone linked to that user
    ldoc1 = phone_models.PhoneLinkedDocument(phoneuser=user1, phone=EXAMPLE_NUMBER_IN)
    db_session.add(ldoc1)
    assert ldoc1.phoneuser == user1
    assert ldoc1.phone_number == pn1

    # But another user can't use this phone number
    with pytest.raises(models.PhoneNumberInUseError):
        phone_models.PhoneLinkedDocument(phoneuser=user2, phone=EXAMPLE_NUMBER_IN)

    # This restriction also applies when user is not specified. Here, this phone is
    # claimed by user2 above
    with pytest.raises(models.PhoneNumberInUseError):
        phone_models.PhoneLinkedDocument(phoneuser=None, phone=EXAMPLE_NUMBER_US)

    # But it works with an unaffiliated phone number
    ldoc2 = phone_models.PhoneLinkedDocument(phone=EXAMPLE_NUMBER_GB)
    db_session.add(ldoc2)
    assert ldoc2.phoneuser is None
    assert ldoc2.phone == EXAMPLE_NUMBER_GB

    ldoc3 = phone_models.PhoneLinkedDocument(phoneuser=user2, phone=EXAMPLE_NUMBER_DE)
    db_session.add(ldoc3)
    assert ldoc3.phoneuser is user2
    assert ldoc3.phone == EXAMPLE_NUMBER_DE

    # Setting the phone to None on the document removes the link to the PhoneNumber,
    # but does not blank out the PhoneNumber

    assert ldoc1.phone_number == pn1
    assert pn1.number == EXAMPLE_NUMBER_IN
    ldoc1.phone = None
    assert ldoc1.phone_number is None
    assert pn1.number == EXAMPLE_NUMBER_IN


def test_phone_number_refcount_drop(phone_models, db_session, refcount_data) -> None:
    """Test that PhoneNumber.refcount drop events are fired."""
    # The refcount changing signal handler will have received events for every phone
    # number in this test. A request teardown processor can use this to determine
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


def test_phone_number_validate_for(phone_models, db_session) -> None:
    """PhoneNumber.validate_for can be used to determine availability."""
    user1 = phone_models.PhoneUser()
    user2 = phone_models.PhoneUser()
    anon_user = None
    db_session.add_all([user1, user2])

    # A new phone number is available to all
    assert models.PhoneNumber.validate_for(user1, EXAMPLE_NUMBER_IN) is True
    assert models.PhoneNumber.validate_for(user2, EXAMPLE_NUMBER_IN) is True
    assert models.PhoneNumber.validate_for(anon_user, EXAMPLE_NUMBER_IN) is True

    # Once it's assigned to a user, availability changes
    link = phone_models.PhoneLink(phoneuser=user1, phone=EXAMPLE_NUMBER_IN)
    db_session.add(link)

    assert models.PhoneNumber.validate_for(user1, EXAMPLE_NUMBER_IN) is True
    assert models.PhoneNumber.validate_for(user2, EXAMPLE_NUMBER_IN) is False
    assert models.PhoneNumber.validate_for(anon_user, EXAMPLE_NUMBER_IN) is False

    # A number in use is not available to claim as new
    assert (
        models.PhoneNumber.validate_for(user1, EXAMPLE_NUMBER_IN, new=True) == 'not_new'
    )
    assert models.PhoneNumber.validate_for(user2, EXAMPLE_NUMBER_IN, new=True) is False
    assert (
        models.PhoneNumber.validate_for(anon_user, EXAMPLE_NUMBER_IN, new=True) is False
    )

    # A blocked number is available to no one
    blocked_phone = models.PhoneNumber(EXAMPLE_NUMBER_CA)
    blocked_phone.mark_blocked()
    db_session.add(blocked_phone)
    assert models.PhoneNumber.validate_for(user1, EXAMPLE_NUMBER_CA) == 'blocked'
    assert models.PhoneNumber.validate_for(user2, EXAMPLE_NUMBER_CA) == 'blocked'
    assert models.PhoneNumber.validate_for(anon_user, EXAMPLE_NUMBER_CA) == 'blocked'

    # An invalid number is available to no one
    assert models.PhoneNumber.validate_for(user1, 'invalid') == 'invalid'
    assert models.PhoneNumber.validate_for(user2, 'invalid') == 'invalid'
    assert models.PhoneNumber.validate_for(anon_user, 'invalid') == 'invalid'


def test_phone_number_existing_but_unused_validate_for(
    phone_models, db_session
) -> None:
    """An unused but existing phone number should be available to claim."""
    user = phone_models.PhoneUser()
    phone_number = models.PhoneNumber.add(EXAMPLE_NUMBER_GB)
    db_session.add_all([user, phone_number])
    db_session.commit()

    assert models.PhoneNumber.validate_for(user, EXAMPLE_NUMBER_GB, new=True) is True
    assert models.PhoneNumber.validate_for(user, EXAMPLE_NUMBER_GB) is True
