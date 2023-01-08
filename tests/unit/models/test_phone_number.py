"""Tests for PhoneNumber model."""

from types import SimpleNamespace
from typing import Generator

import sqlalchemy as sa

import pytest

from funnel import models

# This hash map should not be edited -- hashes are permanent
hash_map = {
    'not-a-valid-number': (
        b'\xd6\xac\xd6\x83\x8d\xbcu\xbf\x96ls\x9c\xe2\xda\xa2~?\xcd\x1c\x18'
    ),
    '+919845012345': b'\xa0=>k\x12\x0cC\xbf\x08\xf3F8`\xfd<\xeaW\x91\xe0\xfe',
    '+12345678900': b'\xdc\xc2\x93y\x14)3\xa1C\x94?\x06\xa7\x11\x14\xeaT\x94\xae\xac',
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


def test_phone_hash_stability() -> None:
    """Safety test to ensure phone_blakeb160_hash doesn't change spec."""
    phash = models.phone_number.phone_blake2b160_hash
    with pytest.raises(ValueError, match="Invalid phone number"):
        phash('not-a-valid-number')
    # However, insisting the number is pre-validated will generate a hash. This is only
    # useful when the number is actually pre-validated
    assert phash('not-a-valid-number', True) == hash_map['not-a-valid-number']
    # Number validation will attempt to find a matching prefix before hashing, and
    # will normalize formatting
    assert phash('9845012345') == phash('+91 9845012345') == hash_map['+919845012345']
    # Hashing for non-Indian numbers requires a full number, but variable formatting is
    # accepted
    assert phash('+12345678900') == phash('+1 234 567-8900') == hash_map['+12345678900']


def test_phone_number_refcount_drop(phone_models, db_session, refcount_data) -> None:
    """Test that PhoneNumber.refcount drop events are fired."""
    # The refcount changing signal handler will have received events for every phone
    # address in this test. A request teardown processor can use this to determine
    # which phone numberes need to be forgotten (preferably in a background job)

    # We have an empty set at the start of this test
    assert isinstance(refcount_data, set)
    assert refcount_data == set()

    pn = models.PhoneNumber.add('+919845012345')
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
    pn1 = models.PhoneNumber('9845012345')
    assert pn1.phone == '+919845012345'
    assert pn1.blake2b160 == hash_map['+919845012345']
    pn2 = models.PhoneNumber('+91 98450 12345')
    assert pn2.phone == '+919845012345'
