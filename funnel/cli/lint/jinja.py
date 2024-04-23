"""Jinja template linter."""

import sys
from collections import deque
from collections.abc import Sequence

import click
import jinja2
from jinja2 import TemplateNotFound, TemplateSyntaxError
from rich.console import Console

from ... import app
from ...utils import JinjaTemplateBase
from . import lint


def all_jinja_template_classes() -> dict[str, type[JinjaTemplateBase]]:
    """Find all JinjaTemplate classes and return as a dict against the template name."""
    classes = deque([JinjaTemplateBase])
    result: dict[str, type[JinjaTemplateBase]] = {}
    while True:
        try:
            cls = classes.popleft()
        except IndexError:
            break
        if hasattr(cls, '_template'):
            result[cls._template] = cls  # pylint: disable=protected-access
        classes.extend(cls.__subclasses__())
    return result


@lint.command('jinja')
@click.argument('templates', nargs=-1)
@click.option('-a', '--all', is_flag=True, help="Lint all Jinja templates.")
def lint_jinja_templates(
    templates: Sequence[str],
    all: bool = False,  # noqa: A002 # pylint: disable=redefined-builtin
) -> None:
    """Lint Jinja templates."""
    if all:
        templates = list(templates) + app.jinja_env.list_templates()
    elif not templates:
        click.echo("Specify template names (not paths) or --all")

    template_classes = all_jinja_template_classes()
    console = Console(highlight=False)
    rprint = console.print

    for template in templates:
        has_cls = True
        cls = template_classes.get(template)
        if cls is None:
            has_cls = False
            cls = type('_', (JinjaTemplateBase,), {}, template=template)
        try:
            report = cls.jinja_unresolved_identifiers()
        except TemplateNotFound:
            rprint(f"[red][bold]{template}[/] not found :cross_mark:")
            continue
        except TemplateSyntaxError:
            rprint(f"[red][bold]{template}[/] syntax error")
            console.print_exception(
                width=None,
                max_frames=1,
                word_wrap=True,
                suppress=['funnel/cli', 'funnel/utils', jinja2],
            )
            continue
        has_deps = len(report) > 1
        has_undefined = any(report.values())
        if not has_cls:
            rprint(f"[bold white]{template}[/]", end='')
        else:
            rprint(
                f"[bold white]{template}[/]"
                f" ([link={sys.modules[cls.__module__].__file__}]{cls.__module__}"
                f".[bold yellow]{cls.__qualname__}[/][/])",
                end='',
            )
        if has_undefined:
            if has_cls:
                rprint(' :cross_mark_button:', end='')
            else:
                rprint(' :cross_mark:', end='')
        else:
            rprint(' :white_check_mark:', end='')
        if has_deps and has_undefined:
            rprint(" [dim]dependencies and undefined names:")
        elif has_deps:
            rprint(" [dim]dependencies:")
        elif has_undefined:
            rprint(" [dim]undefined names:")
        else:
            rprint()
        for dep_template, undefined_names in report.items():
            rprint(f" - {dep_template}", end='')
            if undefined_names:
                rprint(': ', end='')
            rprint(
                ', '.join(
                    f'[red]{line}:[bold]{name}[/][/]'
                    for line, name in sorted(undefined_names)
                ),
                soft_wrap=True,
            )
