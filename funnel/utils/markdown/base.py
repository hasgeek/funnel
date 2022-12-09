"""Markdown parser and config profiles."""
# pylint: disable=too-many-arguments

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypedDict,
    Union,
    overload,
)
import json

from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins import anchors, footnote, tasklists
from typing_extensions import NotRequired

from coaster.utils import make_name
from coaster.utils.text import normalize_spaces_multiline

from .mdit_plugins import (  # toc_plugin,
    del_plugin,
    embeds_plugin,
    ins_plugin,
    mark_plugin,
    sub_plugin,
    sup_plugin,
)

__all__ = ['markdown', 'markdown_plugins', 'markdown_plugin_config', 'MarkdownProfile']

default_markdown_extensions: List[str] = ['footnote', 'heading_anchors', 'tasklists']

markdown_plugins: Dict[str, Callable] = {
    'footnote': footnote.footnote_plugin,
    'heading_anchors': anchors.anchors_plugin,
    'tasklists': tasklists.tasklists_plugin,
    'ins': ins_plugin,
    'del': del_plugin,
    'sub': sub_plugin,
    'sup': sup_plugin,
    'mark': mark_plugin,
    'markmap': embeds_plugin,
    'vega-lite': embeds_plugin,
    'mermaid': embeds_plugin,
    # 'toc': toc_plugin,
}

markdown_plugin_config: Dict[str, Dict[str, Any]] = {
    'heading_anchors': {
        'min_level': 1,
        'max_level': 3,
        'slug_func': lambda x, **options: 'h:' + make_name(x, **options),
        'permalink': True,
    },
    'tasklists': {'enabled': True, 'label': True, 'label_after': False},
    'markmap': {'name': 'markmap'},
    'vega-lite': {'name': 'vega-lite'},
    'mermaid': {'name': 'mermaid'},
}


class PostConfig(TypedDict):
    disable: NotRequired[List[str]]
    enable: NotRequired[List[str]]
    enableOnly: NotRequired[List[str]]  # noqa: N815


class MarkdownProfile:
    """Markdown config metadata in a non-callable class structure."""

    # Registry of named sub-classes
    registry: Dict[str, Type[MarkdownProfile]] = {}

    args: Tuple[str, Mapping] = (
        'commonmark',
        {
            'html': False,
            'breaks': True,
        },
    )
    plugins: List[str] = []
    post_config: PostConfig = {}
    render_with: str = 'render'

    linkify_fuzzy_link: bool = False
    linkify_fuzzy_email: bool = False

    def __new__(cls):
        raise RuntimeError("Markdown profiles cannot be instantiated")

    def __init_subclass__(cls, name: str) -> None:
        if name in MarkdownProfile.registry:
            raise TypeError(f"MarkdownProfile '{name}' already exists")
        MarkdownProfile.registry[name] = cls
        super().__init_subclass__()

    # @classmethod
    # def markdown(cls, *args, **kwargs)


class MarkdownProfileBasic(MarkdownProfile, name='basic'):
    pass


class MarkdownProfileDocument(MarkdownProfile, name='document'):
    args: Tuple[str, Mapping] = (
        'gfm-like',
        {
            'html': False,
            'linkify': True,
            'typographer': True,
            'breaks': True,
        },
    )
    plugins: List[str] = [
        'footnote',
        'heading_anchors',
        'tasklists',
        'ins',
        'del',
        'sub',
        'sup',
        'mark',
        'markmap',
        'vega-lite',
        'mermaid',
        # 'toc',
    ]
    post_config: PostConfig = {'enable': ['smartquotes']}


class MarkdownProfileInline(MarkdownProfile, name='inline'):
    args: Tuple[str, Mapping] = (
        'zero',
        {
            'html': False,
        },
    )
    post_config: PostConfig = {
        'enable': [
            'emphasis',
            'backticks',
        ],
    }
    render_with: str = 'renderInline'


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

    :param profile: Config profile to use
    """
    if text is None:
        return None

    # Replace invisible characters with spaces
    text = normalize_spaces_multiline(text)

    if isinstance(profile, str):
        try:
            profile = MarkdownProfile.registry[profile]
        except KeyError as exc:
            raise KeyError(f"Unknown Markdown config profile '{profile}'") from exc

    # TODO: Move MarkdownIt instance generation to profile class method
    md = MarkdownIt(*profile.args)

    if md.linkify is not None:
        md.linkify.set(
            {
                'fuzzy_link': profile.linkify_fuzzy_link,
                'fuzzy_email': profile.linkify_fuzzy_email,
            }
        )

    for action in ['enableOnly', 'enable', 'disable']:
        if action in profile.post_config:
            getattr(md, action)(
                profile.post_config[action]  # type: ignore[literal-required]
            )

    for e in profile.plugins:
        try:
            ext = markdown_plugins[e]
        except KeyError as exc:
            raise KeyError(
                f'Wrong markdown-it-py plugin key "{e}". Check name.'
            ) from exc
        md.use(ext, **markdown_plugin_config.get(e, {}))

    # type: ignore[arg-type]
    return Markup(getattr(md, profile.render_with)(text))


def _print_rules(md: MarkdownIt, active: Optional[str] = None):
    """Debug function to be removed before merge."""
    rules = {'all_rules': md.get_all_rules(), 'active_rules': {}}
    for p, pr in MarkdownProfile.registry.items():
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
                ext = markdown_plugins[e]
            except KeyError as exc:
                raise KeyError(
                    f'Wrong markdown-it-py plugin key "{e}". Check name.'
                ) from exc
            m.use(ext, **markdown_plugin_config.get(e, {}))
        rules['active_rules'][p] = m.get_active_rules()
    if active is not None:
        print(json.dumps(rules['active_rules'][active], indent=2))  # noqa: T201
    else:
        print(json.dumps(rules, indent=2))  # noqa: T201
