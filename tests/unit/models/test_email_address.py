from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

import pytest

from funnel.models import BaseMixin, db
from funnel.models.email_address import (
    EmailAddress,
    EmailAddressBlockedError,
    EmailAddressInUseError,
    EmailAddressMixin,
    canonical_email_representation,
    email_blake2b160_hash,
    email_normalized,
    emailaddress_refcount_dropping,
)

# Fixture used across tests.
hash_map = {
    'example@example.com': b'X5Q\xc1<\xceE<\x05\x9c\xa7\x0f\xee{\xcd\xc2\xe5\xbd\x82\xa1',
    'example+extra@example.com': b'\xcfi\xf2\xdfph\xc0\x81\xfb\xe8\\\xa6\xa5\xf1\xfb:\xbb\xe4\x88\xde',
    'example@gmail.com': b"\tC*\xd2\x9a\xcb\xdfR\xcb\xbf=>2D'(\xa8V\x13\xa7",
    'example@googlemail.com': b'x\xd6#Ue\xa8-_\xeclJ+o8\xfe\x1f\xa1\x0b:9',
    'eg@räksmörgås.org': b'g\xc4B`\x9ej\x05\xf8\xa6\x9b\\"l\x0c$\xd4\xa8\xe42j',
}


@pytest.fixture(scope='function')
def refcount_data():
    refcount_signal_fired = set()

    def refcount_signal_receiver(sender):
        refcount_signal_fired.add(sender)

    emailaddress_refcount_dropping.connect(refcount_signal_receiver)
    yield refcount_signal_fired
    emailaddress_refcount_dropping.disconnect(refcount_signal_receiver)


def test_email_normalized():
    """Normalized email addresses are lowercase, with IDN encoded into punycode"""
    assert email_normalized('example@example.com') == 'example@example.com'
    assert email_normalized('Example@Example.com') == 'example@example.com'
    assert email_normalized('Example+Extra@Example.com') == 'example+extra@example.com'
    # The following two examples are from
    # https://www.w3.org/2003/Talks/0425-duerst-idniri/slide12-0.html
    assert email_normalized('eg@räksmörgås.org') == 'eg@xn--rksmrgs-5wao1o.org'
    assert (
        email_normalized('ABC@納豆.w3.mag.keio.ac.jp')
        == 'abc@xn--99zt52a.w3.mag.keio.ac.jp'
    )


def test_email_hash_stability():
    """Safety test to ensure email_blakeb160_hash doesn't change spec"""
    ehash = email_blake2b160_hash
    assert ehash('example@example.com') == hash_map['example@example.com']
    # email_hash explicitly uses the normalized form (but not the canonical form)
    assert ehash('EXAMPLE@EXAMPLE.COM') == hash_map['example@example.com']
    assert ehash('example@gmail.com') == hash_map['example@gmail.com']
    assert ehash('example@googlemail.com') == hash_map['example@googlemail.com']
    assert ehash('eg@räksmörgås.org') == hash_map['eg@räksmörgås.org']


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
    with pytest.raises(ValueError):
        cemail('')
    with pytest.raises(ValueError):
        cemail('invalid')


def test_email_address_init():
    """EmailAddress instances can be created using a string email address"""

    # Ordinary use constructor passes without incident
    ea1 = EmailAddress('example@example.com')
    assert ea1.email == 'example@example.com'
    assert ea1.email_normalized == 'example@example.com'
    assert ea1.domain == 'example.com'
    assert ea1.blake2b160 == hash_map['example@example.com']
    assert ea1.email_canonical == 'example@example.com'
    assert ea1.blake2b160_canonical == hash_map['example@example.com']
    assert str(ea1) == 'example@example.com'
    assert repr(ea1) == "EmailAddress('example@example.com')"
    # Public hash (for URLs)
    assert ea1.email_hash == '2EGz72jxcsYjvXxF7r5rqfAgikor'

    # Case is preserved but disregarded for hashes
    ea2 = EmailAddress('Example@Example.com')
    assert ea2.email == 'Example@Example.com'
    assert ea2.email_normalized == 'example@example.com'
    assert ea2.domain == 'example.com'
    assert ea2.blake2b160 == hash_map['example@example.com']
    assert ea1.email_canonical == 'example@example.com'
    assert ea2.blake2b160_canonical == hash_map['example@example.com']
    assert str(ea2) == 'Example@Example.com'
    assert repr(ea2) == "EmailAddress('Example@Example.com')"

    # Canonical representation's hash can be distinct from regular hash
    ea3 = EmailAddress('Example+Extra@example.com')
    assert ea3.email == 'Example+Extra@example.com'
    assert ea3.email_normalized == 'example+extra@example.com'
    assert ea3.domain == 'example.com'
    assert ea3.blake2b160 == hash_map['example+extra@example.com']
    assert ea1.email_canonical == 'example@example.com'
    assert ea3.blake2b160_canonical == hash_map['example@example.com']
    assert str(ea3) == 'Example+Extra@example.com'
    assert repr(ea3) == "EmailAddress('Example+Extra@example.com')"

    # FIXME: There is no test for an IDN email address because the underlying pyIsEmail
    # validator does not support them. While we can encode the domain to punycode
    # before sending to pyIsEmail, this is insufficient as RFC6530 explicitly requires
    # support for non-ASCII characters in the mailbox portion. Support for IDN emails
    # therefore remains unavailable until pyIsEmail is updated, or another validator
    # is used.


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
    with pytest.raises(ValueError):
        # Must be syntactically valid (caught elsewhere internally)
        EmailAddress('@invalid')


