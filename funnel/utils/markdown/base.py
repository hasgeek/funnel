"""Base files for markdown parser."""

from typing import Dict, List, Mapping, Optional, Union, cast, overload

from markdown_it import MarkdownIt
from markupsafe import Markup

from coaster.utils.text import normalize_spaces_multiline, sanitize_html

from .extmap import EXT_LIST, EXT_MAP
from .helpers import DEFAULT_MD_EXT, MARKDOWN_HTML_TAGS

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
    html: bool = False,
    linkify: bool = True,
    valid_tags: Optional[Union[List[str], Mapping[str, List]]] = None,
    extensions: Union[List[str], None] = None,
    extension_configs: Optional[Dict[str, str]] = None,
    # TODO: Extend to accept helpers.EXT_CONFIG_TYPE (Dict)
) -> None:
    ...


@overload
def markdown(
    text: str,
    html: bool = False,
    linkify: bool = True,
    valid_tags: Optional[Union[List[str], Mapping[str, List]]] = None,
    extensions: Union[List[str], None] = None,
    extension_configs: Optional[Dict[str, str]] = None,
    # TODO: Extend to accept helpers.EXT_CONFIG_TYPE (Dict)
) -> Markup:
    ...


def markdown(
    text: Optional[str],
    html: bool = False,
    linkify: bool = True,
    valid_tags: Optional[Union[List[str], Mapping[str, List]]] = None,
    extensions: Union[List[str], None] = None,
    extension_configs: Optional[Dict[str, str]] = None,
    # TODO: Extend to accept helpers.EXT_CONFIG_TYPE (Dict)
) -> Optional[Markup]:
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

    if extensions is None:
        extensions = DEFAULT_MD_EXT

    for e in extensions:
        e = cast(str, e)
        if e in EXT_LIST and (not html or (html and EXT_MAP[e]['when_html'])):
            ext_config = EXT_MAP[e]['configs'][EXT_MAP[e]['default_config']]
            if extension_configs is not None:
                if (
                    e in extension_configs
                    and extension_configs[e] in EXT_MAP[e]['configs']
                ):
                    ext_config = EXT_MAP[e]['configs'][extension_configs[e]]
            md.use(EXT_MAP[e]['ext'], **ext_config)

    if html:
        return Markup(sanitize_html(md.render(text), valid_tags=valid_tags))
    return Markup(md.render(text))