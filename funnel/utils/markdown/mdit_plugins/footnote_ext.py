"""Markdown-it-py plugin to modify output of the footnote plugin."""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import OptionsDict, RendererHTML
from markdown_it.token import Token
from mdit_py_plugins.footnote.index import render_footnote_caption


def caption(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: MutableMapping,
) -> str:
    output = render_footnote_caption(renderer, tokens, idx, options, env)
    return output.replace('[', '').replace(']', '')


def footnote_extend_plugin(md: MarkdownIt, **opts) -> None:
    if 'footnote_ref' not in md.get_active_rules()['inline']:
        return
    md.add_render_rule('footnote_caption', caption)