def test_email_address_mutability():
    """EmailAddress can be mutated to change casing or delete the address only"""
    ea = EmailAddress('example@example.com')
    assert ea.email == 'example@example.com'
    assert ea.domain == 'example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # Case changes allowed, hash remains the same
    ea.email = 'Example@Example.com'
    assert ea.email == 'Example@Example.com'
    assert ea.domain == 'example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # Setting it to existing value is allowed
    ea.email = 'Example@Example.com'
    assert ea.email == 'Example@Example.com'
    assert ea.domain == 'example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # Nulling allowed, hash remains intact
    ea.email = None
    assert ea.email is None
    assert ea.domain is None
    assert ea.blake2b160 == hash_map['example@example.com']

    # Restoring allowed (case insensitive)
    ea.email = 'exAmple@exAmple.com'
    assert ea.email == 'exAmple@exAmple.com'
    assert ea.domain == 'example.com'
    assert ea.blake2b160 == hash_map['example@example.com']

    # But changing to another email address is not allowed
    with pytest.raises(ValueError):
        ea.email = 'other@example.com'

    # Change is also not allowed by blanking and then setting to another
    ea.email = None
    with pytest.raises(ValueError):
        ea.email = 'other@example.com'

    # Changing the domain is also not allowed
    with pytest.raises(AttributeError):
        ea.domain = 'gmail.com'

    # Setting to an invalid value is not allowed
    with pytest.raises(ValueError):
        ea.email = ''


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

    # A forgotten email address will be restored by calling EmailAddress.add
    ea3.email = None
    assert ea3.email is None
    ea5 = EmailAddress.add('other@example.com')
    assert ea5 == ea3
    assert ea5.email == ea3.email == 'other@example.com'


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
    """An email address can have the last known delivery state set on it"""
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

    # Sent email is soft bouncing (typically mailbox full)
    ea.mark_soft_fail()
    assert ea.delivery_state.SOFT_FAIL
    assert str(ea.delivery_state_at) == str(db.func.utcnow())

    # Sent email is hard bouncing (typically mailbox invalid)
    ea.mark_hard_fail()
    assert ea.delivery_state.HARD_FAIL
    assert str(ea.delivery_state_at) == str(db.func.utcnow())


# This fixture must be session scope as it cannot be called twice in the same process.
# SQLAlchemy models must only be defined once.
@pytest.fixture(scope='session')
def email_models():
    class EmailUser(BaseMixin, db.Model):
        """Test model representing a user account"""

        __tablename__ = 'emailuser'

    class EmailLink(EmailAddressMixin, BaseMixin, db.Model):
        """Test model connecting EmailUser to EmailAddress"""

        __email_optional__ = False
        __email_unique__ = True
        __email_for__ = 'emailuser'
        __email_is_exclusive__ = True

        emailuser_id = db.Column(db.ForeignKey('emailuser.id'), nullable=False)
        emailuser = db.relationship(EmailUser)

    class EmailDocument(EmailAddressMixin, BaseMixin, db.Model):
        """Test model unaffiliated to a user that has an email address attached"""

    class EmailLinkedDocument(EmailAddressMixin, BaseMixin, db.Model):
        """Test model that accepts an optional user and an optional email"""

        __email_for__ = 'emailuser'

        emailuser_id = db.Column(db.ForeignKey('emailuser.id'), nullable=True)
        emailuser = db.relationship(EmailUser)

    db.create_all()  # This will only create models not already in the database
    return SimpleNamespace(**locals())


