from types import SimpleNamespace

from sqlalchemy.exc import StatementError

import pytest

from funnel.models import ImgeeType, db
from funnel.models.helpers import add_to_class, reopen, valid_name, valid_username


def test_valid_name():
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


def test_valid_username():
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


def test_reopen():
    """Test reopening a class to add more to it."""

    class UnrelatedMixin:
        pass

    class OriginalClass:
        def foo(self):
            return "foo"

    saved_reference = OriginalClass

    @reopen(OriginalClass)
    class ReopenedClass:
        def bar(self):
            return "bar"

    # The decorator returns the original class with the decorated class's contents
    assert ReopenedClass is OriginalClass
    assert saved_reference is ReopenedClass
    assert ReopenedClass.foo is OriginalClass.foo
    assert ReopenedClass.bar is OriginalClass.bar

    # The decorator will refuse to process classes with base classes
    with pytest.raises(TypeError):

        @reopen(OriginalClass)
        class Subclass(UnrelatedMixin):
            pass

    # The decorator will refuse to process classes with metaclasses
    with pytest.raises(TypeError):

        @reopen(OriginalClass)
        class HasMetaclass(with_metaclass=UnrelatedMixin):
            pass

    # The decorator will refuse to process classes that affect the original's attributes
    # (__slots__, __getattribute__, __get/set/delattr__)
    with pytest.raises(TypeError):

        @reopen(OriginalClass)
        class HasSlots:
            __slots__ = ['foo', 'bar']


def test_add_to_class():
    """Add to class adds new attributes to a class."""

    class ReferenceClass:
        def foo(self):
            return 'is_foo'

    assert ReferenceClass().foo() == 'is_foo'
    assert not hasattr(ReferenceClass, 'bar')

    # New methods can be added
    @add_to_class(ReferenceClass)
    def bar(self):  # skipcq: PTC-W0065
        return 'is_bar'

    assert hasattr(ReferenceClass, 'bar')
    assert ReferenceClass().bar() == 'is_bar'
    assert not hasattr(ReferenceClass, 'foobar')
    assert not hasattr(ReferenceClass, 'foobar_property')

    # New methods can have a custom name and can take any decorator valid in the class
    @add_to_class(ReferenceClass, 'foobar')
    @property
    def foobar_property(self):
        return 'is_foobar'

    assert hasattr(ReferenceClass, 'foobar')
    assert not hasattr(ReferenceClass, 'foobar_property')
    assert ReferenceClass.foobar is foobar_property
    assert ReferenceClass().foobar == 'is_foobar'

    # Existing attributes cannot be replaced
    with pytest.raises(AttributeError):

        @add_to_class(ReferenceClass, 'foobar')
        def new_foobar(self):
            pass


@pytest.fixture(scope='session')
def image_models(database):
    class MyImageModel(db.Model):
        __tablename__ = 'my_image_model'
        id = db.Column(db.Integer, primary_key=True)
        image_url = db.Column(ImgeeType)

    database.create_all()
    return SimpleNamespace(**locals())


def test_imgeetype(db_session, image_models):
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
    assert m2.image_url.url == valid_url_with_resize
    assert m2.image_url.resize(120, 100).args['size'] == '120x100'
    assert m2.image_url.resize(120).args['size'] == '120'

    m2.image_url = valid_url_with_qs
    db_session.commit()
    assert m2.image_url.url == valid_url_with_qs
    assert m2.image_url.resize(120).args['foo'] == 'bar'
    assert m2.image_url.resize(120, 100).args['size'] == '120x100'
    assert m2.image_url.resize(120).args['size'] == '120'
