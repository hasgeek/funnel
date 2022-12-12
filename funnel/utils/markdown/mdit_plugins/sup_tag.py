"""
Markdown-it-py plugin to introduce <sup> markup using ^superscript^.

Ported from
https://github.com/markdown-it/markdown-it-sup/blob/master/dist/markdown-it-sup.js
"""

import re

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline

__all__ = ['sup_plugin']

CARET_CHAR = 0x5E  # ASCII value for `^`


def sup_plugin(md: MarkdownIt):
    def tokenize(state: StateInline, silent: bool):
        start = state.pos
        marker = state.srcCharCode[start]
        maximum = state.posMax
        found = False

        if silent:
            return False

        if marker != CARET_CHAR:
            return False

        # Don't run any pairs in validation mode
        if start + 2 >= maximum:
            return False

        state.pos = start + 1

        while state.pos < maximum:
            if state.srcCharCode[state.pos] == CARET_CHAR:
                found = True
                break
            state.md.inline.skipToken(state)

        if not found or start + 1 == state.pos:
            state.pos = start
            return False

        content = state.src[start + 1 : state.pos]

        # Don't allow unescaped spaces/newlines inside
        if re.search(r'(^|[^\\])(\\\\)*\s', content) is not None:
            state.pos = start
            return False

        state.posMax = state.pos
        state.pos = start + 1

        # Earlier we checked "not silent", but this implementation does not need it
        token = state.push('sup_open', 'sup', 1)
        token.markup = '^'

        token = state.push('text', '', 0)
        token.content = content.replace(
            r'\\([ \\!"#$%&\'()*+,.\/:;<=>?@[\]^_`{|}~-])', '$1'
        )

        token = state.push('sup_close', 'sup', -1)
        token.markup = '^'

        state.pos = state.posMax + 1
        state.posMax = maximum
        return True

    md.inline.ruler.after('emphasis', 'sup', tokenize)

    def sup_open(self, tokens, idx, options, env):
        return '<sup>'

    def sup_close(self, tokens, idx, options, env):
        return '</sup>'

    md.add_render_rule('sup_open', sup_open)
    md.add_render_rule('sup_close', sup_close)
