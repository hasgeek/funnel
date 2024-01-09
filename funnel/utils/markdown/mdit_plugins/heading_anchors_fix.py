"""MDIT plugin to modify the token stream output of mdit-py-plugin heading-anchors."""

from __future__ import annotations

from typing import Any

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token

__all__ = ['heading_anchors_fix_plugin']


def heading_anchors_fix(state: StateCore) -> None:
    prev_token: Token | None = None

    for token in state.tokens:
        if prev_token is None:
            prev_token = token
            continue
        if token.type == 'inline' and prev_token.type == 'heading_open':
            tree = token.children
            if tree is not None:
                header_anchor_index = 0
                for inline_token in tree:
                    if (
                        inline_token.type == 'link_open'
                        and inline_token.attrGet('class') == 'header-anchor'
                    ):
                        break
                    header_anchor_index += 1
                if header_anchor_index < len(tree):
                    popped = tree.pop(header_anchor_index)
                    tree.insert(0, popped)
                    anchor_index = 1
                    while anchor_index < len(tree) - 1:
                        node = tree[anchor_index]
                        if node.type in ['link_open', 'link_close']:
                            tree.pop(anchor_index)
                        else:
                            anchor_index += 1
                    tree[0].attrs.pop('class')
                    tree.pop(len(tree) - 2)
        prev_token = token


def heading_anchors_fix_plugin(md: MarkdownIt, **opts: Any) -> None:
    if 'anchor' in md.get_active_rules()['core']:
        md.core.ruler.after('anchor', 'heading_anchors_fix', heading_anchors_fix)
