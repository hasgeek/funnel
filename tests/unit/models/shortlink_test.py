"""Test Shortlink model."""

# The example URLs used here are as per RFC 2606 and RFC 6761
# https://datatracker.ietf.org/doc/html/rfc2606#section-3
# https://datatracker.ietf.org/doc/html/rfc6761#section-6.5

# Since a random number generator is not a unique number generator, some tests are
# marked as flaky and will be re-run in case a dupe value is generated

from collections.abc import Sequence
from typing import Any
from unittest.mock import patch

import pytest
from furl import furl

from funnel import models

from ...conftest import scoped_session


class MockRandomBigint:
    """Mock for random_bigint that returns from a pre-determined sequence."""

    def __init__(self, sequence: Sequence[int]) -> None:
        self.sequence = sequence
        self.counter = 0

    def __call__(self, smaller: bool = False) -> Any:
        value = self.sequence[self.counter % len(self.sequence)]
        self.counter += 1
        return value


@pytest.mark.flaky(reruns=2)
def test_random_bigint() -> None:
    """Random numbers are within expected range (this test depends on luck)."""
    randset = set()
    for _loop in range(1000):
        num = models.shortlink.random_bigint()
        assert num != 0
        # Bigints are 64-bit (8 bytes). That gives us 63 bits + 1 bit for sign
        assert -(2**63) <= num <= 2**63 - 1
        randset.add(num)
    # Ignore up to 2 collisions
    assert len(randset) == 1000


@pytest.mark.flaky(reruns=2)
def test_smaller_random_int() -> None:
    """Smaller random numbers are within expected range (this test depends on luck)."""
    randset = set()
    for _loop in range(1000):
        num = models.shortlink.random_bigint(True)
        # Smaller ids are 24-bit (3 bytes) and not signed, since they are significantly
        # within bigint sign bit range
        assert 0 < num <= 2**24 - 1
        randset.add(num)
    assert len(randset) == 1000


def test_mock_random_bigint() -> None:
    """Test that MockRandomBigint works as expected."""
    prng_values = [43, 123, 5345, 123, 5435]
    mockfunc = MockRandomBigint(prng_values)

    extracted_values = [mockfunc() for _c in range(len(prng_values) * 2)]
    assert extracted_values == prng_values + prng_values

    with patch(
        'funnel.models.shortlink.random_bigint', wraps=MockRandomBigint(prng_values)
    ):
        extracted_values = [
            models.shortlink.random_bigint() for _c in range(len(prng_values) * 2)
        ]
        assert extracted_values == prng_values + prng_values


@pytest.mark.parametrize(
    ('lhs', 'rhs'),
    [
        ('https://example.com', '//example.com'),
        ('https://example.com/', 'https://example.com'),
    ],
)
def test_url_hash_is_normalized(lhs: str, rhs: str) -> None:
    """URL hash is normalized and handles furl objects."""
    assert models.shortlink.url_blake2b160_hash(
        lhs
    ) == models.shortlink.url_blake2b160_hash(rhs)
    assert models.shortlink.url_blake2b160_hash(
        furl(lhs)
    ) == models.shortlink.url_blake2b160_hash(rhs)
    assert models.shortlink.url_blake2b160_hash(
        lhs
    ) == models.shortlink.url_blake2b160_hash(furl(rhs))


def test_url_hash_is_constant() -> None:
    """URL hashes are a guaranteed identical output (including in the future)."""
    # These values should never need revision.
    example_com = 'https://example.com/'
    example_com_hash = (
        b'\x97\xb9z\xc1\x7f\xbb~\x82\x06\x0c\xc9\xcf"\x97\xb2\x90\xeeT\x98\x96'
    )

    assert models.shortlink.url_blake2b160_hash(example_com) == example_com_hash
    assert models.shortlink.url_blake2b160_hash(furl(example_com)) == example_com_hash


