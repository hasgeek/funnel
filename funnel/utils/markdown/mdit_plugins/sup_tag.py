"""Markdown-it-py plugin to introduce <sup> markup using ^superscript^."""

from typing import Any, List

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.state_inline import Delimiter


def sup_plugin(md: MarkdownIt):
    def tokenize(state: StateInline, silent: bool):
        start = state.pos
        marker = state.srcCharCode[start]
        ch = chr(marker)

        if silent:
            return False

        if marker != 0x5E:
            return False

        scanned = state.scanDelims(state.pos, True)

        length = scanned.length

        i = 0
        while i < length:
            token = state.push('text', '', 0)
            token.content = ch
            state.delimiters.append(
                Delimiter(
                    marker=marker,
                    length=0,
                    jump=i,
                    token=len(state.tokens) - 1,
                    end=-1,
                    open=scanned.can_open,
                    close=scanned.can_close,
                )
            )
            i += 1

        state.pos += scanned.length
        return True

    def _post_process(state: StateInline, delimiters: List[Any]):
        lone_markers = []
        max_ = len(delimiters)

        for i in range(0, max_):
            start_delim = delimiters[i]
            if start_delim.marker != 0x5E or start_delim.end == -1:
                continue
            end_delim = delimiters[start_delim.end]

            token = state.tokens[start_delim.token]
            token.type = 'sup_open'
            token.tag = 'sup'
            token.nesting = 1
            token.markup = '^'
            token.content = ''

            token = state.tokens[end_delim.token]
            token.type = 'sup_close'
            token.tag = 'sup'
            token.nesting = -1
            token.markup = '^'
            token.content = ''

            end_token = state.tokens[end_delim.token - 1]

            if end_token.type == 'text' and end_token == chr(0x5E):
                lone_markers.append(end_delim.token - 1)

        while len(lone_markers) > 0:
            i = lone_markers.pop()
            j = i + 1

            while j < len(state.tokens) and state.tokens[j].type == 'sup_close':
                j += 1

            j -= 1

            if i != j:
                (state.tokens[i], state.tokens[j]) = (state.tokens[j], state.tokens[i])

    md.inline.ruler.before('emphasis', 'sup', tokenize)

    def post_process(state: StateInline):
        tokens_meta = state.tokens_meta
        max_ = len(state.tokens_meta)
        _post_process(state, state.delimiters)
        for current in range(0, max_):
            if tokens_meta[current] and tokens_meta[current]['delimiters']:
                _post_process(state, tokens_meta[current]['delimiters'])

    md.inline.ruler2.before('emphasis', 'sup', post_process)

    def sup_open(self, tokens, idx, options, env):
        return '<sup>'

    def sup_close(self, tokens, idx, options, env):
        return '</sup>'

    md.add_render_rule('sup_open', sup_open)
    md.add_render_rule('sup_close', sup_close)
