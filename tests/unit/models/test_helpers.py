"""Tests for model helpers."""
# pylint: disable=possibly-unused-variable

from types import SimpleNamespace

from sqlalchemy.exc import StatementError

from flask_babelhg import lazy_gettext

import pytest

from funnel.models import ImgeeType, db
from funnel.models.helpers import (
    MessageComposite,
    add_to_class,
    quote_autocomplete_tsquery,
    reopen,
    valid_name,
    valid_username,
)


def test_valid_name() -> None:
    """Names are lowercase and contain letters, numbers and non-terminal hyphens."""
    assert valid_name('example person') is False
    assert valid_name('example_person') is False
    assert valid_name('exampleperson') is True
    assert valid_name('example1person') is True
    assert valid_name('1exampleperson') is True
    assert valid_name('exampleperson1') is True
    assert valid_name('example-person') is True
    assert valid_name('a') is True
    assert valid_name('a-') is False
    assert valid_name('ab-') is False
    assert valid_name('-a') is False
    assert valid_name('-ab') is False
    assert valid_name('Example Person') is False
    assert valid_name('Example_Person') is False
    assert valid_name('ExamplePerson') is False
    assert valid_name('Example1Person') is False
    assert valid_name('1ExamplePerson') is False
    assert valid_name('ExamplePerson1') is False
    assert valid_name('Example-Person') is False
    assert valid_name('A') is False
    assert valid_name('A-') is False
    assert valid_name('Ab-') is False
    assert valid_name('-A') is False
    assert valid_name('-Ab') is False


def test_valid_username() -> None:
    """Usernames contain letters, numbers and non-terminal hyphens."""
    assert valid_username('example person') is False
    assert valid_username('example_person') is False
    assert valid_username('exampleperson') is True
    assert valid_name('example1person') is True
    assert valid_name('1exampleperson') is True
    assert valid_name('exampleperson1') is True
    assert valid_username('example-person') is True
    assert valid_username('a') is True
    assert valid_username('a-') is False
    assert valid_username('ab-') is False
    assert valid_username('-a') is False
    assert valid_username('-ab') is False
    assert valid_username('Example Person') is False
    assert valid_username('Example_Person') is False
    assert valid_username('ExamplePerson') is True
    assert valid_username('Example1Person') is True
    assert valid_username('1ExamplePerson') is True
    assert valid_username('ExamplePerson1') is True
    assert valid_username('Example-Person') is True
    assert valid_username('A') is True
    assert valid_username('A-') is False
    assert valid_username('Ab-') is False
    assert valid_username('-A') is False
    assert valid_username('-Ab') is False


def test_reopen() -> None:
    """Test reopening a class to add more to it."""

    class UnrelatedMixin:
        pass

    class TestMetaclass(type):  # pylint: disable=unused-variable
        pass

    class OriginalClass:
        def spam(self):
            return "spam"

    saved_reference = OriginalClass

    @reopen(OriginalClass)
    class ReopenedClass:
        def eggs(self):
            return "eggs"

    # The decorator returns the original class with the decorated class's contents
    assert ReopenedClass is OriginalClass
    assert saved_reference is ReopenedClass
    assert ReopenedClass.spam is OriginalClass.spam  # type: ignore[attr-defined]
    assert ReopenedClass.eggs is OriginalClass.eggs  # type: ignore[attr-defined]

    # The decorator will refuse to process classes with base classes
    with pytest.raises(TypeError):

        @reopen(OriginalClass)
        class Subclass(UnrelatedMixin):  # pylint: disable=unused-variable
            pass

    # The decorator will refuse to process classes with metaclasses
    with pytest.raises(TypeError):

        @reopen(OriginalClass)
        class HasMetaclass(metaclass=TestMetaclass):  # pylint: disable=unused-variable
            pass

    # The decorator will refuse to process classes that affect the original's attributes
    # (__slots__, __getattribute__, __get/set/delattr__)
    with pytest.raises(TypeError):

        @reopen(OriginalClass)
        class HasSlots:  # pylint: disable=unused-variable
            __slots__ = ['spam', 'eggs']


