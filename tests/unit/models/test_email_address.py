import pytest

from funnel.models.email_address import (
    EmailAddress,
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
