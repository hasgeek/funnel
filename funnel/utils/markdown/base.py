"""Base files for markdown parser."""
# pylint: disable=too-many-arguments

from typing import List, Optional, overload

from markdown_it import MarkdownIt
from markupsafe import Markup

from coaster.utils.text import normalize_spaces_multiline

from .profiles import plugin_configs, plugins, profiles

__all__ = ['markdown']

default_markdown_extensions: List[str] = ['footnote', 'heading_anchors', 'tasklists']

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


@overload
def markdown(text: None, profile: str = 'proposal') -> None:
    ...


@overload
def markdown(text: str, profile: str = 'proposal') -> Markup:
    ...


def markdown(text: Optional[str], profile: str = 'proposal') -> Optional[Markup]:
    """
    Markdown parser compliant with Commonmark+GFM using markdown-it-py.

    :param bool profile: Config profile to use
    """
    if text is None:
        return None

    # Replace invisible characters with spaces
    text = normalize_spaces_multiline(text)

    if profile not in profiles:
        raise KeyError(f'Wrong markdown config profile "{profile}". Check name.')

    args = profiles[profile].get('args', ())

    md = MarkdownIt(*args)

    funnel_config = profiles[profile].get('funnel_config', {})

    if md.linkify is not None:
        md.linkify.set({'fuzzy_link': False, 'fuzzy_email': False})

    for action in ['enable', 'disable']:
        if action in funnel_config:
            md.enable(funnel_config[action])

    for e in profiles[profile].get('plugins', []):
        try:
            ext = plugins[e]
        except KeyError as exc:
            raise KeyError(
                f'Wrong markdown-it-py plugin key "{e}". Check name.'
            ) from exc
        md.use(ext, **plugin_configs.get(e, {}))

    return Markup(md.render(text))  # type: ignore[arg-type]
