"""Non-database model for registered SMS templates in India."""

from __future__ import annotations

import re
from enum import Enum
from re import Pattern
from string import Formatter
from types import SimpleNamespace
from typing import Any, ClassVar, cast

from flask import Flask

__all__ = [
    'DLT_VAR_MAX_LENGTH',
    'SmsPriority',
    'SmsTemplate',
    'WebOtpTemplate',
]

# MARK: Registered template processor --------------------------------------------------

# This list of chars is from https://archive.is/XJJHV via Airtel.
# Not currently used because the documentation is unclear on how to use it
dlt_exempted_chars_re = re.compile('[~`!@#$%^&*()_+={}\\[\\]|\\\\/:;"\'<>,.?-]')

_var_variant_re = re.compile(r'{\s*#\s*var\s*#\s*}', re.IGNORECASE)
_var_repeat_re = re.compile('({#.*?#})+')

#: The maximum number of characters that can appear under one {#var#}
#: Unclear in documentation: are exempted characters excluded from this length limit?
DLT_VAR_MAX_LENGTH = 30


class SmsPriority(Enum):
    URGENT = 1  # For OTPs and time-sensitive messages
    IMPORTANT = 2  # For messaging any time of the day, including during DND hours
    OPTIONAL = 3  # Okay to drop this message if not sent at a good time
    NORMAL = 4  # Everything else, will not be sent during DND hours, TODO requeue


