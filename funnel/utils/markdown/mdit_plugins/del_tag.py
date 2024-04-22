"""Markdown-it-py plugin to replace <s> with <del> for ~~."""

from __future__ import annotations

from collections.abc import Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

__all__ = ['del_plugin']


def del_open(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    return '<del>'


def del_close(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    return '</del>'


def del_plugin(md: MarkdownIt) -> None:
    """Render ``~~text~~`` markup with a HTML ``<del>`` tag."""
    md.add_render_rule('s_open', del_open)
    md.add_render_rule('s_close', del_close)
