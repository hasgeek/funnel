"""
Markdown-it-py plugin to introduce <abbr> markup for defined abbreviations.

Ported from javascript plugin markdown-it-abbr.
"""

from __future__ import annotations

import re

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token

__all__ = ['abbr_plugin']

abbr_def_re = re.compile(r'^\s*\*\[(.+?)\]:(.+)$')


def abbr_def(state: StateBlock, start_line: int, end_line: int, silent: bool) -> bool:
    """Store abbreviation definitions in env and remove them from content."""
    pos = state.bMarks[start_line] + state.tShift[start_line]
    maximum = state.eMarks[start_line]

    if pos + 2 >= maximum:
        return False

    line = state.src[pos:maximum]

    if not line.startswith('*['):
        return False

    result = abbr_def_re.match(line)

    if result is None:
        return False

    if silent:
        return True

    # Extract label and title and store it in state.env

    label = result.group(1).replace('\\', '')
    title = result.group(2).strip()

    if len(label) == 0 or len(title) == 0:
        return False

    if 'abbr' not in state.env:
        state.env['abbr'] = {}

    if label not in state.env['abbr']:
        state.env['abbr'][label] = title

    state.line = start_line + 1
    return True


def abbr_replace(state: StateInline) -> None:
    """Tokenizes and tags defined abbreviations in content."""
    block_tokens = state.tokens

    if 'abbr' not in state.env:
        return

    labels_re_str = '|'.join(
        [state.md.utils.escapeRE(k) for k in sorted(state.env['abbr'].keys(), key=len)]
    )

    simple_re = re.compile('(?:' + labels_re_str + ')')

    match_re_str = r'(^|\W)(' + labels_re_str + r')($|\W)'

    match_re = re.compile(match_re_str)

    block_token_index, block_tokens_length = 0, len(block_tokens)
    while block_token_index < block_tokens_length:
        block_token = block_tokens[block_token_index]
        if block_token.type != 'inline':
            block_token_index += 1
            continue
        tokens = block_token.children

        token_index = len(tokens) - 1  # type: ignore[arg-type]
        while token_index >= 0:
            current_token = tokens[token_index]  # type: ignore[index]
            if current_token.type != 'text':
                token_index -= 1
                continue

            current_text = current_token.content

            nodes = []

            if simple_re.search(current_text) is None:
                token_index -= 1
                continue

            next_pos = 0
            for matches in match_re.finditer(current_text):
                prefix, match = matches.groups()[:2]
                prefix_indices, suffix_indices = matches.regs[1:4:2]

                if prefix != '':
                    token = Token('text', '', 0)
                    token.content = current_text[next_pos : prefix_indices[1]]
                    nodes.append(token)

                token = Token('abbr_open', 'abbr', 1)
                token.attrs['title'] = state.env['abbr'][match]
                nodes.append(token)

                token = Token('text', '', 0)
                token.content = match
                nodes.append(token)

                token = Token('abbr_close', 'abbr', -1)
                nodes.append(token)

                next_pos = suffix_indices[0]

            if len(nodes) == 0:
                token_index -= 1
                continue

            if next_pos < len(current_text):
                token = Token('text', '', 0)
                token.content = current_text[next_pos:]
                nodes.append(token)

            block_token.children = tokens = state.md.utils.arrayReplaceAt(
                tokens, token_index, nodes
            )
            token_index -= 1

        block_token_index += 1


def abbr_plugin(md: MarkdownIt) -> None:
    md.block.ruler.before(
        'reference', 'abbr_def', abbr_def, {'alt': ['paragraph', 'reference']}
    )
    md.core.ruler.after('linkify', 'abbr_replace', abbr_replace)