class SmsTemplate:
    r"""
    SMS template validator and formatter, for DLT registered SMS in India.

    To use, create a subclass with the registered and Python templates, and optionally
    override :meth:process to process variables. The registered and Python templates are
    validated to match each other when the class is created::

        class MyTemplate(SmsTemplate):
            registered_template = 'Insert {#var#} here'
            template = "Insert {var} here"
            plaintext_template = "Simplified template also embedding {var}"

            var: str  # Declare variable type like this

            # Optional truncator
            def truncate(self) -> None:
                self.var = self.var[:10]

    The template can be used in a single pass::

        >>> str(MyTemplate(var="sample"))
        'Insert sample here'

    Or it can be constructed one variable at a time::

        >>> msg = MyTemplate()
        >>> msg.var = "sample"
        >>> msg.var
        'sample'
        >>> msg.text
        'Insert sample here'

    Format fields for the Python template can be set and accessed directly from the
    class instance. The formatted string is available as :property:`text`, or by casting
    the template object to a string.

    Templates can be split into a base "registered template" class and an "application
    template" subclass. This pattern allows for multiple application templates riding
    atop a single generic registered template, and also for localization. The text in
    the registered template cannot be localized.

    Since registered templates may require mandatory boilerplate, an optional plain
    template can be provided to allow use outside an SMS context, such as text messages
    to other messengers. This template is formatted before truncation::

        class RegisteredTemplate(SmsTemplate):
            registered_template = '{#var#}{#var#}{#var#}{#var#}\n\n{#var#} to stop'
            template = '{content}\n\n{unsubscribe_url} to stop'
            plaintext_template = '{content}'

            @property
            def unsubscribe_url(self):
                return 'https://unsubscribe.example/'

            def available_var_len(self):
                '''Return available length for variables.'''
                return self.template_var_len - len(self.unsubscribe_url)


        class MessageTemplate(RegisteredTemplate):
            @property
            def content(self):
                return _("You have a message from {user}").format(user=self.user)

            def truncate(self):
                '''Truncate variables to fit available length.'''
                alen = self.available_var_len()
                if len(self.user) > alen:
                    self.user = self.user[: alen - 1] + '…'


        >>> str(MessageTemplate("Rincewind"))
        'You have a message from Rincewind\n\nhttps://unsubscribe.example/ to stop'
        >>> MessageTemplate("Rincewind").plaintext
        'You have a message from Rincewind'
    """

    #: Maximum length for a single variable as per the spec
    var_max_length: ClassVar[int] = DLT_VAR_MAX_LENGTH
    #: Registered entity id
    registered_entityid: ClassVar[str | None] = None
    #: Registered template id
    registered_templateid: ClassVar[str | None] = None
    #: Registered template, using `{#var#}` where variables should appear
    registered_template: ClassVar[str] = ""
    #: Python template, with formatting variables as {var}
    template: ClassVar[str] = ""
    #: Optional plaintext Python template without validation against registered template
    plaintext_template: ClassVar[str] = ""
    #: Message delivery priority
    message_priority: ClassVar[SmsPriority] = SmsPriority.NORMAL

    #: Autogenerated regex version of registered template, will be updated in subclasses
    registered_template_re: ClassVar[Pattern] = re.compile('')
    #: Autogenerated count of static characters in registered template
    registered_template_static_len: ClassVar[int] = 0  # Will be replaced in subclasses
    #: Autogenerated count of characters available in variables
    registered_template_var_len: ClassVar[int] = 0  # Will be replaced in subclasses

    # Type hints for mypy. These attributes are set in __init__
    _text: str | None
    _plaintext: str | None
    _format_kwargs: dict[str, Any]
    template_static_len: ClassVar[int]
    template_var_len: int

    def __init__(self, **kwargs: Any) -> None:
        """Initialize template with variables."""
        object.__setattr__(self, '_text', None)
        object.__setattr__(self, '_plaintext', None)
        object.__setattr__(self, '_format_kwargs', {})
        # Calculate the formatted length before variables are inserted. Subclasses
        # can use this to truncate variables to fit. We do this in the instance and not
        # the class so that subclasses can support localization of static text by
        # defining those "variables" as properties on the class. Since no variables
        # have been stored yet, this call to vformat will invoke self.__getitem__, which
        # will return '' for unknown keys.
        object.__setattr__(
            self,
            'template_static_len',
            # vformat only needs __getitem__, so ignore mypy's warning about arg type.
            # The expected type is Mapping[str, Any]
            len(
                Formatter().vformat(  # type: ignore[call-overload]
                    self.template, (), self
                )
            ),
        )
        # Now set the length available for variables by comparing with the registered
        # template. The Python template may have static text where the registered
        # template has a variable, so we get the difference. This value can be used by
        # :meth:`process` to truncate variables to fit.
        object.__setattr__(
            self,
            'template_var_len',
            self.registered_template_var_len
            + self.registered_template_static_len
            - self.template_static_len,
        )
        # Next, store real format field values
        for arg, value in kwargs.items():
            # Use setattr so subclasses can define special behaviour
            setattr(self, arg, value)

    def available_var_len(self) -> int:
        """
        Available length for variable characters, to truncate as necessary.

        Subclasses may override this to subtract variables that cannot be truncated.
        """
        return self.template_var_len

    def truncate(self) -> None:
        """Truncate variables (subclasses may override as necessary)."""

    def format(self) -> None:
        """Format template with variables."""
        # Format plaintext before truncation
        object.__setattr__(
            self,
            '_plaintext',
            # vformat only needs __getitem__, so ignore mypy's warning about arg type.
            # The expected type is Mapping[str, Any]
            (
                Formatter().vformat(  # type: ignore[call-overload]
                    self.plaintext_template, (), self
                )
                if self.plaintext_template
                else ''
            ),
        )
        self.truncate()
        object.__setattr__(
            self,
            '_text',
            # vformat only needs __getitem__, so ignore mypy's warning about arg type.
            # The expected type is Mapping[str, Any]
            Formatter().vformat(self.template, (), self),  # type: ignore[call-overload]
        )

    @property
    def text(self) -> str:
        """Format template into text."""
        if self._text is None:
            self.format()
        # self.format() ensures `_text` is str, but mypy doesn't know
        return cast(str, self._text)

    @property
    def plaintext(self) -> str:
        """Format plaintext template into text."""
        if self._text is None:
            self.format()
        # self.format() ensures `_plaintext` is str, but mypy doesn't know
        return cast(str, self._plaintext)

    def __str__(self) -> str:
        """Return SMS text as string."""
        return self.text

    def __repr__(self) -> str:
        """Return a representation of self."""
        return f'<{self.__class__.__name__} {self.text!r}>'

    def __getattr__(self, attr: str) -> Any:
        """Get a format variable."""
        try:
            return self._format_kwargs[attr]
        except KeyError as exc:
            raise AttributeError(
                attr, name=attr, obj=SimpleNamespace(**self._format_kwargs)
            ) from exc

    def __getitem__(self, key: str) -> Any:
        """Get a format variable via dictionary access, defaulting to ''."""
        return getattr(self, key, '')

    def __setattr__(self, attr: str, value: Any) -> None:
        """Set a format variable."""
        clsattr = getattr(self.__class__, attr, None)
        if clsattr is not None:
            # If this attr is from the class, handover processing to object
            object.__setattr__(self, attr, value)
        else:
            # If not, assume template variable
            self._format_kwargs[attr] = value
            object.__setattr__(self, '_text', None)
            # We do not reset `_plaintext` here as the `plaintext` property checks only
            # `_text`. This is because `format()` calls `truncate()`, which may update a
            # variable, which will call `__setattr__`. At this point `_plaintext` has
            # already been set by `.format()` and should not be reset.

    def vars(self) -> dict[str, Any]:
        """Return a dictionary of variables in the template."""
        return dict(self._format_kwargs)

    @classmethod
    def validate_registered_template(cls) -> None:
        """Validate the Registered template as per documented rules."""
        # 1. Confirm the template is within 2000 characters
        if len(cls.registered_template) > 2000:
            raise ValueError(
                f"Registered template must be within 2000 chars"
                f" (currently {len(cls.registered_template)} chars)"
            )

        # 2. Check for incorrect representations of `{#var#}` (spaces, casing)
        for varmatch in _var_variant_re.findall(cls.registered_template):
            if varmatch != '{#var#}':
                raise ValueError(
                    f"Registered template must use {{#var#}}, not {varmatch}"
                )
        cls.registered_template_static_len = len(
            _var_repeat_re.sub('', cls.registered_template)
        )
        cls.registered_template_var_len = (
            cls.registered_template.count('{#var#}') * DLT_VAR_MAX_LENGTH
        )

        # 3. Create a compiled regex for the registered template that replaces
        #    repetitions of '{#var#}' with a '.*?'. This is used to validate the Python
        #    template. Registered templates need to have repetitions of '{#var#}' to
        #    increase the number of characters allowed (30 per instance), but as per
        #    current understanding of the spec, the length limit is shared across the
        #    template and not per var. Therefore we use '.*?' instead of '.{0,30}?' and
        #    leave the length validation and truncation to :meth:`process`
        cls.registered_template_re = re.compile(
            re.escape(_var_repeat_re.sub('{#var#}', cls.registered_template)).replace(
                # `re.escape` will convert '{#var#}' to r'\{\#var\#\}'
                r'\{\#var\#\}',
                '.*?',
            ),
            re.DOTALL,  # Let .*? include newlines, as that is valid in variables
        )

    @classmethod
    def validate_template(cls) -> None:
        """Validate that the Python template matches the registered template."""
        # 1. Confirm template does not use format fields that conflict with class
        #    members, or are positional instead of keyword.
        for _literal_text, field_name, _format_spec, _conversion in Formatter().parse(
            cls.template
        ):
            if field_name is not None:
                if field_name == '' or field_name.isdigit():
                    raise ValueError("Templates cannot have positional fields")
                if (
                    field_name in ('_text', '_plaintext', '_format_kwargs')
                    or field_name in SmsTemplate.__dict__
                ):
                    raise ValueError(
                        f"Template field '{field_name}' in {cls.__name__} is reserved"
                        f" and cannot be used"
                    )

        # 2. Match regex against Python template
        if cls.registered_template_re.fullmatch(cls.template) is None:
            raise ValueError(
                f"Python template does not match registered template in {cls.__name__}"
                f"\nRegistered template: {cls.registered_template!r}"
                f"\nAs regex: {cls.registered_template_re!r}"
                f"\nTemplate: {cls.template!r}"
            )

    @classmethod
    def validate_no_entity_template_id(cls) -> None:
        """Validate that confidential information is not present in the class spec."""
        if (
            'registered_entityid' in cls.__dict__
            or 'registered_templateid' in cls.__dict__
        ):
            raise TypeError(
                f"Registered entity id and template id are not public information and"
                f" must be in config. Use init_app to load config (class has:"
                f" registered_entityid={cls.registered_entityid},"
                f" registered_templateid={cls.registered_templateid})"
            )

    def __init_subclass__(cls) -> None:
        """Validate templates in subclasses."""
        super().__init_subclass__()
        cls.validate_no_entity_template_id()
        cls.validate_registered_template()
        cls.validate_template()

    @classmethod
    def init_subclass_config(cls, app: Flask, config: dict[str, str]) -> None:
        """Recursive init for setting template ids in subclasses."""
        for subcls in cls.__subclasses__():
            subcls_config_name = ''.join(
                ['_' + c.lower() if c.isupper() else c for c in subcls.__name__]
            ).lstrip('_')
            templateid = config.get(subcls_config_name)
            if not templateid:
                # No template id provided. If class already has a templateid from
                # parent class, let this pass. If not, raise a warning.
                if not cls.registered_templateid:
                    app.logger.warning(
                        "App config is missing SMS_DLT_TEMPLATE_IDS['%s']"
                        " for template %s",
                        subcls_config_name,
                        subcls.__name__,
                    )
            else:
                # Set the template id from config
                subcls.registered_templateid = templateid
            # Recursively configure subclasses of this subclass
            subcls.init_subclass_config(app, config)

    @classmethod
    def init_app(cls, app: Flask) -> None:
        """Set Registered entity id and template ids from app config."""
        cls.registered_entityid = app.config.get('SMS_DLT_ENTITY_ID')
        cls.init_subclass_config(app, app.config.get('SMS_DLT_TEMPLATE_IDS', {}))


# MARK: Registered templates used by this app ------------------------------------------


class WebOtpTemplate(SmsTemplate):
    """Template for Web OTPs."""

    registered_template = (
        'OTP is {#var#} for Hasgeek. If you did not request this, report misuse at'
        ' https://hasgeek.com/account/not-my-otp\n\n@hasgeek.com #{#var#}'
    )
    template = (
        "OTP is {otp} for Hasgeek. If you did not request this, report misuse at"
        " https://hasgeek.com/account/not-my-otp\n\n@hasgeek.com #{otp}"
    )
    plaintext_template = (
        "OTP is {otp} for Hasgeek. If you did not request this, report misuse at"
        " https://hasgeek.com/account/not-my-otp\n\n@hasgeek.com #{otp}"
    )
    message_priority = SmsPriority.URGENT
