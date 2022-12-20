"""MDIT plugin to add language-none class to code fence & code block tokens."""

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML


def block_code_extend_plugin(md: MarkdownIt, **opts) -> None:
    def fence(self, tokens, idx, options, env):
        output = RendererHTML.fence(self, tokens, idx, options, env)
        output = output.replace('<pre><code>', '<pre><code class="language-none">')
        return output

    md.add_render_rule('fence', fence)

    def code_block(self, tokens, idx, options, env):
        output = RendererHTML.code_block(self, tokens, idx, options, env)
        output = output.replace('<pre><code>', '<pre><code class="language-none">')
        return output

    md.add_render_rule('code_block', code_block)
