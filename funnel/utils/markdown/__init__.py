"""Markdown parser using markdown-it-py."""

__protected__ = ['mdit_plugins', 'tabs']

# --- Everything below this line is auto-generated using `make initpy` -----------------

from . import base, escape, mdit_plugins, tabs
from .base import (
    MarkdownConfig,
    MarkdownPlugin,
    markdown_basic,
    markdown_document,
    markdown_inline,
    markdown_mailer,
)
from .escape import HasMarkdown, MarkdownString, markdown_escape

__all__ = [
    "HasMarkdown",
    "MarkdownConfig",
    "MarkdownPlugin",
    "MarkdownString",
    "base",
    "escape",
    "markdown_basic",
    "markdown_document",
    "markdown_escape",
    "markdown_inline",
    "markdown_mailer",
    "mdit_plugins",
    "tabs",
]
