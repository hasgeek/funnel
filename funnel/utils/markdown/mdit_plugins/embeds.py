"""
Markdown-it-py plugin to handle embeds.

Ported from mdit_py_plugins.container
and mdit_py_plugins.colon_fence.
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping, Sequence
from math import floor

from markdown_it import MarkdownIt
from markdown_it.common.utils import charCodeAt
from markdown_it.renderer import OptionsDict, RendererHTML
from markdown_it.rules_block import StateBlock
from markdown_it.token import Token

LOADING_PLACEHOLDER = {
    'markmap': 'Mindmap',
    'mermaid': 'Visualization',
    'vega-lite': 'Visualization',
}

VALIDATE_RE = re.compile(r'^{\s*([a-zA-Z0-9_\-]+)\s*}.*$')


def embeds_plugin(
    md: MarkdownIt,
    name: str,
    marker: str = '`',
) -> None:
    def validate(params: str, *args) -> bool:
        results = VALIDATE_RE.findall(params.strip())
        return len(results) != 0 and results[0] == name

    def render(
        renderer: RendererHTML,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: MutableMapping,
    ) -> str:
        token = tokens[idx]
        content = md.utils.escapeHtml(token.content)
        placeholder = LOADING_PLACEHOLDER.get(name, '')
        return (
            f'<div class="md-embed md-embed-{name}">'
            + f'<div class="embed-loading">{placeholder}</div>'
            + '<pre class="embed-content">'
            + content
            + '</pre><div class="embed-container"></div></div>\n'
        )

    min_markers = 3
    marker_str = marker
    marker_char = charCodeAt(marker_str, 0)
    marker_len = len(marker_str)

    def embeds_func(
        state: StateBlock, start_line: int, end_line: int, silent: bool
    ) -> bool:
        auto_closed = False
        start = state.bMarks[start_line] + state.tShift[start_line]
        maximum = state.eMarks[start_line]

        # Check out the first character quickly,
        # this should filter out most of non-containers
        if marker_char != ord(state.src[start]):
            return False

        # Check out the rest of the marker string
        pos = start + 1
        while pos <= maximum:
            try:
                character = state.src[pos]
            except IndexError:
                break
            if marker_str[(pos - start) % marker_len] != character:
                break
            pos += 1

        marker_count = floor((pos - start) / marker_len)
        if marker_count < min_markers:
            return False
        pos -= (pos - start) % marker_len

        markup = state.src[start:pos]
        params = state.src[pos:maximum]

        if not validate(params, markup):
            return False

        # Since start is found, we can report success here in validation mode
        if silent:
            return True

        # Search for the end of the block
        next_line = start_line

        while True:
            next_line += 1
            if next_line >= end_line:
                # unclosed block should be autoclosed by end of document.
                # also block seems to be autoclosed by end of parent
                break

            start = state.bMarks[next_line] + state.tShift[next_line]
            maximum = state.eMarks[next_line]

            if start < maximum and state.sCount[next_line] < state.blkIndent:
                # non-empty line with negative indent should stop the list:
                # - ```
                #  test
                break

            if marker_char != ord(state.src[start]):
                continue

            if state.sCount[next_line] - state.blkIndent >= 4:
                # closing fence should be indented less than 4 spaces
                continue

            pos = start + 1
            while pos <= maximum:
                try:
                    character = state.src[pos]
                except IndexError:
                    break
                if marker_str[(pos - start) % marker_len] != character:
                    break
                pos += 1

            # closing code fence must be at least as long as the opening one
            if floor((pos - start) / marker_len) < marker_count:
                continue

            # make sure tail has spaces only
            pos -= (pos - start) % marker_len
            pos = state.skipSpaces(pos)

            if pos < maximum:
                continue

            # found!
            auto_closed = True
            break

        state.line = next_line + (1 if auto_closed else 0)

        # Borrowed from mdit_py_plugins.colon_fence
        token = state.push(f'embed_{name}', 'div', 0)
        token.info = params
        token.content = state.getLines(start_line + 1, next_line, marker_count, True)
        token.markup = markup
        token.map = [start_line, state.line]

        return True

    md.block.ruler.before(
        'fence',
        f'embed_{name}',
        embeds_func,
    )

    md.add_render_rule(f'embed_{name}', render)
