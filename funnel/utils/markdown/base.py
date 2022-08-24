"""Base files for markdown parser."""

from copy import deepcopy

from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins import anchors, footnote, tasklists

from coaster.utils import make_name
from coaster.utils.text import VALID_TAGS, normalize_spaces_multiline, sanitize_html

MARKDOWN_HTML_TAGS = deepcopy(VALID_TAGS)

# --- Standard extensions --------------------------------------------------------------
# FOR CUT 2
# TODO: caret, tilde:
#       ^^ins^^, ^sup^ dont work OOTB. ~~del~~ uses <s/>, not <del/>.
#       Can port 1st 2 from markdown-it-[sup|ins] and implement del separately.
#       Port from https://github.com/markdown-it/markdown-it-sup
#       Port from https://github.com/markdown-it/markdown-it-ins
# TODO: emoji, (mark => highlight, inlinehilite)
#       Port from https://github.com/markdown-it/markdown-it-emoji
#       Port from https://github.com/markdown-it/markdown-it-mark
#       Evaluate:
#       https://www.npmjs.com/search?q=highlight%20keywords%3Amarkdown-it-plugin


default_markdown_extensions_html = {
    'footnote': footnote.footnote_plugin,
}

default_markdown_extensions = {
    'footnote': footnote.footnote_plugin,
    'heading_anchors': anchors.anchors_plugin,
    'tasklists': tasklists.tasklists_plugin,
}

default_markdown_extension_configs = {
    'footnote': {},
    'heading_anchors': {
        'min_level': 1,
        'max_level': 3,
        'slug_func': make_name,
        'permalink': True,
    },
    'tasklists': {'enabled': False, 'label': False, 'label_after': False},
}


# --- Markdown processor ---------------------------------------------------------------

# pylint: disable=too-many-arguments
def markdown(
    text,
    html=False,
    linkify=True,
    valid_tags=None,
    extensions=None,
    extension_configs=None,
):
    """
    Markdown parser compliant with Commonmark+GFM.

    :param bool html: Allow known-safe HTML tags in text
        (this disables code syntax highlighting and task lists)
    :param bool linkify: Whether to convert naked URLs into links
    :param dict valid_tags: Valid tags and attributes if HTML is allowed
    :param list extensions: List of Markdown extensions to be enabled
    :param dict extension_configs: Config for Markdown extensions
    """
    if text is None:
        return None
    if valid_tags is None:
        valid_tags = MARKDOWN_HTML_TAGS

    # For the first cut release,
    # ignore extensions and extension configs passed by method caller
    if html:
        extensions = default_markdown_extensions_html
    else:
        extensions = default_markdown_extensions
    extension_configs = default_markdown_extension_configs

    # Replace invisible characters with spaces
    text = normalize_spaces_multiline(text)

    md = MarkdownIt(
        'gfm-like',
        {
            'breaks': True,
            'html': html,
            'linkify': linkify,
            'typographer': True,
        },
    ).enable(['smartquotes'])

    for (key, ext) in extensions.items():
        md.use(ext, **extension_configs[key])

    if html:
        return Markup(sanitize_html(md.render(text), valid_tags=valid_tags))
    return Markup(md.render(text))
