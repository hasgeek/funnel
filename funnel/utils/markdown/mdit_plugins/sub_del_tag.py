"""Markdown-it-py plugin for <sub> & <del> using ~subscricpt~ & ~~deleted~~."""

from typing import Any, List

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.state_inline import Delimiter

__all__ = ['del_sub_plugin']


def del_sub_plugin(md: MarkdownIt):
    def tokenize(state: StateInline, silent: bool):
        start = state.pos
        marker = state.srcCharCode[start]
        chr(marker)

        if silent:
            return False

        if marker != 0x7E:
            return False

        scanned = state.scanDelims(state.pos, True)

        for i in range(scanned.length):
            token = state.push("text", "", 0)
            token.content = chr(marker)
            state.delimiters.append(
                Delimiter(
                    marker=marker,
                    length=scanned.length,
                    jump=i,
                    token=len(state.tokens) - 1,
                    end=-1,
                    open=scanned.can_open,
                    close=scanned.can_close,
                )
            )

        state.pos += scanned.length
        return True

    def _post_process(state: StateInline, delimiters: List[Any]):
        i = len(delimiters) - 1
        while i >= 0:
            start_delim = delimiters[i]

            # /* ~ */
            if start_delim.marker != 0x7E:
                i -= 1
                continue

            # Process only opening markers
            if start_delim.end == -1:
                i -= 1
                continue

            end_delim = delimiters[start_delim.end]

            is_del = (
                i > 0
                and delimiters[i - 1].end == start_delim.end + 1
                and delimiters[i - 1].token == start_delim.token - 1
                and delimiters[start_delim.end + 1].token == end_delim.token + 1
                and delimiters[i - 1].marker == start_delim.marker
            )

            ch = chr(start_delim.marker)

            token = state.tokens[start_delim.token]
            token.type = "del_open" if is_del else "sub_open"
            token.tag = "del" if is_del else "sub"
            token.nesting = 1
            token.markup = ch + ch if is_del else ch
            token.content = ""

            token = state.tokens[end_delim.token]
            token.type = "del_close" if is_del else "sub_close"
            token.tag = "del" if is_del else "sub"
            token.nesting = -1
            token.markup = ch + ch if is_del else ch
            token.content = ""

            if is_del:
                state.tokens[delimiters[i - 1].token].content = ""
                state.tokens[delimiters[start_delim.end + 1].token].content = ""
                i -= 1

            i -= 1

    md.inline.ruler.disable('strikethrough')
    md.inline.ruler.before('emphasis', 'sub_del', tokenize)

    def post_process(state: StateInline):
        _post_process(state, state.delimiters)

        for token in state.tokens_meta:
            if token and "delimiters" in token:
                _post_process(state, token["delimiters"])

    md.inline.ruler2.disable('strikethrough')
    md.inline.ruler2.before('emphasis', 'del', post_process)

    def del_open(self, tokens, idx, options, env):
        return '<del>'

    def del_close(self, tokens, idx, options, env):
        return '</del>'

    def sub_open(self, tokens, idx, options, env):
        return '<sub>'

    def sub_close(self, tokens, idx, options, env):
        return '</sub>'

    md.add_render_rule('del_open', del_open)
    md.add_render_rule('del_close', del_close)
    md.add_render_rule('sub_open', sub_open)
    md.add_render_rule('sub_close', sub_close)