#: These mappings are bi-directional.
name_bigint_mappings = [
    ('', 0),
    ('hello', 2691033477),
    ('_', 252),
    ('__9_', 8388607),
    ('_________38', 9223372036854775807),
    ('AAAAAAAAAI', -9223372036854775808),
    ('__________8', -1),
    ('_v________8', -2),
]

#: These mappings are name -> bigint only because of the trailing capital A
uni_name_bigint_mappings = [
    ('A', 0),
    ('AA', 0),
    ('helloA', 2691033477),
    ('helloAA', 2691033477),
    ('AAAAAAAAAIA', -9223372036854775808),
]


@pytest.mark.parametrize(('name', 'bigint'), name_bigint_mappings)
def test_bigint_to_name(name: str, bigint: int) -> None:
    """Bigints can be mapped to names."""
    assert models.shortlink.bigint_to_name(bigint) == name


@pytest.mark.parametrize(
    ('name', 'bigint'), name_bigint_mappings + uni_name_bigint_mappings
)
def test_name_to_bigint(name: str, bigint: int) -> None:
    """Names can be mapped to bigints."""
    # Works with `str`
    assert models.shortlink.name_to_bigint(name) == bigint
    # Works with `bytes`
    assert models.shortlink.name_to_bigint(name.encode()) == bigint


