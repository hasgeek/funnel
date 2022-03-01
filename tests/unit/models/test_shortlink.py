"""Test Shortlink model."""
# The example URLs used here are as per RFC 2606 and RFC 6761
# https://datatracker.ietf.org/doc/html/rfc2606#section-3
# https://datatracker.ietf.org/doc/html/rfc6761#section-6.5

from unittest.mock import patch

from furl import furl
import pytest

import funnel.models.shortlink as shortlink


class MockRandomBigint:
    """Mock for random_bigint that returns from a pre-determined sequence."""

    def __init__(self, sequence):
        self.sequence = sequence
        self.counter = 0

    def __call__(self, smaller: bool = False):
        value = self.sequence[self.counter % len(self.sequence)]
        self.counter += 1
        return value


def test_random_bigint():
    """Random numbers are within expected range (this test depends on luck)."""
    randset = set()
    for _loop in range(1000):
        num = shortlink.random_bigint()
        assert num != 0
        # Bigints are 64-bit (8 bytes). That gives us 63 bits + 1 bit for sign
        assert -(2**63) <= num <= 2**63 - 1
        randset.add(num)
    # Ignore up to 2 collisions
    assert 998 <= len(randset) <= 1000


def test_smaller_random_int():
    """Smaller random numbers are within expected range (this test depends on luck)."""
    randset = set()
    for _loop in range(1000):
        num = shortlink.random_bigint(True)
        # Smaller ids are 24-bit (3 bytes) and not signed, since they are significantly
        # within bigint sign bit range
        assert 0 < num <= 2**24 - 1
        randset.add(num)
    # Ignore up to 2 collisions
    assert 998 <= len(randset) <= 1000


def test_mock_random_bigint():
    """Test that MockRandomBigint works as expected."""
    prng_values = [43, 123, 5345, 123, 5435]
    mockfunc = MockRandomBigint(prng_values)

    extracted_values = [mockfunc() for _c in range(len(prng_values) * 2)]
    assert extracted_values == prng_values + prng_values

    with patch(
        'funnel.models.shortlink.random_bigint', wraps=MockRandomBigint(prng_values)
    ):
        extracted_values = [
            shortlink.random_bigint() for _c in range(len(prng_values) * 2)
        ]
        assert extracted_values == prng_values + prng_values


@pytest.mark.parametrize(
    ['lhs', 'rhs'],
    [
        ('https://example.com', 'example.com'),
        ('https://example.com/', 'https://example.com'),
    ],
)
def test_url_hash_is_normalized(lhs, rhs):
    """URL hash is normalized by default, and handles furl objects."""
    assert shortlink.url_blake2b160_hash(lhs) == shortlink.url_blake2b160_hash(rhs)
    assert shortlink.url_blake2b160_hash(furl(lhs)) == shortlink.url_blake2b160_hash(
        rhs
    )
    assert shortlink.url_blake2b160_hash(lhs) == shortlink.url_blake2b160_hash(
        furl(rhs)
    )


def test_url_hash_is_constant():
    """URL hashes are a guaranteed identical output (including in the future)."""
    # These values should never need revision.
    example_com = 'https://example.com/'
    example_com_hash = (
        b'\x97\xb9z\xc1\x7f\xbb~\x82\x06\x0c\xc9\xcf"\x97\xb2\x90\xeeT\x98\x96'
    )

    assert shortlink.url_blake2b160_hash(example_com) == example_com_hash
    assert shortlink.url_blake2b160_hash(furl(example_com)) == example_com_hash
    assert (
        shortlink.url_blake2b160_hash(example_com, normalize=False) == example_com_hash
    )
    assert (
        shortlink.url_blake2b160_hash(furl(example_com), normalize=False)
        == example_com_hash
    )


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


@pytest.mark.parametrize(['name', 'bigint'], name_bigint_mappings)
def test_bigint_to_name(name, bigint):
    """Bigints can be mapped to names."""
    assert shortlink.bigint_to_name(bigint) == name


@pytest.mark.parametrize(
    ['name', 'bigint'], name_bigint_mappings + uni_name_bigint_mappings
)
def test_name_to_bigint(name, bigint):
    """Names can be mapped to bigints."""
    # Works with `str`
    assert shortlink.name_to_bigint(name) == bigint
    # Works with `bytes`
    assert shortlink.name_to_bigint(name.encode()) == bigint


