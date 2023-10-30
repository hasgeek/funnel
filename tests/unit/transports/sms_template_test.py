"""Test SMS templates."""
# pylint: disable=possibly-unused-variable,redefined-outer-name

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Flask

from funnel.transports import sms


@pytest.fixture()
def app() -> Flask:
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SMS_DLT_ENTITY_ID'] = 'dlt_entity_id'
    test_app.config['SMS_DLT_TEMPLATE_IDS'] = {}
    return test_app


@pytest.fixture(scope='session')
def msgt() -> SimpleNamespace:
    class MyMessage(sms.SmsTemplate):
        registered_template = 'Insert {#var#} here'
        template = "Insert {var} here"
        plaintext_template = "{var} here"

    return SimpleNamespace(**locals())


def test_validate_registered_template() -> None:
    """Test DLT registered template validator."""
    # pylint: disable=unused-variable
    with pytest.raises(
        ValueError,
        match='Registered template must be within 2000 chars',
    ):

        class TemplateTooLong(sms.SmsTemplate):
            registered_template = template = 'a' * 2001

    with pytest.raises(
        ValueError, match='Registered template must use {#var#}, not {# var #}'
    ):

        class TemplateVarSpaceWrong(sms.SmsTemplate):
            registered_template = '{# var #}'
            template = '{var}'

    with pytest.raises(
        ValueError, match='Registered template must use {#var#}, not {#VAR#}'
    ):

        class TemplateVarCaseWrong(sms.SmsTemplate):
            registered_template = '{#VAR#}'
            template = '{var}'


def test_template_lengths() -> None:
    """Static and variable character lengths are calculated automatically."""

    class OneVarTemplate(sms.SmsTemplate):
        registered_template = 'This has one {#var#}'
        template = "This has one {var}"

    class TwoVarTemplate(sms.SmsTemplate):
        registered_template = 'This has two {#var#}{#var#}'
        template = "This has two {var}"

    class ThreeVarTemplate(sms.SmsTemplate):
        registered_template = '{#var#} this has three {#var#}{#var#}'
        template = "{var} this has three {var}"

    class MismatchTemplate(sms.SmsTemplate):
        registered_template = 'This has two {#var#}{#var#}'
        template = "This has two  {var}"  # Extra space here

    assert OneVarTemplate.registered_template_static_len == len("This has one ") == 13
    assert OneVarTemplate.registered_template_var_len == 30
    assert TwoVarTemplate.registered_template_static_len == len("This has two ") == 13
    assert TwoVarTemplate.registered_template_var_len == 60
    assert (
        ThreeVarTemplate.registered_template_static_len == len(" this has three ") == 16
    )
    assert ThreeVarTemplate.registered_template_var_len == 90
    assert MismatchTemplate.registered_template_static_len == len("This has two ") == 13
    assert MismatchTemplate.registered_template_var_len == 60

    # Lengths for Python templates are available after instantiation:
    t1 = OneVarTemplate()
    t2 = TwoVarTemplate()
    t3 = ThreeVarTemplate()
    tm = MismatchTemplate()

    # These values match the registered template
    assert t1.template_static_len == 13
    assert t1.template_var_len == 30
    assert t2.template_static_len == 13
    assert t2.template_var_len == 60
    assert t3.template_static_len == 16
    assert t3.template_var_len == 90

    # The mismatched template will be off by one because the Python template has a space
    # that is considered part of the variable in the registered template
    assert tm.template_static_len == 14
    assert tm.template_var_len == 59

    # These values are also available through the overrideable available_var_len method:
    assert t1.available_var_len() == 30
    assert t2.available_var_len() == 60
    assert t3.available_var_len() == 90
    assert tm.available_var_len() == 59

    # These values don't change even if a var is provided to the constructor:
    t1 = OneVarTemplate(var='example')
    t2 = TwoVarTemplate(var='example')
    t3 = ThreeVarTemplate(var='example')
    tm = MismatchTemplate(var='example')

    assert t1.template_static_len == 13
    assert t1.template_var_len == 30
    assert t2.template_static_len == 13
    assert t2.template_var_len == 60
    assert t3.template_static_len == 16
    assert t3.template_var_len == 90
    assert tm.template_static_len == 14
    assert tm.template_var_len == 59
    assert t1.available_var_len() == 30
    assert t2.available_var_len() == 60
    assert t3.available_var_len() == 90
    assert tm.available_var_len() == 59


def test_validate_template() -> None:
    """Test Python template validator."""
    # pylint: disable=unused-variable
    with pytest.raises(
        ValueError, match='Python template does not match registered template'
    ):

        class TemplatSpaceMismatch(sms.SmsTemplate):
            registered_template = '{#var#} '  # extra space
            template = '{var}'  # no space

    with pytest.raises(
        ValueError, match='Python template does not match registered template'
    ):

        class TemplateCaseMismatch(sms.SmsTemplate):
            registered_template = 'I{#var#} '  # uppercase
            template = 'i{var}'  # lowercase

    with pytest.raises(
        ValueError, match="Template field 'text' in TemplateVarReserved is reserved"
    ):

        class TemplateVarReserved(sms.SmsTemplate):
            registered_template = '{#var#}'
            template = "{text}"

    with pytest.raises(ValueError, match='Templates cannot have positional fields'):

        class TemplateVarPositional(sms.SmsTemplate):
            registered_template = '{#var#}'
            template = "{}"


