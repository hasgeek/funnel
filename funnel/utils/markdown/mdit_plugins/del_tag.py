"""Markdown-it-py plugin to replace <s> with <del> for ~~."""

from markdown_it import MarkdownIt

__all__ = ['del_plugin']


def del_plugin(md: MarkdownIt) -> None:
    def del_open(self, tokens, idx, options, env):
        return '<del>'

    def del_close(self, tokens, idx, options, env):
        return '</del>'

    md.add_render_rule('s_open', del_open)
    md.add_render_rule('s_close', del_close)
