"""MDIT plugin to add language-none class to code fence & code block tokens."""

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML


# FIXME: `self` parameter? Need types
def fence(self, tokens, idx, options, env) -> str:
    output = RendererHTML.fence(self, tokens, idx, options, env)
    output = output.replace('<pre><code>', '<pre><code class="language-none">')
    return output


def code_block(self, tokens, idx, options, env) -> str:
    output = RendererHTML.code_block(self, tokens, idx, options, env)
    output = output.replace('<pre><code>', '<pre><code class="language-none">')
    return output


def block_code_extend_plugin(md: MarkdownIt, **opts) -> None:
    """Add CSS class ``language-none`` for code fences with no language identifier."""
    md.add_render_rule('fence', fence)
    md.add_render_rule('code_block', code_block)
