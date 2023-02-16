"""
Markdown-it-py plugin to introduce <abbr> markup for defined abbreviations.

Ported from javascript plugin markdown-it-abbr.
"""

import re
import unicodedata

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token

__all__ = ['abbr_plugin']

ASTERISK_CHAR = 0x2A  # ASCII value for `*`
OPEN_SQBR_CHAR = 0x5B  # ASCII value for `[`
CLOSE_SQBR_CHAR = 0x5D  # ASCII value for `]`
BACKSLASH_CHAR = 0x5C  # ASCII value for `\`
COLON_CHAR = 0x3A  # ASCII value for `:`

PADDING_CHARACTERS = (
    '['
    + ''.join(
        chr(x) for x in range(65536) if unicodedata.category(chr(x))[0] in ('P', 'Z')
    )
    .replace('\\', '\\\\')
    .replace('[', '\\[')
    .replace(']', '\\]')
    + ' \r\n$+<=>^`|~'
    + ']'
)


def abbr_def(state: StateBlock, start_line: int, end_line: int, silent: bool):
    pos = state.bMarks[start_line] + state.tShift[start_line]
    maximum = state.eMarks[start_line]

    if pos + 2 >= maximum:
        return False

    # Check if line is of the format `*[Abbreviation]:Full Form`
    if state.srcCharCode[pos] != ASTERISK_CHAR:
        return False
    pos += 1
    if state.srcCharCode[pos] != OPEN_SQBR_CHAR:
        return False
    pos += 1

    label_end = -1
    label_start = pos
    while pos < maximum:
        ch = state.srcCharCode[pos]
        if ch == OPEN_SQBR_CHAR:  # pylint: disable=no-else-return
            return False
        elif ch == CLOSE_SQBR_CHAR:
            label_end = pos
            break
        elif ch == BACKSLASH_CHAR:
            pos += 1
        pos += 1

    if label_end < 0 or state.srcCharCode[label_end + 1] != COLON_CHAR:
        return False

    if silent:
        return True

    # Extract label and title and store it in state.env
    label = state.src[label_start:label_end].replace('\\', '')
    title = state.src[label_end + 2 : maximum].strip()
    if len(label) == 0 or len(title) == 0:
        return False

    if 'abbr' not in state.env:
        state.env['abbr'] = {}

    if label not in state.env['abbr']:
        state.env['abbr'][label] = title

    state.line = start_line + 1
    return True


def abbr_replace(state: StateInline):
    block_tokens = state.tokens

    if 'abbr' not in state.env:
        return

    labels_re_str = '|'.join(
        [state.md.utils.escapeRE(k) for k in sorted(state.env['abbr'].keys(), key=len)]
    )

    simple_re = re.compile('(?:' + labels_re_str + ')')

    match_re_str = (
        '(^|' + PADDING_CHARACTERS + ')'
        '(' + labels_re_str + ')'
        '($|' + PADDING_CHARACTERS + ')'
    )

    match_re = re.compile(match_re_str)

    j, block_tokens_length = 0, len(block_tokens)
    while j < block_tokens_length:
        block_token = block_tokens[j]
        if block_token.type != 'inline':
            j += 1
            continue
        tokens = block_token.children

        i = len(tokens) - 1  # type: ignore[arg-type]
        while i >= 0:
            current_token = tokens[i]  # type: ignore[index]
            if current_token.type != 'text':
                i -= 1
                continue

            current_text = current_token.content

            nodes = []

            if simple_re.search(current_text) is None:
                i -= 1
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
                i -= 1
                continue

            if next_pos < len(current_text):
                token = Token('text', '', 0)
                token.content = current_text[next_pos:]
                nodes.append(token)

            block_token.children = tokens = state.md.utils.arrayReplaceAt(
                tokens, i, nodes
            )
            i -= 1

        j += 1


def abbr_plugin(md: MarkdownIt):
    md.block.ruler.before(
        'reference', 'abbr_def', abbr_def, {'alt': ['paragraph', 'reference']}
    )
    md.core.ruler.after('linkify', 'abbr_replace', abbr_replace)