def test_name_to_bigint_data_type() -> None:
    """name_to_bigint is fussy about data type."""
    # Calling with something not str or bytes will raise an error
    with pytest.raises(TypeError):
        models.shortlink.name_to_bigint(12345)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        models.shortlink.name_to_bigint(True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        models.shortlink.name_to_bigint(None)  # type: ignore[arg-type]

    # Value is too long (length limit is 11)
    with pytest.raises(ValueError, match='Shortlink name is too long'):
        models.shortlink.name_to_bigint('A' * 12)
    with pytest.raises(ValueError, match='Shortlink name is too long'):
        models.shortlink.name_to_bigint('B' * 12)

    # Value contains invalid characters
    with pytest.raises(ValueError, match='Shortlink name contains invalid characters'):
        models.shortlink.name_to_bigint('A/B')
    with pytest.raises(ValueError, match='Shortlink name contains invalid characters'):
        models.shortlink.name_to_bigint('A@B')


@pytest.mark.usefixtures('db_session')
def test_shortlink_id_equals_zero() -> None:
    """Shortlink cannot have an id of 0."""
    with pytest.raises(ValueError, match='Id cannot be zero'):
        models.shortlink.Shortlink(id=0)


@pytest.mark.usefixtures('db_session')
def test_shortlink_url_is_normalized() -> None:
    """Shortlink URLs are normalized."""
    sl = models.shortlink.Shortlink(url='https://example.com')
    assert sl.url == 'https://example.com/'


@pytest.mark.usefixtures('db_session')
def test_shortlink_without_id_has_empty_name() -> None:
    """Shortlink without an id has empty name."""
    sl = models.shortlink.Shortlink()
    assert sl.name == ''


@pytest.mark.usefixtures('db_session')
def test_shortlink_with_small_id_has_short_name() -> None:
    """Shortlink with small id has a short name."""
    sl = models.shortlink.Shortlink(id=1)
    assert sl.name == 'AQ'


@pytest.mark.usefixtures('db_session')
def test_shortlink_gets_id_from_name() -> None:
    """Shortlink with a name will get an id from the name."""
    sl = models.shortlink.Shortlink(name='AQ')
    assert sl.id == 1


@pytest.mark.usefixtures('db_session')
def test_constructor_reuse_with_name() -> None:
    """Shortlink constructor with both `reuse` and `name` will fail."""
    with pytest.raises(TypeError):
        models.shortlink.Shortlink.new(  # type: ignore[call-overload]
            'https://example.com/', reuse=True, name='example'
        )


@pytest.mark.usefixtures('db_session')
def test_shortlink_constructor_with_reuse() -> None:
    """Shortlink constructor will return existing when asked to reuse."""
    sl1 = models.shortlink.Shortlink.new('https://example.com', reuse=True)
    sl2 = models.shortlink.Shortlink.new('https://example.org', reuse=True)
    assert sl1 != sl2

    # db_session.add(...) is not required because Shortlink already adds to session
    # db_session.commit() is not required for this test because Shortlink does not
    # disable autoflush
    sl3 = models.shortlink.Shortlink.new('https://example.com/', reuse=True)
    assert sl3 == sl1
    assert sl3.id == sl1.id
    assert sl3 != sl2
    assert sl3.id != sl2.id


@pytest.mark.parametrize(
    ('longid', 'match'), [(146727516324, False), (-1, False), (4235324, True)]
)
def test_shortlink_reuse_with_shorter(
    db_session: scoped_session, longid: int, match: bool
) -> None:
    """Shortlink reuse with shorter will avoid longer ids."""
    sl1 = models.shortlink.Shortlink(id=longid, url='https://example.com')
    db_session.add(sl1)
    sl2 = models.shortlink.Shortlink.new(
        url='https://example.com', shorter=True, reuse=True
    )
    assert (sl2.id == sl1.id) is match


@pytest.mark.usefixtures('db_session')
@pytest.mark.filterwarnings('ignore:New instance')
def test_shortlink_constructor_with_name() -> None:
    """Shortlink constructor will accept a name."""
    sl1 = models.shortlink.Shortlink.new('https://example.com', name='example')
    assert sl1.name == 'example'

    with pytest.raises(ValueError, match='name is not available'):
        # This will cause an SAWarning before it raises ValueError. We ignore it
        # using the filterwarnings decorator:
        #     SAWarning: New instance <Shortlink at 0x...> with identity key
        #     (<class 'funnel.models.shortlink.Shortlink'>, (141113946412667,), None)
        #     conflicts with persistent instance <Shortlink at 0x...>
        models.shortlink.Shortlink.new('https://example.org', name='example')

    # The db transaction remains open after an error, allowing additional inserts
    sl2 = models.shortlink.Shortlink.new('https://example.org', name='example_org')
    sl3 = models.shortlink.Shortlink.new('https://example.org', reuse=True)
    assert sl3 == sl2
    assert sl3.id == sl2.id
    assert sl3.name == sl2.name == 'example_org'


@pytest.mark.filterwarnings('ignore:New instance')
def test_shortlink_constructor_handle_collisions(
    db_session: scoped_session,
) -> None:
    """Shortlink constructor will handle random id collisions gracefully."""
    prngids = MockRandomBigint([42, 42, 128, 128, 128, 384])
    with patch(
        'funnel.models.shortlink.random_bigint',
        wraps=prngids,
    ) as mockid:
        sl1 = models.shortlink.Shortlink.new('https://example.org')
        assert sl1.id == 42
        assert mockid.call_count == 1
        mockid.assert_called_with(False)
        mockid.reset_mock()

        sl2 = models.shortlink.Shortlink.new('https://example.com', shorter=False)
        assert sl2.id == 128
        assert mockid.call_count == 2  # Returned 42 the first time, 128 second time
        mockid.assert_called_with(False)
        mockid.reset_mock()

        sl3 = models.shortlink.Shortlink.new('https://example.net', shorter=True)
        assert sl3.id == 384
        assert mockid.call_count == 3  # Returned 128, 128, 384
        mockid.assert_called_with(True)  # Called with smaller=True
        mockid.reset_mock()

        sl4 = models.shortlink.Shortlink.new('https://example.org', name='example')
        assert sl4.name == 'example'
        assert mockid.call_count == 0
        mockid.reset_mock()

    # SQLAlchemy will issue SAWarning about reused ids:
    #     SAWarning: New instance <Shortlink at 0x...> with identity key
    #     (<class 'funnel.models.shortlink.Shortlink'>, (128,), None) conflicts with
    #     persistent instance <Shortlink at 0x...>
    # Test that the previous instances were not mangled:
    assert sl1 != sl2 != sl3 != sl4
    assert sl1 in db_session
    assert sl1.id == 42
    assert sl1.url == 'https://example.org/'
    assert sl2 in db_session
    assert sl2.id == 128
    assert sl2.url == 'https://example.com/'
    assert sl3 in db_session
    assert sl3.id == 384
    assert sl3.url == 'https://example.net/'
    assert sl4 in db_session
    assert sl4.name == 'example'
    assert sl4.url == 'https://example.org/'


@pytest.mark.usefixtures('db_session')
def test_shortlink_new_profanity_filter() -> None:
    """Generated shortlink ids are tested against a profanity filter."""
    prngids = MockRandomBigint(
        [
            models.shortlink.name_to_bigint('works'),
            models.shortlink.name_to_bigint('xxx'),
            models.shortlink.name_to_bigint('sexy'),
            models.shortlink.name_to_bigint('okay'),
        ]
    )
    with patch(
        'funnel.models.shortlink.random_bigint',
        wraps=prngids,
    ) as mockid:
        sl1 = models.shortlink.Shortlink.new('https://example.org')
        assert sl1.name == 'works'
        assert mockid.call_count == 1
        mockid.reset_mock()

        sl2 = models.shortlink.Shortlink.new('https://example.com')
        assert sl2.name == 'okay'
        assert mockid.call_count == 3  # Middle mocks got dropped by profanity filter
        mockid.reset_mock()


@pytest.mark.usefixtures('db_session')
def test_shortlink_name_available() -> None:
    """Shortlink has a `name_available` classmethod to test for availability."""
    assert models.shortlink.Shortlink.name_available('example') is True
    models.shortlink.Shortlink.new('https://example.org', name='example')
    assert models.shortlink.Shortlink.name_available('example') is False
    assert models.shortlink.Shortlink.name_available('example_org') is True
    assert models.shortlink.Shortlink.name_available('example_too_long') is False


@pytest.mark.usefixtures('db_session')
def test_shortlink_get() -> None:
    """Shortlink has a `get` classmethod."""
    assert models.shortlink.Shortlink.get('example') is None
    models.shortlink.Shortlink.new('https://example.org', name='example')
    sl = models.shortlink.Shortlink.get('example')
    assert sl is not None
    assert sl.name == 'example'
    assert models.shortlink.Shortlink.get('example_org') is None
    assert models.shortlink.Shortlink.get('example_too_long') is None

    sl.enabled = False
    assert models.shortlink.Shortlink.get('example') is None
    assert models.shortlink.Shortlink.get('example', True) == sl


def test_shortlink_comparator() -> None:
    """Shortlink lookup by name generates SQLAlchemy expressions."""
    # Equality and container expressions work
    expr = models.shortlink.Shortlink.name == 'example'
    assert expr is not None
    expr = models.shortlink.Shortlink.name.in_(['example', 'example_org'])
    assert expr is not None
    # Inequality expression is not supported, nor is anything else
    with pytest.raises(NotImplementedError):
        _expr = models.shortlink.Shortlink.name != 'example'  # noqa: F841


@pytest.mark.usefixtures('app_context')
def test_shortlink_lookup_multiple() -> None:
    """Shortlink allows lookup by name."""
    sl1 = models.shortlink.Shortlink.new('https://example.org', name='example')
    sl2 = models.shortlink.Shortlink.new('https://example.com', name='example_com')
    assert models.shortlink.Shortlink.query.filter_by(name='example').all() == [sl1]
    assert models.shortlink.Shortlink.query.filter_by(name='example_com').all() == [sl2]
    assert models.shortlink.Shortlink.query.filter_by(name='unknown').all() == []
    assert models.shortlink.Shortlink.query.filter(
        models.shortlink.Shortlink.name.in_(['example', 'example_com', 'unknown'])
    ).all() == [sl1, sl2]
