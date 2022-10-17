"""
Markdown-it-py plugin to introduce <mark> markup using ==marked==.

Ported from markdown_it.rules_inline.strikethrough.
"""

from typing import Any, List

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.state_inline import Delimiter

__all__ = ['mark_plugin']


def mark_plugin(md: MarkdownIt):
    def tokenize(state: StateInline, silent: bool):
        """Insert each marker as a separate text token, and add it to delimiter list."""
        start = state.pos
        marker = state.srcCharCode[start]
        ch = chr(marker)

        if silent:
            return False

        if marker != 0x3D:
            return False

        scanned = state.scanDelims(state.pos, True)

        length = scanned.length

        if length < 2:
            return False

        if length % 2:
            token = state.push("text", "", 0)
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
                    jump=i // 2,  # for `==` 1 marker = 2 characters
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
            if start_delim.marker != 0x3D:
                i += 1
                continue

            if start_delim.end == -1:
                i += 1
                continue

            end_delim = delimiters[start_delim.end]

            token = state.tokens[start_delim.token]
            token.type = 'mark_open'
            token.tag = 'mark'
            token.nesting = 1
            token.markup = '=='
            token.content = ''

            token = state.tokens[end_delim.token]
            token.type = 'mark_close'
            token.tag = 'mark'
            token.nesting = -1
            token.markup = '=='
            token.content = ''

            end_token = state.tokens[end_delim.token - 1]

            if end_token.type == 'text' and end_token == chr(0x3D):
                lone_markers.append(end_delim.token - 1)

        # If a marker sequence has an odd number of characters, it's split
        # like this: `=====` -> `=` + `==` + `==`, leaving one marker at the
        # start of the sequence.
        #
        # So, we have to move all those markers after subsequent mark_close tags.
        #
        while lone_markers:
            i = lone_markers.pop()
            j = i + 1

            while j < len(state.tokens) and state.tokens[j].type == 'mark_close':
                j += 1

            j -= 1

            if i != j:
                token = state.tokens[j]
                state.tokens[j] = state.tokens[i]
                state.tokens[i] = token

    md.inline.ruler.before('strikethrough', 'mark', tokenize)

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
                if curr_meta and "delimiters" in curr_meta:
                    _post_process(state, curr_meta["delimiters"])
            curr += 1

    md.inline.ruler2.before('strikethrough', 'mark', post_process)

    def mark_open(self, tokens, idx, options, env):
        return '<mark>'

    def mark_close(self, tokens, idx, options, env):
        return '</mark>'

    md.add_render_rule('mark_open', mark_open)
    md.add_render_rule('mark_close', mark_close)
