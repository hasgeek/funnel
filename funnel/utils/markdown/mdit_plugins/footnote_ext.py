"""Markdown-it-py plugin to modify output of the footnote plugin."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict
from mdit_py_plugins.footnote.index import render_footnote_caption

__all__ = ['footnote_extend_plugin']


def caption(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    output = render_footnote_caption(renderer, tokens, idx, options, env)
    return output.replace('[', '').replace(']', '')


def footnote_extend_plugin(md: MarkdownIt, **_opts: Any) -> None:
    if 'footnote_ref' not in md.get_active_rules()['inline']:
        return
    md.add_render_rule('footnote_caption', caption)
