"""Jinja2 templates with type hints (in future: also type checking of the template)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, ClassVar, Literal, NamedTuple

from flask import current_app, render_template, stream_template
from jinja2 import Environment, Template
from jinja2.meta import find_referenced_templates
from jinja2.nodes import Template as TemplateNode
from typing_extensions import dataclass_transform

from coaster.utils import is_dunder

__all__ = ['JinjaTemplateBase', 'jinja_global_marker']

# MARK: Jinja helpers ------------------------------------------------------------------


class TemplateAst(NamedTuple):
    template: str
    ast: TemplateNode
    filename: str | None

    def __repr__(self) -> str:
        return f'TemplateAst({self.template!r}, ast, {self.filename!r})'


# MARK: Typed template dataclass -------------------------------------------------------


def jinja_global_marker(*, init: Literal[False] = False) -> Any:
    return ...


@dataclass_transform(
    eq_default=False, kw_only_default=True, field_specifiers=(jinja_global_marker,)
)
class JinjaTemplateBase:
    """Base class for a Jinja2 template with explicit context var types."""

    _template: ClassVar[str]

    def __init__(self, **context) -> None:
        self.__dict__.update(context)

    def __init_subclass__(cls, template: str | None) -> None:
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

    # Primary methods, only usable given an app context

    def render_template(self) -> str:
        """Render template with context vars."""
        return render_template(self._template, **self.__dict__)

    def stream_template(self) -> Iterator[str]:
        """Stream template with context vars."""
        return stream_template(self._template, **self.__dict__)

    # MARK: Helper classmethods
    # These methods accept an optional Jinja2 environment and template name. If not
    # specified, they attempt to use the current Flask app context's Jinja environment,
    # and the template specified when defining the class

    @classmethod
    def jinja_template(
        cls, env: Environment | None = None, template: str | None = None
    ) -> Template:
        """Return Jinja template object."""
        if env is None:
            env = current_app.jinja_env
        return env.get_or_select_template(template or cls._template)

    @classmethod
    def jinja_source(
        cls, env: Environment | None = None, template: str | None = None
    ) -> tuple[str, str | None]:
        """Return Jinja2 template source and filename for the Jinja template."""
        if env is None:
            env = current_app.jinja_env
        if env.loader is None:
            raise RuntimeError("Missing jinja_env.loader")
        t = template or cls._template
        return env.loader.get_source(env, t)[:2]

    @classmethod
    def jinja_python_source(
        cls, env: Environment | None = None, template: str | None = None
    ) -> str:
        """Return compiled Python source for the Jinja template."""
        if env is None:
            env = current_app.jinja_env
        jinja_source, filename = cls.jinja_source(env, template)
        python_source = env.compile(jinja_source, cls._template, filename, raw=True)
        return python_source

    @classmethod
    def jinja_validate_syntax(
        cls, env: Environment | None = None, template: str | None = None
    ) -> None:
        """Load template and raise exception if there's an error."""
        if env is None:
            env = current_app.jinja_env
        env.get_or_select_template(template or cls._template)

    @classmethod
    def jinja_ast_stack(
        cls, env: Environment | None = None, template: str | None = None
    ) -> list[TemplateAst]:
        """Return a stack of Jinja templates referenced from the first template."""
        if env is None:
            env = current_app.jinja_env
        template = template or cls._template
        stack = [
            TemplateAst(
                template, env.parse((tf := cls.jinja_source(env, template))[0]), tf[1]
            )
        ]
        processed = {template}  # Catch multiple references to the same template
        iterator = 0
        while iterator < len(stack):
            for ref_template in find_referenced_templates(stack[iterator].ast):
                if ref_template is not None and ref_template not in processed:
                    stack.append(
                        TemplateAst(
                            ref_template,
                            env.parse((tf := cls.jinja_source(env, ref_template))[0]),
                            tf[1],
                        )
                    )
                    processed.add(ref_template)
            iterator += 1
        return stack
