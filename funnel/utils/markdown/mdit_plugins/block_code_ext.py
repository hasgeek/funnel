"""MDIT plugin to add language-none class to code fence & code block tokens."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

__all__ = ['block_code_extend_plugin']


def fence(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    output = RendererHTML.fence(renderer, tokens, idx, options, env)
    output = output.replace('<pre><code>', '<pre><code class="language-none">')
    return output


def code_block(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: EnvType,
) -> str:
    output = RendererHTML.code_block(renderer, tokens, idx, options, env)
    output = output.replace('<pre><code>', '<pre><code class="language-none">')
    return output


def block_code_extend_plugin(md: MarkdownIt, **opts: Any) -> None:
    """Add CSS class ``language-none`` for code fences with no language identifier."""
    md.add_render_rule('fence', fence)
    md.add_render_rule('code_block', code_block)
