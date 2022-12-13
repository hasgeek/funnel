"""Markdown-it-py plugin to add language-none class to code fence tokens."""

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML


def fence_extend_plugin(md: MarkdownIt, **opts) -> None:
    def fence(self, tokens, idx, options, env):
        output = RendererHTML.fence(self, tokens, idx, options, env)
        output = output.replace('<pre><code>', '<pre><code class="language-none">')
        return output

    md.add_render_rule('fence', fence)
