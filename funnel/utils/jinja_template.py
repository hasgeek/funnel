"""Jinja2 templates with type hints (in future: also type checking of the template)."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any, ClassVar, Literal, NamedTuple, get_type_hints

from flask import current_app, render_template, stream_template
from jinja2 import Environment, Template, nodes
from jinja2.compiler import CodeGenerator, Frame
from jinja2.meta import find_referenced_templates
from typing_extensions import dataclass_transform

from coaster.utils import is_dunder

__all__ = ['JinjaTemplateBase', 'jinja_global', 'jinja_undefined']

# MARK: Jinja helpers ------------------------------------------------------------------


class TemplateAst(NamedTuple):
    template: str
    ast: nodes.Template
    filename: str | None

    def __repr__(self) -> str:
        return f'TemplateAst({self.template!r}, ast, {self.filename!r})'


class TrackingCodeGenerator(CodeGenerator):
    """Fix the implementation in jinja2.meta to track context apart from frames."""

    def __init__(self, *args, templates: list[TemplateAst], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.templates = {
            template_ast.template: template_ast for template_ast in templates
        }
        self.context_vars: set[str] = set(self.environment.globals.keys())
        self.unresolved_identifiers: dict[str, set[tuple[int, str]]] = {
            (self.name or ''): set()
        }
        self.unresolved_identifiers_in_frame: set[str] | None = None

    def visit_new_template(
        self, template: str, with_context: bool, frame: Frame | None = None
    ) -> None:
        """Visit a new template, passing forward context if required."""
        template_ast = self.templates[template]
        codegen = self.__class__(
            environment=self.environment,
            name=template_ast.template,
            filename=template_ast.filename,
            templates=[],
        )
        codegen.templates = self.templates
        if with_context:
            if frame:
                # Copied context, with both top-level context and local context
                codegen.context_vars = self.context_vars | set(
                    frame.symbols.dump_stores().keys()
                )
            else:
                # Shared top-level context (required for `extends` tag)
                codegen.context_vars = self.context_vars
        codegen.visit(template_ast.ast)
        self.unresolved_identifiers.update(codegen.unresolved_identifiers)

    def pop_assign_tracking(self, frame: Frame) -> None:
        """Track top-level variable assignments."""
        if frame.toplevel:
            new_vars = self._assign_stack[-1]
            if new_vars:
                self.context_vars.update(new_vars)
        return super().pop_assign_tracking(frame)

    def enter_frame(self, frame: Frame) -> None:
        unresolved_identifiers = {
            param
            for (_target, (action, param)) in frame.symbols.loads.items()
            if action == 'resolve'
            and param not in self.context_vars
            and param not in set(frame.symbols.dump_stores().keys())
        }
        if unresolved_identifiers:
            self.unresolved_identifiers_in_frame = unresolved_identifiers
        return super().enter_frame(frame)

    def leave_frame(self, frame: Frame, with_python_scope: bool = False) -> None:
        if with_python_scope and (unresolved := self.unresolved_identifiers_in_frame):
            for each in unresolved:
                self.unresolved_identifiers[self.name or ''].add((0, each))
            self.unresolved_identifiers_in_frame = None
        return super().leave_frame(frame, with_python_scope)

    def visit_Include(self, node: nodes.Include, frame: Frame) -> None:  # noqa: N802
        """Examine an included template."""
        super().visit_Include(node, frame)
        template = None
        include_template: Any = node.template
        if isinstance(include_template, (nodes.Tuple, nodes.List)):
            try:
                include_template = include_template.as_const()
            except nodes.Impossible:
                warnings.warn(
                    f"Can't process dynamic include: {node.template}", stacklevel=1
                )
                return
        if isinstance(include_template, nodes.Const):
            include_template = include_template.value
        if isinstance(include_template, str):
            if include_template in self.templates:
                template = include_template
        elif isinstance(include_template, (tuple, list)):
            for candidate in include_template:
                if candidate in self.templates:
                    template = candidate
                    break
        if template is not None:
            self.visit_new_template(template, node.with_context, frame)

    def visit_Extends(self, node: nodes.Extends, frame: Frame) -> None:  # noqa: N802
        """Extend context to an extended template."""
        super().visit_Extends(node, frame)
        try:
            template = node.template.as_const()
        except nodes.Impossible:
            warnings.warn(f"Can't process dynamic extends at {node}", stacklevel=1)
        if template not in self.templates:
            warnings.warn(f"Cannot extend unknown template {template}", stacklevel=1)
        self.visit_new_template(template, with_context=True)  # No frame

    def visit_Import(self, node: nodes.Import, frame: Frame) -> None:  # noqa: N802
        """Examine an imported template."""
        super().visit_Import(node, frame)
        try:
            template = node.template.as_const()
        except nodes.Impossible:
            warnings.warn(f"Can't process dynamic import at {node}", stacklevel=1)
        if template not in self.templates:
            warnings.warn(f"Cannot import unknown template {template}", stacklevel=1)
        self.visit_new_template(template, node.with_context, frame)
        if frame.toplevel:
            self.context_vars.add(node.target)

    def visit_FromImport(  # noqa: N802
        self, node: nodes.FromImport, frame: Frame
    ) -> None:
        """Examine an imported template and track symbols added to context."""
        super().visit_FromImport(node, frame)
        try:
            template = node.template.as_const()
        except nodes.Impossible:
            warnings.warn(f"Can't process dynamic import at {node}", stacklevel=1)
        if template not in self.templates:
            warnings.warn(f"Cannot import unknown template {template}", stacklevel=1)
        self.visit_new_template(template, node.with_context, frame)
        if frame.toplevel:
            self.context_vars.update(
                name[1] if isinstance(name, tuple) else name for name in node.names
            )

    def visit_Macro(self, node: nodes.Macro, frame: Frame) -> None:  # noqa: N802
        """Record macro names as top-level context."""
        super().visit_Macro(node, frame)
        if frame.toplevel:
            self.context_vars.add(node.name)

    def visit_Name(self, node: nodes.Name, frame: Frame) -> None:  # noqa: N802
        if (
            node.ctx == 'load'
            and (unresolved := self.unresolved_identifiers_in_frame) is not None
            and node.name in unresolved
        ):
            self.unresolved_identifiers[self.name or ''].add((node.lineno, node.name))
            unresolved.remove(node.name)
        return super().visit_Name(node, frame)


# MARK: Typed template dataclass -------------------------------------------------------


def jinja_global(*, init: Literal[False] = False) -> Any:
    """Sentinel for a Jinja2 environment global value."""
    return ...


def jinja_undefined(*, default: Literal[None] = None) -> Any:
    """Sentinel for an optional Jinja2 context variable."""
    return ...


@dataclass_transform(
    eq_default=False,
    kw_only_default=True,
    field_specifiers=(jinja_global, jinja_undefined),
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

    @classmethod
    def jinja_validate_vars(
        cls,
        env: Environment | None = None,
    ) -> dict[str, set[tuple[int, str]]]:
        """Find vars used in the template but missing in the dataclass."""
        if env is None:
            env = current_app.jinja_env
        dataclass_vars = set(get_type_hints(cls).keys())
        dataclass_vars.discard('_template')
        stack = cls.jinja_ast_stack(env, cls._template)
        first = stack[0]
        codegen = TrackingCodeGenerator(
            environment=env,
            name=first.template,
            filename=first.filename,
            templates=stack,
        )
        codegen.context_vars |= set(dataclass_vars)
        codegen.visit(first.ast)
        return codegen.unresolved_identifiers