@pytest.fixture(scope='function')
def clean_mixin_db(email_models, clean_db):
    """Fixture that removes all test model instances"""
    yield clean_db
    clean_db.session.rollback()
    email_models.EmailDocument.query.delete(synchronize_session=False)
    email_models.EmailLink.query.delete(synchronize_session=False)
    email_models.EmailUser.query.delete(synchronize_session=False)
    clean_db.session.commit()


def test_email_address_mixin(email_models, clean_mixin_db):
    """The EmailAddressMixin class adds safety checks for using an email address"""
    db = clean_mixin_db
    models = email_models

    blocked_email = EmailAddress('blocked@example.com')

    user1 = models.EmailUser()
    user2 = models.EmailUser()

    doc1 = models.EmailDocument()
    doc2 = models.EmailDocument()

    db.session.add_all([user1, user2, doc1, doc2, blocked_email])

    EmailAddress.mark_blocked('blocked@example.com')

    # Mixin-based classes can simply specify an email parameter to link to an
    # EmailAddress instance
    link1 = models.EmailLink(emailuser=user1, email='example@example.com')
    db.session.add(link1)
    ea1 = EmailAddress.get('example@example.com')
    assert link1.email == 'example@example.com'
    assert link1.email_address == ea1

    # Link an unrelated email address to another user to demonstrate that it works
    link2 = models.EmailLink(emailuser=user2, email='other@example.com')
    db.session.add(link2)
    ea2 = EmailAddress.get('other@example.com')
    assert link2.email == 'other@example.com'
    assert link2.email_address == ea2

    db.session.commit()

    # 'other@example.com' is now exclusive to user2. Attempting it to assign it to
    # user1 will raise an exception, even if the case is changed.
    with pytest.raises(EmailAddressInUseError):
        models.EmailLink(emailuser=user1, email='Other@example.com')

    # This safety catch works even if the email_address column is used:
    with pytest.raises(EmailAddressInUseError):
        models.EmailLink(emailuser=user1, email_address=ea2)

    db.session.rollback()

    # Blocked addresses cannot be used either
    with pytest.raises(EmailAddressBlockedError):
        models.EmailLink(emailuser=user1, email='blocked@example.com')

    with pytest.raises(EmailAddressBlockedError):
        models.EmailLink(emailuser=user1, email_address=blocked_email)

    db.session.rollback()

    # Attempting to assign 'other@example.com' to user2 a second time will cause a
    # SQL integrity error because EmailLink.__email_unique__ is True.
    link3 = models.EmailLink(emailuser=user2, email='Other@example.com')
    db.session.add(link3)
    with pytest.raises(IntegrityError):
        db.session.flush()

    del link3
    db.session.rollback()

    # The EmailDocument model, in contrast, has no requirement of availability to a
    # specific user, so it won't be blocked here despite being exclusive to user1
    assert doc1.email is None
    assert doc2.email is None
    assert doc1.email_address is None
    assert doc2.email_address is None

    doc1.email = 'example@example.com'
    doc2.email = 'example@example.com'

    assert doc1.email == 'example@example.com'
    assert doc2.email == 'example@example.com'
    assert doc1.email_address == ea1
    assert doc2.email_address == ea1

    # ea1 now has three references, while ea2 has 1
    assert ea1.refcount() == 3
    assert ea2.refcount() == 1

    # Setting the email property on EmailDocument will mutate
    # EmailDocument.email_address and not EmailDocument.email_address.email
    assert ea1.email == 'example@example.com'
    doc1.email = None
    assert ea1.email == 'example@example.com'
    assert doc1.email_address is None
    doc2.email = 'other@example.com'
    assert ea1.email == 'example@example.com'
    assert doc2.email_address == ea2

    # EmailLinkedDocument takes the complexity up a notch

    # A document linked to a user can use any email linked to that user
    ldoc1 = models.EmailLinkedDocument(emailuser=user1, email='example@example.com')
    db.session.add(ldoc1)
    assert ldoc1.emailuser == user1
    assert ldoc1.email_address == ea1

    # But another user can't use this email address
    with pytest.raises(EmailAddressInUseError):
        models.EmailLinkedDocument(emailuser=user2, email='example@example.com')

    # This restriction also applies when user is not specified. Here, this email is
    # claimed by user2 above
    with pytest.raises(EmailAddressInUseError):
        models.EmailLinkedDocument(emailuser=None, email='other@example.com')

    # But it works with an unaffiliated email address
    ldoc2 = models.EmailLinkedDocument(email='yetanother@example.com')
    db.session.add(ldoc2)
    assert ldoc2.emailuser is None
    assert ldoc2.email == 'yetanother@example.com'

    ldoc3 = models.EmailLinkedDocument(emailuser=user2, email='onemore@example.com')
    db.session.add(ldoc3)
    assert ldoc3.emailuser is user2
    assert ldoc3.email == 'onemore@example.com'

    # Setting the email to None on the document removes the link to the EmailAddress,
    # but does not blank out the EmailAddress

    assert ldoc1.email_address == ea1
    assert ea1.email == 'example@example.com'
    ldoc1.email = None
    assert ldoc1.email_address is None
    assert ea1.email == 'example@example.com'