def test_name_to_bigint_data_type():
    """name_to_bigint is fussy about data type."""
    # Calling with something not str or bytes will raise an error
    with pytest.raises(TypeError):
        shortlink.name_to_bigint(12345)
    with pytest.raises(TypeError):
        shortlink.name_to_bigint(True)
    with pytest.raises(TypeError):
        shortlink.name_to_bigint(None)

    # Value is too long (length limit is 11)
    with pytest.raises(ValueError):
        shortlink.name_to_bigint('A' * 12)
    with pytest.raises(ValueError):
        shortlink.name_to_bigint('B' * 12)

    # Value contains invalid characters
    with pytest.raises(ValueError):
        shortlink.name_to_bigint('A/B')
    with pytest.raises(ValueError):
        shortlink.name_to_bigint('A@B')


def test_shortlink_id_equals_zero(db_session):
    """Shortlink cannot have an id of 0."""
    with pytest.raises(ValueError):
        shortlink.Shortlink(id=0)


def test_shortlink_url_is_normalized(db_session):
    """Shortlink URLs are normalized."""
    sl = shortlink.Shortlink(url='example.com')
    assert sl.url == 'https://example.com/'


def test_shortlink_without_id_has_empty_name(db_session):
    """Shortlink without an id has empty name."""
    sl = shortlink.Shortlink()
    assert sl.name == ''


def test_shortlink_with_small_id_has_short_name(db_session):
    """Shortlink with small id has a short name."""
    sl = shortlink.Shortlink(id=1)
    assert sl.name == 'AQ'


def test_shortlink_gets_id_from_name(db_session):
    """Shortlink with a name will get an id from the name."""
    sl = shortlink.Shortlink(name='AQ')
    assert sl.id == 1


def test_constructor_reuse_with_name(db_session):
    """Shortlink constructor with both `reuse` and `name` will fail."""
    with pytest.raises(TypeError):
        shortlink.Shortlink.new('https://example.com/', reuse=True, name='example')


def test_shortlink_constructor_with_reuse(db_session):
    """Shortlink constructor will return existing when asked to reuse."""
    sl1 = shortlink.Shortlink.new('example.com', reuse=True)
    sl2 = shortlink.Shortlink.new('example.org', reuse=True)
    assert sl1 != sl2

    # db_session.add(...) is not required because Shortlink already adds to session
    # db_session.commit() is not required for this test because Shortlink does not
    # disable autoflush
    sl3 = shortlink.Shortlink.new('example.com/', reuse=True)
    assert sl3 == sl1
    assert sl3.id == sl1.id
    assert sl3 != sl2
    assert sl3.id != sl2.id


@pytest.mark.parametrize(
    ['longid', 'match'], [(146727516324, False), (-1, False), (4235324, True)]
)
def test_shortlink_reuse_with_shorter(db_session, longid, match):
    """Shortlink reuse with shorter will avoid longer ids."""
    sl1 = shortlink.Shortlink(id=longid, url='example.com')
    db_session.add(sl1)
    sl2 = shortlink.Shortlink.new(url='example.com', shorter=True, reuse=True)
    assert (sl2.id == sl1.id) is match


@pytest.mark.filterwarnings('ignore:New instance')
def test_shortlink_constructor_with_name(db_session):
    """Shortlink constructor will accept a name."""
    sl1 = shortlink.Shortlink.new('example.com', name='example')
    assert sl1.name == 'example'

    with pytest.raises(ValueError):
        # This will cause an SAWarning before it raises ValueError. We ignore it
        # using the filterwarnings decorator:
        #     SAWarning: New instance <Shortlink at 0x...> with identity key
        #     (<class 'funnel.models.shortlink.Shortlink'>, (141113946412667,), None)
        #     conflicts with persistent instance <Shortlink at 0x...>
        shortlink.Shortlink.new('example.org', name='example')

    # The db transaction remains open after an error, allowing additional inserts
    sl2 = shortlink.Shortlink.new('example.org', name='example_org')
    sl3 = shortlink.Shortlink.new('example.org', reuse=True)
    assert sl3 == sl2
    assert sl3.id == sl2.id
    assert sl3.name == sl2.name == 'example_org'


