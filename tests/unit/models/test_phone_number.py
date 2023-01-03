"""Tests for PhoneNumber model."""

from types import SimpleNamespace

import sqlalchemy as sa

import pytest

from funnel import models

# Fixture used across tests.
hash_map = {'+91': b''}


# This fixture must be session scope as it cannot be called twice in the same process.
# SQLAlchemy models must only be defined once. A model can theoretically be removed,
# but there is no formal API. Removal has at least three parts:
# 1. Remove class from mapper registry using ``db.Model.registry._dispose_cls(cls)``
# 2. Remove table from metadata using db.metadata.remove(cls.__table__)
# 3. Remove all relationships to other classes (unsolved)
@pytest.fixture(scope='session')
def phone_models(database, app):
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

        phoneuser_id = sa.Column(sa.ForeignKey('phoneuser.id'), nullable=False)
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

        phoneuser_id = sa.Column(sa.ForeignKey('phoneuser.id'), nullable=True)
        phoneuser = sa.orm.relationship(PhoneUser)

    new_models = [PhoneUser, PhoneLink, PhoneDocument, PhoneLinkedDocument]

    # These models do not use __bind_key__ so no bind is provided to create_all/drop_all
    with app.app_context():
        database.metadata.create_all(
            bind=database.engine, tables=[model.__table__ for model in new_models]
        )
    yield SimpleNamespace(**{model.__name__: model for model in new_models})
    with app.app_context():
        database.metadata.drop_all(
            bind=database.engine, tables=[model.__table__ for model in new_models]
        )


@pytest.fixture()
def refcount_data(funnel):
    refcount_signal_fired = set()

    def refcount_signal_receiver(sender):
        refcount_signal_fired.add(sender)

    funnel.signals.phonenumber_refcount_dropping.connect(refcount_signal_receiver)
    yield refcount_signal_fired
    funnel.signals.phonenumber_refcount_dropping.disconnect(refcount_signal_receiver)


def test_phone_number_refcount_drop(phone_models, db_session, refcount_data) -> None:
    """Test that PhoneNumber.refcount drop events are fired."""
    # The refcount changing signal handler will have received events for every phone
    # address in this test. A request teardown processor can use this to determine
    # which phone numberes need to be forgotten (preferably in a background job)

    # We have an empty set at the start of this test
    assert isinstance(refcount_data, set)
    assert refcount_data == set()

    ea = models.PhoneNumber.add('+919845012345')
    assert refcount_data == set()

    user = phone_models.PhoneUser()
    doc = phone_models.PhoneDocument()
    link = phone_models.PhoneLink(phoneuser=user, phone_number=ea)
    db_session.add_all([ea, user, doc, link])

    assert refcount_data == set()

    doc.phone_number = ea
    assert refcount_data == set()
    assert ea.refcount() == 2

    doc.phone_number = None
    assert refcount_data == {ea}
    assert ea.refcount() == 1

    refcount_data.remove(ea)
    assert refcount_data == set()
    db_session.commit()  # Persist before deleting
    db_session.delete(link)
    db_session.commit()
    assert refcount_data == {ea}
    assert ea.refcount() == 0
