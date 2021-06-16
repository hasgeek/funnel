"""Test SMS templates."""

from flask import Flask

import pytest

from funnel.transports.sms import (
    MessageTemplate,
    OneLineTemplate,
    SmsTemplate,
    TwoLineTemplate,
    WebOtpTemplate,
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SMS_DLT_ENTITY_ID'] = 'dlt_entity_id'
    app.config['SMS_DLT_TEMPLATE_IDS'] = {}
    return app


class MyMessage(SmsTemplate):
    registered_template = "Insert {#var#} here"
    template = "Insert {var} here"


def test_base_length():
    """SmsTemplate.base_length returns number of base chars in a template."""
    assert SmsTemplate.base_length('123{var1}456{var2}789') == 9
    assert SmsTemplate.base_length('{var1}123456{var2}789') == 9
    assert SmsTemplate.base_length('{var1}123456789{var2}') == 9
    assert SmsTemplate.base_length('{var1}123456789') == 9
    assert SmsTemplate.base_length('123456789{var2}') == 9
    assert SmsTemplate.base_length('123456789') == 9


def test_validate_registered_template():
    """Test DLT registered template validator."""
    with pytest.raises(ValueError) as exc:

        class TemplateTooLong(SmsTemplate):
            registered_template = template = 'a' * 2001

    assert (
        str(exc.value)
        == "Registered template must be within 2000 chars (currently 2001 chars)"
    )

    with pytest.raises(ValueError) as exc:

        class TemplateVarSpaceWrong(SmsTemplate):
            registered_template = '{# var #}'
            template = '{var}'

    assert str(exc.value) == "Registered template must use {#var#}, not {# var #}"

    with pytest.raises(ValueError) as exc:

        class TemplateVarCaseWrong(SmsTemplate):
            registered_template = '{#VAR#}'
            template = '{var}'

    assert str(exc.value) == "Registered template must use {#var#}, not {#VAR#}"


def test_validate_template():
    """Test Python template validator."""
    with pytest.raises(ValueError) as exc:

        class TemplatSpaceMismatch(SmsTemplate):
            registered_template = '{#var#} '  # extra space
            template = '{var}'  # no space

    assert "template does not match" in str(exc.value)

    with pytest.raises(ValueError) as exc:

        class TemplateCaseMismatch(SmsTemplate):
            registered_template = 'I{#var#} '  # uppercase
            template = 'i{var}'  # lowercase

    assert "template does not match" in str(exc.value)

    with pytest.raises(ValueError) as exc:

        class TemplateVarReserved(SmsTemplate):
            registered_template = "{#var#}"
            template = "{text}"

    assert "Template keyword 'text' in TemplateVarReserved is reserved" in str(
        exc.value
    )


def test_validate_no_entity_template_id():
    """Entity id and template id must not appear in the class definition."""
    with pytest.raises(TypeError):

        class TemplateHasEntityid(SmsTemplate):
            registered_entityid = '12345'

    with pytest.raises(TypeError):

        class TemplateHasTemplateid(SmsTemplate):
            registered_templateid = '12345'


def test_subclass_config(app):
    class MySubMessage(MyMessage):
        pass

    assert SmsTemplate.registered_templateid is None
    assert MyMessage.registered_templateid is None
    assert MySubMessage.registered_templateid is None
    SmsTemplate.init_subclass_config(app, {'my_message': '12345'})
    assert SmsTemplate.registered_templateid is None
    assert MyMessage.registered_templateid == '12345'
    assert MySubMessage.registered_templateid == '12345'

    SmsTemplate.init_subclass_config(
        app, {'my_message': '67890', 'my_sub_message': 'qwerty'}
    )
    assert SmsTemplate.registered_templateid is None
    assert MyMessage.registered_templateid == '67890'
    assert MySubMessage.registered_templateid == 'qwerty'


def test_init_app(app):
    assert SmsTemplate.registered_entityid is None
    assert MyMessage.registered_entityid is None
    SmsTemplate.init_app(app)
    assert SmsTemplate.registered_entityid == 'dlt_entity_id'
    assert MyMessage.registered_entityid == 'dlt_entity_id'


def test_inline_use():
    assert str(MyMessage(var="sample1")) == "Insert sample1 here"
    assert MyMessage(var="sample2").text == "Insert sample2 here"


def test_object_use():
    msg = MyMessage()
    msg.var = "sample1"
    assert msg.var == "sample1"
    assert str(msg) == "Insert sample1 here"
    msg.var = "sample2"
    assert msg.var == "sample2"
    assert msg.text == "Insert sample2 here"


def test_validate():
    assert MyMessage(var="sample").validate() is True
    assert MyMessage(var="sample" * 1000).validate() is False  # Too long
    # TODO: Find a test for formatted string not matching registered template.
    # This will likely only be relevant after {#var#} length validation is added


# --- Test the registered templates


def test_web_otp_template():
    assert str(
        WebOtpTemplate(otp='1234', helpline_text="call 12345", domain='example.com')
    ) == (
        'OTP is 1234 for Hasgeek.\n\n'
        'Not you? Block misuse: call 12345\n\n'
        '@example.com #1234'
    )


def test_one_line_template():
    # Regular use
    assert str(
        OneLineTemplate(
            text1='1234567890' * 2,
            url='https://example.com/',
            unsubscribe_url='https://unsubscribe.example/',
        )
    ) == (
        '12345678901234567890 https://example.com/\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    # Truncated for length
    msg = OneLineTemplate(
        text1='1234567890' * 10,
        url='https://example.com/',
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert str(msg) == (
        '1234567890123456789012345678901234567890123456789012345678901234567890'
        '12345678901234567890123456... https://example.com/\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    assert len(msg.text1) + 1 + len(msg.url) == 120


def test_two_line_template():
    # Regular use
    assert str(
        TwoLineTemplate(
            text1='1234567890' * 2,
            text2='abcdefghij' * 2,
            url='https://example.com/',
            unsubscribe_url='https://unsubscribe.example/',
        )
    ) == (
        '12345678901234567890\n\n'
        'abcdefghijabcdefghij https://example.com/\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    # Truncated for length
    msg = TwoLineTemplate(
        text1='1234567890' * 10,
        text2='abcdefghij' * 10,
        url='https://example.com/',
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert str(msg) == (
        '123456789012345678901234567890123456789012345678901234567...\n\n'
        'abcdefghijabcdefghijabcdefghijabcdef... https://example.com/\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    assert len(msg.text1) == 60
    assert len(msg.text2) + 1 + len(msg.url) == 60


def test_message_template():
    # Regular use
    assert (
        str(
            MessageTemplate(
                message='1234567890' * 2,
                unsubscribe_url='https://unsubscribe.example/',
            )
        )
        == ('12345678901234567890\n\n' 'https://unsubscribe.example/ to stop - Hasgeek')
    )
    # Truncated for length
    msg = MessageTemplate(
        message='1234567890' * 20,
        unsubscribe_url='https://unsubscribe.example/',
    )
    assert str(msg) == (
        '1234567890123456789012345678901234567890123456789012345678901234567890'
        '12345678901234567890123456789012345678901234567...\n\n'
        'https://unsubscribe.example/ to stop - Hasgeek'
    )
    assert len(msg.message) == 120