def test_email_address_refcount_drop(email_models, clean_mixin_db, refcount_data):
    """Test that EmailAddress.refcount drop events are fired"""
    db = clean_mixin_db
    models = email_models

    # The refcount changing signal handler will have received events for every email
    # address in this test. A request teardown processor can use this to determine
    # which email addresses need to be forgotten (preferably in a background job)

    # We have an empty set at the start of this test
    assert isinstance(refcount_data, set)
    assert refcount_data == set()

    ea = EmailAddress.add('example@example.com')
    assert refcount_data == set()

    user = models.EmailUser()
    doc = models.EmailDocument()
    link = models.EmailLink(emailuser=user, email_address=ea)
    db.session.add_all([ea, user, doc, link])

    assert refcount_data == set()

    doc.email_address = ea
    assert refcount_data == set()
    assert ea.refcount() == 2

    doc.email_address = None
    assert refcount_data == {ea}
    assert ea.refcount() == 1

    refcount_data.remove(ea)
    assert refcount_data == set()
    db.session.commit()  # Persist before deleting
    db.session.delete(link)
    db.session.commit()
    assert refcount_data == {ea}
    assert ea.refcount() == 0


def test_email_address_validate_for(email_models, clean_mixin_db):
    """EmailAddress.validate_for can be used to determine availability"""
    db = clean_mixin_db
    models = email_models

    user1 = models.EmailUser()
    user2 = models.EmailUser()
    anon_user = None
    db.session.add_all([user1, user2])

    # A new email address is available to all
    assert EmailAddress.validate_for(user1, 'example@example.com') is True
    assert EmailAddress.validate_for(user2, 'example@example.com') is True
    assert EmailAddress.validate_for(anon_user, 'example@example.com') is True

    # Once it's assigned to a user, availability changes
    link = models.EmailLink(emailuser=user1, email='example@example.com')
    db.session.add(link)

    assert EmailAddress.validate_for(user1, 'example@example.com') is True
    assert EmailAddress.validate_for(user2, 'example@example.com') is False
    assert EmailAddress.validate_for(anon_user, 'example@example.com') is False

    # When delivery state changes, validate_for's result changes too
    ea = link.email_address
    assert ea.delivery_state.UNKNOWN

    ea.mark_sent()
    assert ea.delivery_state.NORMAL
    assert EmailAddress.validate_for(user1, 'example@example.com') is True
    assert EmailAddress.validate_for(user2, 'example@example.com') is False
    assert EmailAddress.validate_for(anon_user, 'example@example.com') is False

    ea.mark_active()
    assert ea.delivery_state.ACTIVE
    assert EmailAddress.validate_for(user1, 'example@example.com') is True
    assert EmailAddress.validate_for(user2, 'example@example.com') is False
    assert EmailAddress.validate_for(anon_user, 'example@example.com') is False

    ea.mark_soft_fail()
    assert ea.delivery_state.SOFT_FAIL
    assert EmailAddress.validate_for(user1, 'example@example.com') == 'soft_fail'
    assert EmailAddress.validate_for(user2, 'example@example.com') is False
    assert EmailAddress.validate_for(anon_user, 'example@example.com') is False

    ea.mark_hard_fail()
    assert ea.delivery_state.HARD_FAIL
    assert EmailAddress.validate_for(user1, 'example@example.com') == 'hard_fail'
    assert EmailAddress.validate_for(user2, 'example@example.com') is False
    assert EmailAddress.validate_for(anon_user, 'example@example.com') is False

    # A blocked address is available to no one
    db.session.add(EmailAddress('blocked@example.com'))
    EmailAddress.mark_blocked('blocked@example.com')
    assert EmailAddress.validate_for(user1, 'blocked@example.com') is False
    assert EmailAddress.validate_for(user2, 'blocked@example.com') is False
    assert EmailAddress.validate_for(anon_user, 'blocked@example.com') is False
