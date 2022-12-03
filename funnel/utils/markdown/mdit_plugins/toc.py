"""
Markdown-it-py plugin for table of contents.

Ported from the npm package markdown-it-table-of-contents
https://github.com/cmaas/markdown-it-table-of-contents/blob/master/index.js

The algorithm works as follows:
Step 1: Gather all headline tokens from a Markdown document and put them in an array.
Step 2: Turn the flat array into a nested tree, respecting the correct headline level.
Step 3: Turn the nested tree into HTML code.
"""

from functools import reduce
from typing import Dict, List, Optional
import re

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token

from coaster.utils import make_name

__all__ = ['toc_plugin']

defaults: Dict = {
    'include_level': [1, 2, 3, 4, 5, 6],
    'container_class': 'table-of-contents',
    'slugify': lambda x, **options: 'h:' + make_name(x, **options),
    'marker_pattern': r'^\[toc\]',
    'list_type': 'ul',
    'format': lambda content, md: md.render(content),
    'container_header_html': None,
    'container_footer_html': None,
    'transform_link': None,
}


def find_elements(levels: List[int], tokens: List[Token], options: Dict) -> List[Dict]:
    """Find all headline items for the defined levels in a Markdown document."""
    headings = []
    current_heading: Optional[Dict] = None

    for token in tokens:
        if token.type == 'heading_open':
            heading_id = find_existing_id_attr(token)
            level = int(token.tag.lower().replace('h', ''))
            if level in levels:
                current_heading = {'level': level, 'text': None, 'anchor': heading_id}
        elif current_heading is not None and token.type == 'inline':
            text_content = reduce(
                lambda acc, t: acc + t.content,
                [tok for tok in token.children if tok.type in ('text', 'code_inline')],
                '',
            )
            current_heading[  # pylint: disable=[unsupported-assignment-operation]
                'text'
            ] = text_content
            if (
                current_heading['anchor']  # pylint: disable=[unsubscriptable-object]
                is not None
            ):
                current_heading[  # pylint: disable=[unsupported-assignment-operation]
                    'anchor'
                ] = options['slugify'](text_content)
        elif token.type == 'heading_close':
            if current_heading is not None:
                headings.append(current_heading)
            current_heading = None
    return headings


def find_existing_id_attr(token: Token) -> Optional[str]:
    """
    Find an existing id attr on a token.

    Should be a heading_open token, but could be anything really
    provided by markdown-it-anchor or markdown-it-attrs
    """
    for key, val in token.attrs.items():
        if key == 'id':
            return val
    return None


def get_min_level(items: Dict) -> int:
    """Get minimum headline level so that the TOC is nested correctly."""
    return min(item['level'] for item in items)


def add_list_item(
    level: int, text: Optional[str], anchor: Optional[str], root_node: Dict
) -> Dict:
    """Create a TOCItem."""
    item: Dict = {
        'level': level,
        'text': text,
        'anchor': anchor,
        'children': [],
        'parent': root_node,
    }
    root_node['children'].append(item)
    return item


def items_to_tree(items: Dict) -> Dict:
    """Turn list of headline items into a nested tree object representing the TOC."""
    # Create a root node with no text that holds the entire TOC.
    # This won't be rendered, but only its children.
    toc: Dict = {
        'level': get_min_level(items) - 1,
        'anchor': None,
        'text': None,
        'children': [],
        'parent': None,
    }
    # Pointer that tracks the last root item of the current list
    current_root = toc
    # Pointer that tracks the last item
    # (to turn it into a new root node if necessary)
    prev_item = current_root

    for item in items:
        # if level is bigger, take the previous node,
        # add a child list, set current list to this new child list
        if item['level'] > prev_item['level']:
            for _i in range(item['level'] - prev_item['level']):
                current_root = prev_item
                prev_item = add_list_item(item['level'], None, None, current_root)
            prev_item['text'] = item['text']
            prev_item['anchor'] = item['anchor']
        # if level is same, add to the current list
        elif item['level'] == prev_item['level']:
            prev_item = add_list_item(
                item['level'], item['text'], item['anchor'], current_root
            )
        # if level is smaller, set current list to currentlist.parent
        elif item['level'] < prev_item['level']:
            for _i in range(prev_item['level'] - item['level']):
                current_root = current_root['parent']
            prev_item = add_list_item(
                item['level'], item['text'], item['anchor'], current_root
            )
    return toc


def toc_item_to_html(item: Dict, options: Dict, md: MarkdownIt) -> str:
    """Recursively turns a nested tree of tocItems to HTML."""
    html = f"<{options['list_type']}>"
    for child in item['children']:
        li = '<li>'
        anchor = child['anchor']
        if options and options['transform_link']:
            anchor = options['transform_link'](anchor)
        text = options['format'](child['text'], md) if child['text'] is not None else ''
        li = li + (f'<a href="#{anchor}">{text}</a>' if anchor else text)
        li = (
            li
            + (
                toc_item_to_html(child, options, md)
                if len(child['children']) > 0
                else ''
            )
            + '</li>'
        )
        html = html + li
    html = html + f"</{options['list_type']}>"
    return html


def toc_plugin(md: MarkdownIt, **opts):
    opts = {
        **defaults,
        **opts,
    }
    toc_regex = opts['marker_pattern']

    def toc(state: StateInline, silent: bool):
        # Reject if the token does not start with [
        if state.srcCharCode[state.pos] != 0x5B:
            return False
        if silent:
            return False
        if re.match(toc_regex, state.src[state.pos :]) is None:
            return False
        # Build content
        token = state.push('toc_open', 'toc', 1)
        token.markup = '[toc]'
        token = state.push('toc_body', '', 0)
        token = state.push('toc_close', 'toc', -1)

        # Update pos so the parser can continue
        newline = state.src.find('\n', state.pos)
        if newline != -1:
            state.pos = newline
        else:
            state.pos = state.pos + state.posMax + 1
        return True

    def toc_open(self, tokens, idx, options, env):
        open_html = f"<div class=\"{opts['container_class']}\">"
        if opts['container_header_html'] is not None:
            open_html = open_html + opts['container_header_html']
        return open_html

    def toc_close(self, tokens, idx, options, env):
        footer = ''
        if opts['container_footer_html']:
            footer = opts['container_footer_html']
        return footer + '</div>'

    def toc_body(self, tokens, idx, options, env):
        items = find_elements(opts['include_level'], env['gstate'].tokens, opts)
        toc = items_to_tree(items)
        html = toc_item_to_html(toc, opts, md)
        return html

    def grab_state(state: StateInline):
        state.env['gstate'] = state

    md.core.ruler.push('grab_state', grab_state)
    md.add_render_rule('toc_open', toc_open)
    md.add_render_rule('toc_body', toc_body)
    md.add_render_rule('toc_close', toc_close)

    md.inline.ruler.after('emphasis', 'toc', toc)
