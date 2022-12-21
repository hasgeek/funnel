"""Markdown-it-py plugin to replace <s> with <del> for ~~."""

from markdown_it import MarkdownIt

__all__ = ['del_plugin']


# FIXME: `self` parameter? Need types
def del_open(self, tokens, idx, options, env) -> str:
    return '<del>'


def del_close(self, tokens, idx, options, env) -> str:
    return '</del>'


def del_plugin(md: MarkdownIt) -> None:
    """Render ``~~text~~`` markup with a HTML ``<del>`` tag."""
    md.add_render_rule('s_open', del_open)
    md.add_render_rule('s_close', del_close)
