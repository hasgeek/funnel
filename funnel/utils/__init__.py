"""Utility functions."""

__ignore__ = ['base', 'escape', 'tabs']  # Unwanted exports from markdown sub-package

# --- Everything below this line is auto-generated using `make initpy` -----------------

from . import markdown, misc, mustache
from .markdown import (
    HasMarkdown,
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
    "HasMarkdown",
    "MarkdownConfig",
    "MarkdownPlugin",
    "MarkdownString",
    "abort_null",
    "blake2b160_hex",
    "extract_twitter_handle",
    "format_twitter_handle",
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