def test_validate_no_entity_template_id() -> None:
    """Entity id and template id must not appear in the class definition."""
    # pylint: disable=unused-variable
    with pytest.raises(TypeError):

        class TemplateHasEntityid(sms.SmsTemplate):
            registered_entityid = '12345'

    with pytest.raises(TypeError):

        class TemplateHasTemplateid(sms.SmsTemplate):
            registered_templateid = '12345'


def test_subclass_config(app: Flask, msgt: SimpleNamespace) -> None:
    class MySubMessage(msgt.MyMessage):  # type: ignore[name-defined]
        pass

    assert sms.SmsTemplate.registered_templateid is None
    assert msgt.MyMessage.registered_templateid is None
    assert MySubMessage.registered_templateid is None
    sms.SmsTemplate.init_subclass_config(app, {'my_message': '12345'})
    assert sms.SmsTemplate.registered_templateid is None
    assert msgt.MyMessage.registered_templateid == '12345'
    assert MySubMessage.registered_templateid == '12345'

    sms.SmsTemplate.init_subclass_config(
        app, {'my_message': '67890', 'my_sub_message': 'qwerty'}
    )
    assert sms.SmsTemplate.registered_templateid is None
    assert msgt.MyMessage.registered_templateid == '67890'
    assert MySubMessage.registered_templateid == 'qwerty'


@patch.object(sms.SmsTemplate, 'registered_entityid', None)
def test_init_app(app: Flask, msgt: SimpleNamespace) -> None:
    assert sms.SmsTemplate.registered_entityid is None
    assert msgt.MyMessage.registered_entityid is None
    sms.SmsTemplate.init_app(app)
    assert sms.SmsTemplate.registered_entityid == 'dlt_entity_id'
    assert msgt.MyMessage.registered_entityid == 'dlt_entity_id'


def test_inline_use(msgt: SimpleNamespace) -> None:
    assert str(msgt.MyMessage(var="sample1")) == "Insert sample1 here"
    assert msgt.MyMessage(var="sample2").text == "Insert sample2 here"
    assert msgt.MyMessage(var="sample3").plaintext == "sample3 here"


def test_object_use(msgt: SimpleNamespace) -> None:
    # pylint: disable=attribute-defined-outside-init
    msg = msgt.MyMessage()
    msg.var = "sample1"
    assert msg.var == "sample1"
    assert str(msg) == "Insert sample1 here"
    msg.var = "sample2"
    assert msg.var == "sample2"
    assert msg.text == "Insert sample2 here"
    msg.var = "sample3"
    assert msg.var == "sample3"
    assert msg.plaintext == "sample3 here"


# --- Test the registered templates


def test_web_otp_template() -> None:
    t = sms.WebOtpTemplate(otp='1234')
    assert str(t) == (
        'OTP is 1234 for Hasgeek. If you did not request this, report misuse at '
        'https://has.gy/not-my-otp\n\n@hasgeek.com #1234'
    )


def test_one_line_template() -> None:
    # Regular use
    t = sms.OneLineTemplate(
        text1='123456789_' * 2,
        url='https://example.com/',
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert t.template_var_len == 148
    assert t.available_var_len() == 100  # Less two provided URLs
    assert str(t) == (
        '123456789_123456789_ https://example.com/\n\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    # Truncated for length
    msg = sms.OneLineTemplate(
        text1='123456789_' * 20,
        url='https://example.com/',
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert str(msg) == (
        '123456789_123456789_123456789_123456789_123456789_123456789_123456789_'
        '123456789_123456789_123456789… https://example.com/\n\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    assert len(msg.text1) == 100  # Including the added ellipsis


def test_two_line_template() -> None:
    # Regular use
    t = sms.TwoLineTemplate(
        text1='123456789_' * 2,
        text2='abcdefghi_' * 2,
        url='https://example.com/',
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert t.template_var_len == 148
    assert t.available_var_len() == 100  # Less two provided URLs
    assert str(t) == (
        '123456789_123456789_\n\n'
        'abcdefghi_abcdefghi_ https://example.com/\n\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    # Truncated for length
    msg = sms.TwoLineTemplate(
        text1='123456789_' * 20,
        text2='abcdefghi_' * 20,
        url='https://example.com/',
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert str(msg) == (
        '123456789_123456789_123456789_12…\n\n'
        'abcdefghi_abcdefghi_abcdefghi_abcdefghi_abcdefghi_abcdefghi_abcde…'
        ' https://example.com/\n\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    assert len(msg.text1) == 33
    assert len(msg.text2) == 66


def test_message_template() -> None:
    # Regular use
    t = sms.MessageTemplate(
        message='123456789_' * 2,
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert t.template_var_len == 149
    assert t.available_var_len() == 121  # Less one provided URL (for unsubscribe)
    assert str(t) == (
        '123456789_123456789_\n\n\nhttps://unsubscribe.example/ to stop - Hasgeek'
    )
    # Truncated for length
    msg = sms.MessageTemplate(
        message='123456789_' * 20,
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert len(msg.message) == 200
    assert str(msg) == (
        '123456789_123456789_123456789_123456789_123456789_123456789_123456789_'
        '123456789_123456789_123456789_123456789_123456789_…\n\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    assert len(msg.message) == 121

    # However, the plaintext template is formatted before truncation and will not be
    # truncated
    assert msg.plaintext == (
        '123456789_123456789_123456789_123456789_123456789_123456789_123456789_'
        '123456789_123456789_123456789_123456789_123456789_123456789_123456789_'
        '123456789_123456789_123456789_123456789_123456789_123456789_'
    )
    assert len(msg.plaintext) == 200