@pytest.mark.filterwarnings('ignore:New instance')
def test_shortlink_constructor_handle_collisions(db_session):
    """Shortlink constructor will handle random id collisions gracefully."""
    prngids = MockRandomBigint([42, 42, 128, 128, 128, 384])
    with patch(
        'funnel.models.shortlink.random_bigint',
        wraps=prngids,
    ) as mockid:
        sl1 = shortlink.Shortlink.new('example.org')
        assert sl1.id == 42
        assert mockid.call_count == 1
        mockid.assert_called_with(False)
        mockid.reset_mock()

        sl2 = shortlink.Shortlink.new('example.com', shorter=False)
        assert sl2.id == 128
        assert mockid.call_count == 2  # Returned 42 the first time, 128 second time
        mockid.assert_called_with(False)
        mockid.reset_mock()

        sl3 = shortlink.Shortlink.new('example.net', shorter=True)
        assert sl3.id == 384
        assert mockid.call_count == 3  # Returned 128, 128, 384
        mockid.assert_called_with(True)  # Called with smaller=True
        mockid.reset_mock()

        sl4 = shortlink.Shortlink.new('example.org', name='example')
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


def test_shortlink_new_profanity_filter(db_session):
    """Generated shortlink ids are tested against a profanity filter."""
    prngids = MockRandomBigint(
        [
            shortlink.name_to_bigint('works'),
            shortlink.name_to_bigint('xxx'),
            shortlink.name_to_bigint('sexy'),
            shortlink.name_to_bigint('okay'),
        ]
    )
    with patch(
        'funnel.models.shortlink.random_bigint',
        wraps=prngids,
    ) as mockid:
        sl1 = shortlink.Shortlink.new('example.org')
        assert sl1.name == 'works'
        assert mockid.call_count == 1
        mockid.reset_mock()

        sl2 = shortlink.Shortlink.new('example.com')
        assert sl2.name == 'okay'
        assert mockid.call_count == 3  # Middle mocks got dropped by profanity filter
        mockid.reset_mock()


def test_shortlink_name_available(db_session):
    """Shortlink has a `name_available` classmethod to test for availability."""
    assert shortlink.Shortlink.name_available('example') is True
    shortlink.Shortlink.new('example.org', name='example')
    assert shortlink.Shortlink.name_available('example') is False
    assert shortlink.Shortlink.name_available('example_org') is True
    assert shortlink.Shortlink.name_available('example_too_long') is False


def test_shortlink_get(db_session):
    """Shortlink has a `get` classmethod."""
    assert shortlink.Shortlink.get('example') is None
    shortlink.Shortlink.new('example.org', name='example')
    sl = shortlink.Shortlink.get('example')
    assert sl is not None
    assert sl.name == 'example'
    assert shortlink.Shortlink.get('example_org') is None
    assert shortlink.Shortlink.get('example_too_long') is None

    sl.enabled = False
    assert shortlink.Shortlink.get('example') is None
    assert shortlink.Shortlink.get('example', True) == sl


def test_shortlink_comparator():
    """Shortlink lookup by name generates SQLAlchemy expressions."""
    # Equality and container expressions work
    expr = shortlink.Shortlink.name == 'example'
    assert expr is not None
    expr = shortlink.Shortlink.name.in_(['example', 'example_org'])
    assert expr is not None
    # Inequality expression is not supported, nor is anything else
    with pytest.raises(NotImplementedError):
        expr = shortlink.Shortlink.name != 'example'
        assert expr is not None  # This line won't be reached


def test_shortlink_lookup_multiple():
    """Shortlink allows lookup by name."""
    sl1 = shortlink.Shortlink.new('example.org', name='example')
    sl2 = shortlink.Shortlink.new('example.com', name='example_com')
    assert shortlink.Shortlink.query.filter_by(name='example').all() == [sl1]
    assert shortlink.Shortlink.query.filter_by(name='example_com').all() == [sl2]
    assert shortlink.Shortlink.query.filter_by(name='unknown').all() == []
    assert shortlink.Shortlink.query.filter(
        shortlink.Shortlink.name.in_(['example', 'example_com', 'unknown'])
    ).all() == [sl1, sl2]
