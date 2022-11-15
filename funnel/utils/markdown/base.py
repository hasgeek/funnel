"""Base files for markdown parser."""
# pylint: disable=too-many-arguments

from typing import List, Optional, Type, Union, overload
import json

from markdown_it import MarkdownIt
from markupsafe import Markup

from coaster.utils.text import normalize_spaces_multiline

from .profiles import MarkdownProfile, plugin_configs, plugins, profiles

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
def markdown(text: None, profile: Union[str, Type[MarkdownProfile]]) -> None:
    ...


@overload
def markdown(text: str, profile: Union[str, Type[MarkdownProfile]]) -> Markup:
    ...


def markdown(
    text: Optional[str], profile: Union[str, Type[MarkdownProfile]]
) -> Optional[Markup]:
    """
    Markdown parser compliant with Commonmark+GFM using markdown-it-py.

    :param str|dict profile: Config profile to use
    """
    if text is None:
        return None

    # Replace invisible characters with spaces
    text = normalize_spaces_multiline(text)

    if isinstance(profile, str):
        try:
            _profile = profiles[profile]
        except KeyError as exc:
            raise KeyError(
                f'Wrong markdown config profile "{profile}". Check name.'
            ) from exc
    elif issubclass(profile, MarkdownProfile):
        _profile = profile
    else:
        raise TypeError(
            'Wrong type - profile has to be either str or a subclass of MarkdownProfile'
        )

    # TODO: Move MarkdownIt instance generation to profile class method
    md = MarkdownIt(*_profile.args)

    if md.linkify is not None:
        md.linkify.set({'fuzzy_link': False, 'fuzzy_email': False})

    for action in ['enableOnly', 'enable', 'disable']:
        if action in _profile.post_config:
            getattr(md, action)(
                _profile.post_config[action]  # type: ignore[literal-required]
            )

    for e in _profile.plugins:
        try:
            ext = plugins[e]
        except KeyError as exc:
            raise KeyError(
                f'Wrong markdown-it-py plugin key "{e}". Check name.'
            ) from exc
        md.use(ext, **plugin_configs.get(e, {}))

    # type: ignore[arg-type]
    return Markup(getattr(md, _profile.render_with)(text))


def _print_rules(md: MarkdownIt, active: Optional[str] = None):
    """Debug function to be removed before merge."""
    rules = {'all_rules': md.get_all_rules(), 'active_rules': {}}
    for p, pr in profiles.items():
        m = MarkdownIt(*pr.args)
        if m.linkify is not None:
            m.linkify.set({'fuzzy_link': False, 'fuzzy_email': False})
        for action in ['enableOnly', 'enable', 'disable']:
            if action in pr.post_config:
                getattr(m, action)(
                    pr.post_config[action]  # type: ignore[literal-required]
                )
        for e in pr.plugins:
            try:
                ext = plugins[e]
            except KeyError as exc:
                raise KeyError(
                    f'Wrong markdown-it-py plugin key "{e}". Check name.'
                ) from exc
            m.use(ext, **plugin_configs.get(e, {}))
        rules['active_rules'][p] = m.get_active_rules()
    if active is not None:
        print(json.dumps(rules['active_rules'][active], indent=2))  # noqa: T201
    else:
        print(json.dumps(rules, indent=2))  # noqa: T201