def test_add_to_class() -> None:
    """Add to class adds new attributes to a class."""

    class ReferenceClass:
        def spam(self):
            return 'is_spam'

    assert ReferenceClass().spam() == 'is_spam'
    assert not hasattr(ReferenceClass, 'eggs')

    # New methods can be added
    @add_to_class(ReferenceClass)  # skipcq: PTC-W0065
    def eggs(self):  # skipcq: PTC-W0065
        return 'is_eggs'

    assert hasattr(ReferenceClass, 'eggs')
    assert ReferenceClass().eggs() == 'is_eggs'  # type: ignore[attr-defined]
    assert not hasattr(ReferenceClass, 'spameggs')
    assert not hasattr(ReferenceClass, 'spameggs_property')

    # New methods can have a custom name and can take any decorator valid in the class
    @add_to_class(ReferenceClass, 'spameggs')  # type: ignore[misc]
    @property
    def spameggs_property(self):
        return 'is_spameggs'

    assert hasattr(ReferenceClass, 'spameggs')
    assert not hasattr(ReferenceClass, 'spameggs_property')
    assert ReferenceClass.spameggs is spameggs_property  # type: ignore[attr-defined]
    assert ReferenceClass().spameggs == 'is_spameggs'  # type: ignore[attr-defined]

    # Existing attributes cannot be replaced
    with pytest.raises(AttributeError):

        @add_to_class(ReferenceClass, 'spameggs')  # skipcq: PTC-W0049
        def new_foobar(self):
            pass


@pytest.fixture(scope='session')
def image_models(database):
    class MyImageModel(db.Model):
        __tablename__ = 'my_image_model'
        id = db.Column(db.Integer, primary_key=True)  # noqa: A003
        image_url = db.Column(ImgeeType)

    database.create_all()
    return SimpleNamespace(**locals())


def test_imgeetype(db_session, image_models) -> None:
    valid_url = "https://images.example.com/embed/file/randomimagehash"
    valid_url_with_resize = (
        "https://images.example.com/embed/file/randomimagehash?size=120x100"
    )
    valid_url_with_qs = "https://images.example.com/embed/file/randomimagehash?foo=bar"
    invalid_url = "https://example.com/embed/file/randomimagehash"

    m1 = image_models.MyImageModel(
        image_url=invalid_url,
    )
    db_session.add(m1)
    with pytest.raises(StatementError):
        db_session.commit()
    db_session.rollback()

    m2 = image_models.MyImageModel(
        image_url=valid_url,
    )
    db_session.add(m2)
    db_session.commit()
    assert m2.image_url.url == valid_url
    assert m2.image_url.resize(120, 100).args['size'] == '120x100'
    assert m2.image_url.resize(120).args['size'] == '120'
    # Confirm resizing did not mutate the URL
    assert m2.image_url.url == valid_url

    m2.image_url = valid_url_with_resize
    db_session.commit()
    assert m2.image_url.url == valid_url_with_resize  # type: ignore[attr-defined]
    assert (
        m2.image_url.resize(120, 100).args['size']  # type: ignore[attr-defined]
        == '120x100'
    )
    assert m2.image_url.resize(120).args['size'] == '120'  # type: ignore[attr-defined]

    m2.image_url = valid_url_with_qs
    db_session.commit()
    assert m2.image_url.url == valid_url_with_qs  # type: ignore[attr-defined]
    assert m2.image_url.resize(120).args['foo'] == 'bar'  # type: ignore[attr-defined]
    assert (
        m2.image_url.resize(120, 100).args['size']  # type: ignore[attr-defined]
        == '120x100'
    )
    assert m2.image_url.resize(120).args['size'] == '120'  # type: ignore[attr-defined]


def test_quote_autocomplete_tsquery() -> None:
    # Single word autocomplete
    assert quote_autocomplete_tsquery('word') == "'word':*"
    # Multi-word autocomplete with stemming
    assert quote_autocomplete_tsquery('two words') == "'two' <-> 'word':*"


def test_message_composite() -> None:
    """Test MessageComposite has similar properties to MarkdownComposite."""
    text1 = MessageComposite("Text1")
    assert text1.text == "Text1"
    assert text1.html == "<p>Text1</p>"

    text2 = MessageComposite(lazy_gettext("Text2"))
    assert text2.text == "Text2"
    assert text2.html == "<p>Text2</p>"

    text3 = MessageComposite("Text3", 'del')
    assert text3.text == "Text3"
    assert text3.html == "<p><del>Text3</del></p>"

    text4 = MessageComposite(lazy_gettext("Text4"), 'mark')
    assert text4.text == "Text4"
    assert text4.html == "<p><mark>Text4</mark></p>"
