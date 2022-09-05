"""Base files for markdown parser."""

from typing import Dict, List, Optional, Union, overload

from markdown_it import MarkdownIt
from markupsafe import Markup

from coaster.utils.text import normalize_spaces_multiline

from .extmap import markdown_extensions
from .helpers import MDExtDefaults

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


# --- Markdown processor ---------------------------------------------------------------

# pylint: disable=too-many-arguments
@overload
def markdown(
    text: None,
    linkify: bool = True,
    extensions: Union[List[str], None] = None,
    extension_configs: Optional[Dict[str, str]] = None,
    # TODO: Extend to accept helpers.EXT_CONFIG_TYPE (Dict)
) -> None:
    ...


@overload
def markdown(
    text: str,
    linkify: bool = True,
    extensions: Union[List[str], None] = None,
    extension_configs: Optional[Dict[str, str]] = None,
    # TODO: Extend to accept helpers.EXT_CONFIG_TYPE (Dict)
) -> Markup:
    ...


def markdown(
    text: Optional[str],
    linkify: bool = True,
    extensions: Union[List[str], None] = None,
    extension_configs: Optional[Dict[str, str]] = None,
    # TODO: Extend to accept helpers.EXT_CONFIG_TYPE (Dict)
) -> Optional[Markup]:
    """
    Markdown parser compliant with Commonmark+GFM using markdown-it-py.

    :param bool linkify: Whether to convert naked URLs into links
    :param list extensions: List of Markdown extensions to be enabled
    :param dict extension_configs: Config for Markdown extensions
    """
    if text is None:
        return None

    # Replace invisible characters with spaces
    text = normalize_spaces_multiline(text)

    md = MarkdownIt(
        'gfm-like',
        {
            'breaks': True,
            'linkify': linkify,
            'typographer': True,
        },
    ).enable(['smartquotes'])

    md.linkify.set({'fuzzy_link': False, 'fuzzy_email': False})

    if extensions is None:
        extensions = MDExtDefaults

    for e in extensions:
        if e in markdown_extensions:
            ext_config = markdown_extensions[e].default_config
            if extension_configs is not None and e in extension_configs:
                ext_config = markdown_extensions[e].config(extension_configs[e])
            md.use(markdown_extensions[e].ext, **ext_config)

    return Markup(md.render(text))
