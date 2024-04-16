"""Jinja2 templates with type hints (in future: also type checking of the template)."""

from typing import Any, ClassVar, Literal

from flask import render_template
from typing_extensions import dataclass_transform

from coaster.utils import is_dunder

__all__ = ['JinjaTemplateBase', 'jinja_global_marker']


def jinja_global_marker(*, init: Literal[False] = False) -> Any:
    return ...


@dataclass_transform(
    eq_default=False, kw_only_default=True, field_specifiers=(jinja_global_marker,)
)
class JinjaTemplateBase:
    """Base class for a Jinja2 template with explicit context var types."""

    _template: ClassVar[str]

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)

    def __init_subclass__(cls, template: str) -> None:
        # Ensure cls doesn't have any default values. All template context must be
        # passed to `__init__` explicitly
        for attr, value in cls.__dict__.items():
            if not is_dunder(attr):
                if value is not ...:
                    raise TypeError(
                        "Template context variable cannot have a default value:"
                        f" {attr} = {value!r}"
                    )
        if template:
            cls._template = template
        super().__init_subclass__()

    def __call__(self) -> str:
        """Render template with context vars."""
        return render_template(self._template, **self.__dict__)
