from funnel.models.helpers import valid_name, valid_username


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
    """
    Usernames contain letters, numbers and non-terminal hyphens.
    """
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
