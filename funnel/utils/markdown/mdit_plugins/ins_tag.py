"""Markdown-it-py plugin to introduce <ins> markup using ++inserted++."""

from typing import Any, List

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.state_inline import Delimiter


def ins_plugin(md: MarkdownIt):
    def tokenize(state: StateInline, silent: bool):
        start = state.pos
        marker = state.srcCharCode[start]
        ch = chr(marker)

        if silent:
            return False

        if marker != 0x2B:
            return False

        scanned = state.scanDelims(state.pos, True)

        length = scanned.length

        if length < 2:
            return False

        i = 0
        while i < length:
            token = state.push('text', '', 0)
            token.content = ch + ch
            state.delimiters.append(
                Delimiter(
                    marker=marker,
                    length=0,
                    jump=i // 2,
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
        max_ = len(delimiters)

        for i in range(0, max_):
            start_delim = delimiters[i]
            if start_delim.marker != 0x2B or start_delim.end == -1:
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

            if end_token.type == 'text' and end_token == chr(0x2B):
                lone_markers.append(end_delim.token - 1)

        while len(lone_markers) > 0:
            i = lone_markers.pop()
            j = i + 1

            while j < len(state.tokens) and state.tokens[j].type == 'ins_close':
                j += 1

            j -= 1

            if i != j:
                (state.tokens[i], state.tokens[j]) = (state.tokens[j], state.tokens[i])

    md.inline.ruler.before('emphasis', 'ins', tokenize)

    def post_process(state: StateInline):
        tokens_meta = state.tokens_meta
        max_ = len(state.tokens_meta)
        _post_process(state, state.delimiters)
        for current in range(0, max_):
            if tokens_meta[current] and tokens_meta[current]['delimiters']:
                _post_process(state, tokens_meta[current]['delimiters'])

    md.inline.ruler2.before('emphasis', 'ins', post_process)

    def ins_open(self, tokens, idx, options, env):
        return '<ins>'

    def ins_close(self, tokens, idx, options, env):
        return '</ins>'

    md.add_render_rule('ins_open', ins_open)
    md.add_render_rule('ins_close', ins_close)
