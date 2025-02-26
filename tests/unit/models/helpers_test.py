"""Tests for model helpers."""

# pylint: disable=possibly-unused-variable,redefined-outer-name

from collections.abc import Callable, Generator
from types import SimpleNamespace
from typing import LiteralString, cast

import pytest
import sqlalchemy.orm as sa_orm
from flask_babel import lazy_gettext as lazy_gettext_base
from furl import furl
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Mapped

import funnel.models.helpers as mhelpers
from funnel import models

from ...conftest import Flask, SQLAlchemy, scoped_session

lazy_gettext = cast(Callable[[LiteralString], str], lazy_gettext_base)


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


def test_valid_account_name() -> None:
    """Usernames contain letters, numbers and non-terminal hyphens."""
    assert mhelpers.valid_account_name('example person') is False
    assert mhelpers.valid_account_name('example-person') is False
    assert mhelpers.valid_account_name('exampleperson') is True
    assert mhelpers.valid_name('example1person') is True
    assert mhelpers.valid_name('1exampleperson') is True
    assert mhelpers.valid_name('exampleperson1') is True
    assert mhelpers.valid_account_name('example_person') is True
    assert mhelpers.valid_account_name('a') is True
    assert mhelpers.valid_account_name('a-') is False
    assert mhelpers.valid_account_name('ab-') is False
    assert mhelpers.valid_account_name('a_') is True
    assert mhelpers.valid_account_name('ab_') is True
    assert mhelpers.valid_account_name('-a') is False
    assert mhelpers.valid_account_name('-ab') is False
    assert mhelpers.valid_account_name('_a') is False
    assert mhelpers.valid_account_name('_ab') is False
    assert mhelpers.valid_account_name('Example Person') is False
    assert mhelpers.valid_account_name('Example-Person') is False
    assert mhelpers.valid_account_name('ExamplePerson') is True
    assert mhelpers.valid_account_name('Example1Person') is True
    assert mhelpers.valid_account_name('1ExamplePerson') is True
    assert mhelpers.valid_account_name('ExamplePerson1') is True
    assert mhelpers.valid_account_name('Example_Person') is True
    assert mhelpers.valid_account_name('A') is True
    assert mhelpers.valid_account_name('A-') is False
    assert mhelpers.valid_account_name('Ab-') is False
    assert mhelpers.valid_account_name('A_') is True
    assert mhelpers.valid_account_name('Ab_') is True
    assert mhelpers.valid_account_name('-A') is False
    assert mhelpers.valid_account_name('-Ab') is False
    assert mhelpers.valid_account_name('_A') is False
    assert mhelpers.valid_account_name('_Ab') is False


def test_reopen() -> None:
    """Test mhelpers.reopening a class to add more to it."""

    class UnrelatedMixin:
        pass

    class TestMetaclass(type):  # pylint: disable=unused-variable
        pass

    class OriginalClass:
        def spam(self) -> str:
            return "spam"

    saved_reference = OriginalClass

    @mhelpers.reopen(OriginalClass)
    class ReopenedClass:
        def eggs(self) -> str:
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
    with pytest.raises(TypeError, match='contains unsupported __dunder__'):

        @mhelpers.reopen(OriginalClass)
        class HasSlots:  # pylint: disable=unused-variable
            __slots__ = ['eggs', 'spam']


def test_add_to_class() -> None:
    """Add to class adds new attributes to a class."""

    class ReferenceClass:
        def spam(self) -> str:
            return 'is_spam'

    assert ReferenceClass().spam() == 'is_spam'
    assert not hasattr(ReferenceClass, 'eggs')

    # New methods can be added
    @mhelpers.add_to_class(ReferenceClass)
    def eggs(self: ReferenceClass) -> str:  # skipcq: PTC-W0065
        return 'is_eggs'

    assert hasattr(ReferenceClass, 'eggs')
    assert ReferenceClass().eggs() == 'is_eggs'  # type: ignore[attr-defined]
    assert not hasattr(ReferenceClass, 'spameggs')
    assert not hasattr(ReferenceClass, 'spameggs_property')

    # New methods can have a custom name and can take any decorator valid in the class
    @mhelpers.add_to_class(ReferenceClass, 'spameggs')  # type: ignore[misc]
    @property
    def spameggs_property(self: ReferenceClass) -> str:
        return 'is_spameggs'

    assert hasattr(ReferenceClass, 'spameggs')
    assert not hasattr(ReferenceClass, 'spameggs_property')
    assert ReferenceClass.spameggs is spameggs_property  # pyright: ignore[reportAttributeAccessIssue]
    assert ReferenceClass().spameggs == 'is_spameggs'  # type: ignore[attr-defined]

    # Existing attributes cannot be replaced
    with pytest.raises(AttributeError):

        @mhelpers.add_to_class(ReferenceClass, 'spameggs')
        def new_foobar(self: ReferenceClass) -> None:  # skipcq: PTC-W0049
            """Cause an AttributeError in the decorator."""


@pytest.fixture(scope='session')
def image_models(
    database: SQLAlchemy, app: Flask
) -> Generator[SimpleNamespace, None, None]:
    class MyImageModel(models.Model):
        __tablename__ = 'test_my_image_model'
        id: Mapped[int] = sa_orm.mapped_column(primary_key=True)
        image_url: Mapped[furl] = sa_orm.mapped_column(models.ImgeeType)

    new_models = [MyImageModel]

    sa_orm.configure_mappers()
    # These models do not use __bind_key__ so no bind is provided to create_all/drop_all
    with app.app_context():
        database.metadata.create_all(
            bind=database.engine,
            tables=[model.__table__ for model in new_models],
        )
    yield SimpleNamespace(**{model.__name__: model for model in new_models})
    with app.app_context():
        database.metadata.drop_all(
            bind=database.engine,
            tables=[model.__table__ for model in new_models],
        )


def test_imgeetype(db_session: scoped_session, image_models: SimpleNamespace) -> None:
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
        ('\\', False, r'\\%'),
        ('\\', True, r'%\\%'),
        ('ab\\cd', False, r'ab\\cd%'),
        ('ab\\cd', True, r'%ab\\cd%'),
        ('\\%', False, r'\\\%%'),
        ('\\%', True, r'%\\\%%'),
    ],
)
def test_quote_autocomplete_like(prefix: str, midway: bool, query: str) -> None:
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
def test_quote_autocomplete_tsquery(
    db_session: scoped_session, prefix: str, tsquery: str
) -> None:
    assert (
        db_session.query(mhelpers.quote_autocomplete_tsquery(prefix)).scalar()
        == tsquery
    )


def test_message_composite() -> None:
    """Test MessageComposite has similar properties to MarkdownComposite."""
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
