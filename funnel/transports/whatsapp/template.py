"""WhatsApp template validator."""

from __future__ import annotations


class WhatsappTemplate:
    """Whatsapp template formatter."""

    registered_template_name = None
    registered_template_language_code = None
    registered_template = None
    template = None


class OTPTemplate(WhatsappTemplate):
    """OTP template formatter."""

    registered_template_name = "otp2"
    registered_template_language_code = "en"
    # Registered template for reference
    registered_template = """

    OTP is *{{1}}* for Hasgeek.

    If you did not request this, report misuse at https://has.gy/not-my-otp
"""
    template = {
        'name': registered_template_name,
        'language': {
            'code': registered_template_language_code,
        },
        'components': [
            {
                'type': 'body',
                "parameters": [
                    {
                        "type": "text",
                    },
                ],
            }
        ],
    }
    otp: str

    def __init__(self, otp: str = ''):
        self.otp = otp
        self.template['components'][0]['parameters'][0]['text'] = otp
