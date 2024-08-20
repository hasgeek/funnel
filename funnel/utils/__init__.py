"""Utility functions."""

__ignore__ = ['base', 'escape', 'tabs']  # Unwanted exports from markdown sub-package

# MARK: Everything below this line is auto-generated using `make initpy` ---------------

from . import cache, jinja_template, markdown, misc, mustache
from .cache import DictCache
from .jinja_template import JinjaTemplateBase, jinja_global, jinja_undefined
from .markdown import (
    MarkdownConfig,
    MarkdownPlugin,
    MarkdownString,
    markdown_basic,
    markdown_document,
    markdown_escape,
    markdown_inline,
    markdown_mailer,
    mdit_plugins,
)
from .misc import (
    TIMEDELTA_1DAY,
    abort_null,
    blake2b160_hex,
    extract_twitter_handle,
    format_twitter_handle,
    make_qrcode,
    make_redirect_url,
    mask_email,
    mask_phone,
    split_name,
)
from .mustache import mustache_html, mustache_md

__all__ = [
    "DictCache",
    "JinjaTemplateBase",
    "MarkdownConfig",
    "MarkdownPlugin",
    "MarkdownString",
    "TIMEDELTA_1DAY",
    "abort_null",
    "blake2b160_hex",
    "cache",
    "extract_twitter_handle",
    "format_twitter_handle",
    "jinja_global",
    "jinja_template",
    "jinja_undefined",
    "make_qrcode",
    "make_redirect_url",
    "markdown",
    "markdown_basic",
    "markdown_document",
    "markdown_escape",
    "markdown_inline",
    "markdown_mailer",
    "mask_email",
    "mask_phone",
    "mdit_plugins",
    "misc",
    "mustache",
    "mustache_html",
    "mustache_md",
    "split_name",
]
