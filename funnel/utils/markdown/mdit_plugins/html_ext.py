"""Markdown-it-py plugin to sanitize HTML."""

from __future__ import annotations

from typing import List, Mapping
import re

from markdown_it import MarkdownIt
from markdown_it.common.html_re import attr_name, attribute
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token

from coaster.utils.text import sanitize_html

ATTRIBUTE_RE = re.compile(attribute)
ATTR_NAME_RE = re.compile(attr_name)

VALID_TAGS: Mapping[str, List[str]] = {
    'a': [
        'href',
        'title',
        'target',
        'rel',
    ],  # Disallow - vulnerable to javascript security issues
    'abbr': ['title'],
    'b': [],  # Disallow
    'br': [],  # Disallow
    'blockquote': [],  # Disallow
    'cite': [],
    'code': [],
    'dd': [],
    'del': [],
    'dl': [],
    'dt': [],
    'em': [],
    'h3': [],  # Disallow
    'h4': [],  # Disallow
    'h5': [],  # Disallow
    'h6': [],  # Disallow
    'hr': [],
    'i': [],  # Disallow
    'img': ['src', 'width', 'height', 'align', 'alt'],  # Disallow - security
    'ins': [],
    'li': [],  # Disallow
    'mark': [],
    'p': [],  # Disallow
    'pre': [],  # Disallow
    'ol': ['start', 'type'],  # Disallow
    'strong': [],
    'sup': [],
    'sub': [],
    'ul': [],  # Disallow
    'table': ['align', 'bgcolor', 'border', 'cellpadding', 'cellspacing', 'width'],
    'caption': [],
    'col': ['align', 'char', 'charoff'],
    'colgroup': ['align', 'span', 'cols', 'char', 'charoff', 'width'],
    'tbody': ['align', 'char', 'charoff', 'valign'],
    'td': ['align', 'char', 'charoff', 'colspan', 'rowspan', 'valign'],
    'tfoot': ['align', 'char', 'charoff', 'valign'],
    'th': ['align', 'char', 'charoff', 'colspan', 'rowspan', 'valign'],
    'thead': ['align', 'char', 'charoff', 'valign'],
    'tr': ['align', 'char', 'charoff', 'valign'],
    'address': [],
    'article': [],
    'aside': [],
    'details': [],
    'summary': [],
    'figcaption': [],
    'figure': [],
}


def get_url(md: MarkdownIt, link):
    match = md.linkify.match(link)
    if (
        match
        and len(match) == 1
        and match[0].index == 0
        and match[0].last_index == len(link)
    ):
        return match[0].url
    return None


def sanitize_inline_token(token: Token):
    is_closing = token.content.startswith('</')
    tag = (
        token.content.replace('<', '').replace('>', '').replace('/', '').strip().lower()
    )
    if not is_closing:
        tag = tag.split(' ')[0]
    if tag not in VALID_TAGS:
        token.type = 'text'
    elif not is_closing:
        attribs = [
            attrib
            for attrib in ATTRIBUTE_RE.findall(token.content)
            if ATTR_NAME_RE.findall(attrib)[0] in VALID_TAGS[tag]
        ]
        token.content = '<' + tag + ''.join(attribs) + '>'


def sanitize_tokens(tokens: List[Token]):
    token: Token
    for token in tokens:
        if token.type == 'html_block':
            token.content = str(
                sanitize_html(token.content, VALID_TAGS, strip=False, linkify=True)
            ).replace(
                '<code>',
                '<code class="language-none">',
            )
        elif token.type == 'html_inline':
            sanitize_inline_token(token)
        if token.children is not None:
            sanitize_tokens(token.children)


def sanitize_content(state: StateInline, silent=True):
    sanitize_tokens(state.tokens)


def html_extend_plugin(md: MarkdownIt, **options) -> None:
    md.core.ruler.after('linkify', 'sanitize_html', sanitize_content)
