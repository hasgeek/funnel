from sqlalchemy.exc import IntegrityError

import pytest

from funnel.models.email_address import (
    EmailAddress,
    EmailAddressBlockedError,
    canonical_email_representation,
    email_blake2b160_hash,
)

# Fixture used across tests.
hash_map = {
    'example@example.com': b'X5Q\xc1<\xceE<\x05\x9c\xa7\x0f\xee{\xcd\xc2\xe5\xbd\x82\xa1',
    'example+extra@example.com': b'\xcfi\xf2\xdfph\xc0\x81\xfb\xe8\\\xa6\xa5\xf1\xfb:\xbb\xe4\x88\xde',
    'example@gmail.com': b"\tC*\xd2\x9a\xcb\xdfR\xcb\xbf=>2D'(\xa8V\x13\xa7",
    'example@googlemail.com': b'x\xd6#Ue\xa8-_\xeclJ+o8\xfe\x1f\xa1\x0b:9',
}


def test_email_hash_stability():
    """Safety test to ensure email_blakeb160_hash doesn't change spec"""
    ehash = email_blake2b160_hash
    assert ehash('example@example.com') == hash_map['example@example.com']
    assert ehash('EXAMPLE@EXAMPLE.COM') != hash_map['example@example.com']
    assert ehash('example@gmail.com') == hash_map['example@gmail.com']
    assert ehash('example@googlemail.com') == hash_map['example@googlemail.com']


def test_canonical_email_representation():
    """Test canonical email representation"""
    cemail = canonical_email_representation
    assert cemail('example@example.com') == ['example@example.com']
    assert cemail('EXAMPLE@EXAMPLE.COM') == ['example@example.com']
    assert cemail('example@googlemail.com') == [
        'example@gmail.com',
        'example@googlemail.com',
    ]
    assert cemail('example+extra@example.com') == ['example@example.com']
    assert cemail('exam.pl.e@gmail.com') == [
        'example@gmail.com',
        'exam.pl.e@gmail.com',
    ]
    assert cemail('exam.pl.e+extra@gmail.com') == [
        'example@gmail.com',
        'exam.pl.e@gmail.com',
    ]
    assert cemail('exam.pl.e@googlemail.com') == [
        'example@gmail.com',
        'exam.pl.e@googlemail.com',
    ]
    assert cemail('exam.pl.e+extra@googlemail.com') == [
        'example@gmail.com',
        'exam.pl.e@googlemail.com',
    ]


def test_email_address_init():
    """EmailAddress instances can be created using a string email address"""

    # Ordinary use constructor passes without incident
    ea1 = EmailAddress('example@example.com')
    assert ea1.email == 'example@example.com'
    assert ea1.email_lower == 'example@example.com'
    assert ea1.blake2b160 == hash_map['example@example.com']
    assert ea1.email_canonical == 'example@example.com'
    assert ea1.blake2b160_canonical == hash_map['example@example.com']
    assert str(ea1) == 'example@example.com'
    assert repr(ea1) == "EmailAddress('example@example.com')"
    # Public hash (for URLs)
    assert ea1.email_hash == '2EGz72jxcsYjvXxF7r5rqfAgikor'

    # Case is preserved but disregarded for hashes
    ea2 = EmailAddress('Example@example.com')
    assert ea2.email == 'Example@example.com'
    assert ea2.email_lower == 'example@example.com'
    assert ea2.blake2b160 == hash_map['example@example.com']
    assert ea1.email_canonical == 'example@example.com'
    assert ea2.blake2b160_canonical == hash_map['example@example.com']
    assert str(ea2) == 'Example@example.com'
    assert repr(ea2) == "EmailAddress('Example@example.com')"

    # Canonical representation's hash can be distinct from regular hash
    ea3 = EmailAddress('Example+Extra@example.com')
    assert ea3.email == 'Example+Extra@example.com'
    assert ea3.email_lower == 'example+extra@example.com'
    assert ea3.blake2b160 == hash_map['example+extra@example.com']
    assert ea1.email_canonical == 'example@example.com'
    assert ea3.blake2b160_canonical == hash_map['example@example.com']
    assert str(ea3) == 'Example+Extra@example.com'
    assert repr(ea3) == "EmailAddress('Example+Extra@example.com')"


def test_email_address_init_error():
    """EmailAddress constructor will reject various forms of bad input"""
    with pytest.raises(ValueError):
        # Must be a string
        EmailAddress(None)
    with pytest.raises(ValueError):
        # Must not be blank
        EmailAddress('')
    with pytest.raises(ValueError):
        # Must be syntactically valid
        EmailAddress('invalid')


def test_email_address_mutability():
    """EmailAddress can be mutated to change casing or delete the address only"""
    ea = EmailAddress('example@example.com')
    assert ea.email == 'example@example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # Case changes allowed, hash remains the same
    ea.email = 'Example@Example.com'
    assert ea.email == 'Example@Example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # Setting it to existing value is allowed
    ea.email = 'Example@Example.com'
    assert ea.email == 'Example@Example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # Nulling allowed, hash remains intact
    ea.email = None
    assert ea.email is None
    assert ea.blake2b160 == hash_map['example@example.com']

    # Restoring allowed (case insensitive)
    ea.email = 'exAmple@exAmple.com'
    assert ea.email == 'exAmple@exAmple.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # But changing to another email address is not allowed
    with pytest.raises(ValueError):
        ea.email = 'other@example.com'

    # Change is also not allowed by blanking and then setting to another
    ea.email = None
    with pytest.raises(ValueError):
        ea.email = 'other@example.com'


