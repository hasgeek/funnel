"""Tests for model helpers."""
# pylint: disable=possibly-unused-variable,redefined-outer-name

from types import SimpleNamespace

from flask_babel import lazy_gettext
from sqlalchemy.exc import StatementError
import pytest
import sqlalchemy as sa

from funnel import models
import funnel.models.helpers as mhelpers


def test_valid_name() -> None:
    """Names are lowercase and contain letters, numbers and non-terminal hyphens."""
    assert mhelpers.valid_name('example person') is False
    assert mhelpers.valid_name('example_person') is False
    assert mhelpers.valid_name('exampleperson') is True
    assert mhelpers.valid_name('example1person') is True
    assert mhelpers.valid_name('1exampleperson') is True
    assert mhelpers.valid_name('exampleperson1') is True
    assert mhelpers.valid_name('example-person') is True
    assert mhelpers.valid_name('a') is True
    assert mhelpers.valid_name('a-') is False
    assert mhelpers.valid_name('ab-') is False
    assert mhelpers.valid_name('-a') is False
    assert mhelpers.valid_name('-ab') is False
    assert mhelpers.valid_name('Example Person') is False
    assert mhelpers.valid_name('Example_Person') is False
    assert mhelpers.valid_name('ExamplePerson') is False
    assert mhelpers.valid_name('Example1Person') is False
    assert mhelpers.valid_name('1ExamplePerson') is False
    assert mhelpers.valid_name('ExamplePerson1') is False
    assert mhelpers.valid_name('Example-Person') is False
    assert mhelpers.valid_name('A') is False
    assert mhelpers.valid_name('A-') is False
    assert mhelpers.valid_name('Ab-') is False
    assert mhelpers.valid_name('-A') is False
    assert mhelpers.valid_name('-Ab') is False


def test_valid_username() -> None:
    """Usernames contain letters, numbers and non-terminal hyphens."""
    assert mhelpers.valid_username('example person') is False
    assert mhelpers.valid_username('example-person') is False
    assert mhelpers.valid_username('exampleperson') is True
    assert mhelpers.valid_name('example1person') is True
    assert mhelpers.valid_name('1exampleperson') is True
    assert mhelpers.valid_name('exampleperson1') is True
    assert mhelpers.valid_username('example_person') is True
    assert mhelpers.valid_username('a') is True
    assert mhelpers.valid_username('a-') is False
    assert mhelpers.valid_username('ab-') is False
    assert mhelpers.valid_username('a_') is True
    assert mhelpers.valid_username('ab_') is True
    assert mhelpers.valid_username('-a') is False
    assert mhelpers.valid_username('-ab') is False
    assert mhelpers.valid_username('_a') is False
    assert mhelpers.valid_username('_ab') is False
    assert mhelpers.valid_username('Example Person') is False
    assert mhelpers.valid_username('Example-Person') is False
    assert mhelpers.valid_username('ExamplePerson') is True
    assert mhelpers.valid_username('Example1Person') is True
    assert mhelpers.valid_username('1ExamplePerson') is True
    assert mhelpers.valid_username('ExamplePerson1') is True
    assert mhelpers.valid_username('Example_Person') is True
    assert mhelpers.valid_username('A') is True
    assert mhelpers.valid_username('A-') is False
    assert mhelpers.valid_username('Ab-') is False
    assert mhelpers.valid_username('A_') is True
    assert mhelpers.valid_username('Ab_') is True
    assert mhelpers.valid_username('-A') is False
    assert mhelpers.valid_username('-Ab') is False
    assert mhelpers.valid_username('_A') is False
    assert mhelpers.valid_username('_Ab') is False


