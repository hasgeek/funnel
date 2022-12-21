"""Markdown-it-py plugin to modify output of the footnote plugin."""

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote.index import render_footnote_caption


# FIXME: `self` parameter? Need types
def caption(self, tokens, idx, options, env) -> str:
    output = render_footnote_caption(self, tokens, idx, options, env)
    return output.replace('[', '').replace(']', '')


def footnote_extend_plugin(md: MarkdownIt, **opts) -> None:
    if 'footnote_ref' not in md.get_active_rules()['inline']:
        return
    md.add_render_rule('footnote_caption', caption)