def test_email_address_md5():
    """EmailAddress has an MD5 method for legacy applications"""
    ea = EmailAddress('example@example.com')
    assert ea.md5() == '23463b99b62a72f26ed677cc556c44e8'
    ea.email = None
    assert ea.md5() is None


def test_email_address_is_blocked_flag():
    """EmailAddress has a read-only is_blocked flag that is normally False"""
    ea = EmailAddress('example@example.com')
    assert ea.is_blocked is False
    with pytest.raises(AttributeError):
        ea.is_blocked = True


@pytest.fixture(scope='function')
def clean_db(test_db_structure):
    """Fixture that removes all EmailAddress instances after a test"""
    yield test_db_structure
    test_db_structure.session.rollback()
    EmailAddress.query.delete(synchronize_session=False)
    test_db_structure.session.commit()


def test_email_address_can_commit(clean_db):
    """An EmailAddress can be committed to db"""
    db = clean_db
    ea = EmailAddress('example@example.com')
    db.session.add(ea)
    db.session.commit()


def test_email_address_conflict_integrity_error(clean_db):
    """A conflicting EmailAddress cannot be committed to db"""
    db = clean_db
    ea1 = EmailAddress('example@example.com')
    db.session.add(ea1)
    db.session.commit()
    ea2 = EmailAddress('example+extra@example.com')
    db.session.add(ea2)
    db.session.commit()
    ea3 = EmailAddress('Other@example.com')
    db.session.add(ea3)
    db.session.commit()
    # Conflicts with ea1 as email addresses are case preserving but not sensitive
    ea4 = EmailAddress('Example@example.com')
    db.session.add(ea4)
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_email_address_get(clean_db):
    """Email addresses can be loaded using EmailAddress.get"""
    db = clean_db
    ea1 = EmailAddress('example@example.com')
    ea2 = EmailAddress('example+extra@example.com')
    ea3 = EmailAddress('other@example.com')
    db.session.add_all([ea1, ea2, ea3])
    db.session.commit()

    get1 = EmailAddress.get('Example@example.com')
    assert get1 == ea1
    get2 = EmailAddress.get('example+Extra@example.com')
    assert get2 == ea2
    # Can also get by hash
    get3 = EmailAddress.get(blake2b160=hash_map['example@example.com'])
    assert get3 == ea1
    # Or by Base58 representation of hash
    get4 = EmailAddress.get(email_hash='2EGz72jxcsYjvXxF7r5rqfAgikor')
    assert get4 == ea1


def test_email_address_get_canonical(clean_db):
    """EmailAddress.get_canonical returns all matching records"""
    db = clean_db
    ea1 = EmailAddress('example@example.com')
    ea2 = EmailAddress('example+extra@example.com')
    ea3 = EmailAddress('other@example.com')
    db.session.add_all([ea1, ea2, ea3])
    db.session.commit()

    assert set(EmailAddress.get_canonical('Example@example.com')) == {ea1, ea2}


def test_email_address_add(clean_db):
    """Using EmailAddress.add will auto-add to session and return existing instances"""
    ea1 = EmailAddress.add('example@example.com')
    assert isinstance(ea1, EmailAddress)
    assert ea1.email == 'example@example.com'

    ea2 = EmailAddress.add('example+extra@example.com')
    ea3 = EmailAddress.add('other@example.com')
    ea4 = EmailAddress.add('Example@example.com')

    assert ea2 is not None
    assert ea3 is not None
    assert ea4 is not None

    assert ea2 != ea1
    assert ea3 != ea1
    assert ea4 == ea1

    # Email casing was amended by the call to EmailAddress.add
    assert ea1.email == 'Example@example.com'


def test_email_address_blocked(clean_db):
    """A blocked email address cannot be used via EmailAddress.add"""
    ea1 = EmailAddress.add('example@example.com')
    ea2 = EmailAddress.add('example+extra@example.com')
    ea3 = EmailAddress.add('other@example.com')

    EmailAddress.mark_blocked(ea2.email)

    assert ea1.is_blocked is True
    assert ea2.is_blocked is True
    assert ea3.is_blocked is False

    with pytest.raises(EmailAddressBlockedError):
        EmailAddress.add('Example@example.com')


def test_email_address_delivery_state(clean_db):
    """An email address can have last known delivery state set on it"""
    db = clean_db
    ea = EmailAddress.add('example@example.com')
    assert ea.delivery_state.UNKNOWN

    # Calling a transition will change state and set timestamp to update on commit
    ea.mark_sent()
    # An email was sent. Nothing more is known
    assert ea.delivery_state.NORMAL
    assert str(ea.delivery_state_at) == str(db.func.utcnow())

    # Recipient is known to be interacting with email (viewing or opening links)
    ea.mark_active()
    assert ea.delivery_state.ACTIVE
    assert str(ea.delivery_state_at) == str(db.func.utcnow())

    # Email address is soft bouncing (typically mailbox full)
    ea.mark_soft_bounce()
    assert ea.delivery_state.SOFT_BOUNCE
    assert str(ea.delivery_state_at) == str(db.func.utcnow())

    # Email is hard bouncing (typically mailbox invalid)
    ea.mark_hard_bounce()
    assert ea.delivery_state.HARD_BOUNCE
    assert str(ea.delivery_state_at) == str(db.func.utcnow())
