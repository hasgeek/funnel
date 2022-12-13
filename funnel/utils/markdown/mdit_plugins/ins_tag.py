"""
Markdown-it-py plugin to introduce <ins> markup using ++inserted++.

Ported from markdown_it.rules_inline.strikethrough.
"""

from typing import Any, List

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.state_inline import Delimiter

__all__ = ['ins_plugin']

PLUS_CHAR = 0x2B  # ASCII value for `+`


def ins_plugin(md: MarkdownIt) -> None:
    def tokenize(state: StateInline, silent: bool):
        """Insert each marker as a separate text token, and add it to delimiter list."""
        start = state.pos
        marker = state.srcCharCode[start]
        ch = chr(marker)

        if silent:
            return False

        if marker != PLUS_CHAR:
            return False

        scanned = state.scanDelims(state.pos, True)

        length = scanned.length

        if length < 2:
            return False

        if length % 2:
            token = state.push('text', '', 0)
            token.content = ch
            length -= 1

        i = 0
        while i < length:
            token = state.push('text', '', 0)
            token.content = ch + ch
            state.delimiters.append(
                Delimiter(
                    marker=marker,
                    length=0,  # disable "rule of 3" length checks meant for emphasis
                    jump=i // 2,  # for `++` 1 marker = 2 characters
                    token=len(state.tokens) - 1,
                    end=-1,
                    open=scanned.can_open,
                    close=scanned.can_close,
                )
            )
            i += 2

        state.pos += scanned.length
        return True

    def _post_process(state: StateInline, delimiters: List[Any]):
        lone_markers = []
        maximum = len(delimiters)

        for i in range(0, maximum):
            start_delim = delimiters[i]
            if start_delim.marker != PLUS_CHAR:
                i += 1
                continue

            if start_delim.end == -1:
                i += 1
                continue

            end_delim = delimiters[start_delim.end]

            token = state.tokens[start_delim.token]
            token.type = 'ins_open'
            token.tag = 'ins'
            token.nesting = 1
            token.markup = '++'
            token.content = ''

            token = state.tokens[end_delim.token]
            token.type = 'ins_close'
            token.tag = 'ins'
            token.nesting = -1
            token.markup = '++'
            token.content = ''

            end_token = state.tokens[end_delim.token - 1]

            if end_token.type == 'text' and end_token == '+':  # nosec
                lone_markers.append(end_delim.token - 1)

        # If a marker sequence has an odd number of characters, it's split
        # like this: `+++++` -> `+` + `++` + `++`, leaving one marker at the
        # start of the sequence.
        #
        # So, we have to move all those markers after subsequent ins_close tags.
        #
        while lone_markers:
            i = lone_markers.pop()
            j = i + 1

            while j < len(state.tokens) and state.tokens[j].type == 'ins_close':
                j += 1

            j -= 1

            if i != j:
                token = state.tokens[j]
                state.tokens[j] = state.tokens[i]
                state.tokens[i] = token

    md.inline.ruler.before('strikethrough', 'ins', tokenize)

    def post_process(state: StateInline):
        """Walk through delimiter list and replace text tokens with tags."""
        tokens_meta = state.tokens_meta
        maximum = len(state.tokens_meta)
        _post_process(state, state.delimiters)
        curr = 0
        while curr < maximum:
            try:
                curr_meta = tokens_meta[curr]
            except IndexError:
                pass
            else:
                if curr_meta and 'delimiters' in curr_meta:
                    _post_process(state, curr_meta["delimiters"])
            curr += 1

    md.inline.ruler2.before('strikethrough', 'ins', post_process)

    def ins_open(self, tokens, idx, options, env):
        return '<ins>'

    def ins_close(self, tokens, idx, options, env):
        return '</ins>'

    md.add_render_rule('ins_open', ins_open)
    md.add_render_rule('ins_close', ins_close)