def test_reopen() -> None:
    """Test mhelpers.reopening a class to add more to it."""

    class UnrelatedMixin:
        pass

    class TestMetaclass(type):  # pylint: disable=unused-variable
        pass

    class OriginalClass:
        def spam(self):
            return "spam"

    saved_reference = OriginalClass

    @mhelpers.reopen(OriginalClass)
    class ReopenedClass:
        def eggs(self):
            return "eggs"

    # The decorator returns the original class with the decorated class's contents
    assert ReopenedClass is OriginalClass
    assert saved_reference is ReopenedClass
    assert ReopenedClass.spam is OriginalClass.spam  # type: ignore[attr-defined]
    assert ReopenedClass.eggs is OriginalClass.eggs  # type: ignore[attr-defined]

    # The decorator will refuse to process classes with base classes
    with pytest.raises(TypeError, match='cannot add base classes'):

        @mhelpers.reopen(OriginalClass)
        class Subclass(UnrelatedMixin):  # pylint: disable=unused-variable
            pass

    # The decorator will refuse to process classes with metaclasses
    with pytest.raises(TypeError, match='cannot add a metaclass'):

        @mhelpers.reopen(OriginalClass)
        class HasMetaclass(metaclass=TestMetaclass):  # pylint: disable=unused-variable
            pass

    # The decorator will refuse to process classes that affect the original's attributes
    # (__slots__, __getattribute__, __get/set/delattr__)
    with pytest.raises(TypeError, match='contains unsupported __attributes__'):

        @mhelpers.reopen(OriginalClass)
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
    @mhelpers.add_to_class(ReferenceClass)
    def eggs(self):  # skipcq: PTC-W0065
        return 'is_eggs'

    assert hasattr(ReferenceClass, 'eggs')
    assert ReferenceClass().eggs() == 'is_eggs'  # type: ignore[attr-defined]
    assert not hasattr(ReferenceClass, 'spameggs')
    assert not hasattr(ReferenceClass, 'spameggs_property')

    # New methods can have a custom name and can take any decorator valid in the class
    @mhelpers.add_to_class(ReferenceClass, 'spameggs')  # type: ignore[misc]
    @property
    def spameggs_property(self) -> str:
        return 'is_spameggs'

    assert hasattr(ReferenceClass, 'spameggs')
    assert not hasattr(ReferenceClass, 'spameggs_property')
    assert ReferenceClass.spameggs is spameggs_property
    assert ReferenceClass().spameggs == 'is_spameggs'  # type: ignore[attr-defined]

    # Existing attributes cannot be replaced
    with pytest.raises(AttributeError):

        @mhelpers.add_to_class(ReferenceClass, 'spameggs')
        def new_foobar(self):  # skipcq: PTC-W0049
            """Cause an AttributeError in the decorator."""


@pytest.fixture(scope='session')
def image_models(database, app):
    class MyImageModel(models.Model):
        __tablename__ = 'test_my_image_model'
        id = sa.orm.mapped_column(sa.Integer, primary_key=True)  # noqa: A003
        image_url = sa.orm.mapped_column(models.ImgeeType)

    with app.app_context():
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


@pytest.mark.parametrize(
    ('prefix', 'midway', 'query'),
    [
        ('', False, ''),
        ('', True, ''),
        ('@', False, '@%'),
        ('@', True, '%@%'),
        ('a', False, 'a%'),
        ('a', True, '%a%'),
        ('A', False, 'A%'),
        ('A', True, '%A%'),
        ('ab', False, 'ab%'),
        ('ab', True, '%ab%'),
        ('abc', False, 'abc%'),
        ('abc', True, '%abc%'),
        ('abc ', False, 'abc %'),
        ('abc ', True, '%abc %'),
        ('abc de', False, 'abc de%'),
        ('abc de', True, '%abc de%'),
        (' abc ', False, 'abc %'),
        (' abc ', True, '% abc %'),
        ('lu_tz', False, r'lu\_tz%'),
        ('lu_tz', True, r'%lu\_tz%'),
        ('ab[c]_%d', False, r'abc\_\%d%'),
        ('ab[c]_%d', True, r'%abc\_\%d%'),
    ],
)
def test_quote_autocomplete_like(prefix, midway, query) -> None:
    """Test that the LIKE-based autocomplete helper function escapes correctly."""
    assert mhelpers.quote_autocomplete_like(prefix, midway) == query


@pytest.mark.parametrize(
    ('prefix', 'tsquery'),
    [
        ('word', "'word':*"),  # Single word
        ('two words', "'two' <-> 'words':*"),  # Two words, no stemming
        ('am', "'am':*"),  # No stemming (would have been invalid ':*' otherwise)
    ],
)
def test_quote_autocomplete_tsquery(db_session, prefix, tsquery) -> None:
    assert (
        db_session.query(mhelpers.quote_autocomplete_tsquery(prefix)).scalar()
        == tsquery
    )


def test_message_composite() -> None:
    """Test mhelpers.MessageComposite has similar properties to MarkdownComposite."""
    text1 = mhelpers.MessageComposite("Text1")
    assert text1.text == "Text1"
    assert text1.html == "<p>Text1</p>"

    text2 = mhelpers.MessageComposite(lazy_gettext("Text2"))
    assert text2.text == "Text2"
    assert text2.html == "<p>Text2</p>"

    text3 = mhelpers.MessageComposite("Text3", 'del')
    assert text3.text == "Text3"
    assert text3.html == "<p><del>Text3</del></p>"

    text4 = mhelpers.MessageComposite(lazy_gettext("Text4"), 'mark')
    assert text4.text == "Text4"
    assert text4.html == "<p><mark>Text4</mark></p>"
