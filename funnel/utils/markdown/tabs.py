"""MDIT renderer and helpers for tabs."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import reduce
from typing import ClassVar, Dict, List, Optional, Tuple

__all__ = ['render_tab']


def get_tab_tokens(tokens):
    return [
        {
            'index': i,
            'nesting': token.nesting,
            'info': token.info,
            'key': '-'.join([token.markup, str(token.level)]),
        }
        for i, token in enumerate(tokens)
        if token.type in ('container_tab_open', 'container_tab_close')
    ]


def get_pair(tab_tokens, start=0) -> Optional[Tuple[int, int]]:
    i = 1
    while i < len(tab_tokens):
        if (
            tab_tokens[i]['nesting'] == -1
            and tab_tokens[0]['key'] == tab_tokens[i]['key']
        ):
            break
        i += 1
    if i >= len(tab_tokens):
        return None
    return (start, start + i)


def render_tab(self, tokens, idx, _options, env):
    if 'manager' not in env:
        env['manager'] = TabsManager(get_tab_tokens(tokens))

    node = env['manager'].index(idx)
    if node is None:
        return ''
    if tokens[idx].nesting == 1:
        return node.html_open
    return node.html_close


@dataclass
class TabsetNode:
    start: int
    parent: Optional[TabNode] = None
    children: List[TabNode] = field(default_factory=list)
    _html_tabs: ClassVar[str] = '<ul role="tablist">{items_html}</ul>'
    html_close: ClassVar[str] = '</div>'
    _tabset_id: str = ''

    def flatten(self) -> List[TabNode]:
        tabs = self.children
        for tab in self.children:
            for tabset in tab.children:
                tabs = tabs + tabset.flatten()
        return tabs

    @property
    def html_open(self):
        items_html = ''.join([item.html_tab_item for item in self.children])
        return (
            f'<div id="{self.tabset_id}" class="md-tabset">'
            + self._html_tabs.format(items_html=items_html)
        )

    @property
    def tabset_id(self) -> str:
        return 'md-tabset-' + self._tabset_id

    @tabset_id.setter
    def tabset_id(self, value) -> None:
        self._tabset_id = value


@dataclass
class TabNode:
    start: int
    end: int
    info: str
    key: str
    parent: TabsetNode
    _tab_id: str = ''
    children: List[TabsetNode] = field(default_factory=list)
    _opening: ClassVar[str] = (
        '<div role="tabpanel"{class_attr} id="{tab_id}-panel"'
        + ' aria-labelledby="{tab_id}" tabindex="0">'
    )
    _closing: ClassVar[str] = '</div>'
    _item_html: ClassVar[str] = (
        '<li role="presentation"{class_attr}>'
        + '<a role="tab" href="javascript:void(0)" id="{tab_id}"'
        + ' aria-controls="{tab_id}-panel" {accessibility}>{title}</a></li>'
    )

    def _class_attr(self, classes=None):
        if classes is None:
            classes = []
        classes = classes + self._active_class
        if self.title == '':
            classes.append('no-title')
        return f' class="{" ".join(classes)}"' if len(classes) > 0 else ''

    @property
    def _item_aria(self):
        if self.is_first:
            return ' tabindex="0" aria-selected="true"'
        return ' tabindex="-1" aria-selected="false"'

    def flatten(self) -> List[TabsetNode]:
        tabsets = self.children
        for tabset in self.children:
            for tab in tabset.children:
                tabsets = tabsets + tab.flatten()
        return tabsets

    @property
    def _active_class(self):
        return ['md-tab-active'] if self.is_first else []

    @property
    def title(self):
        tab_title = ' '.join(self.info.strip().split()[1:])
        return tab_title or 'Tab ' + str(self.parent.children.index(self) + 1)

    @property
    def tab_id(self) -> str:
        return 'md-tab-' + self._tab_id

    @tab_id.setter
    def tab_id(self, value) -> None:
        self._tab_id = value

    @property
    def is_first(self) -> bool:
        return self.start == self.parent.start

    @property
    def is_last(self) -> bool:
        return self == self.parent.children[-1]

    @property
    def html_open(self) -> str:
        opening = self._opening.format(
            tab_id=self.tab_id,
            class_attr=self._class_attr(),
        )
        if self.is_first:
            opening = self.parent.html_open + opening
        return opening

    @property
    def html_close(self) -> str:
        return self._closing + (self.parent.html_close if self.is_last else '')

    @property
    def html_tab_item(self):
        return self._item_html.format(
            tab_id=self.tab_id,
            tabset_id=self.parent.tabset_id,
            title=self.title,
            class_attr=self._class_attr(),
            accessibility=self._item_aria,
        )


class TabsManager:
    tabsets: List[TabsetNode]
    _index: Dict[int, TabNode]

    def __init__(self, tab_tokens) -> None:
        self.tabsets: List[TabsetNode] = self.make(tab_tokens)
        self._index = {}
        self.index()

    def make(self, tab_tokens, parent: Optional[TabNode] = None) -> List[TabsetNode]:
        open_index, close_index = 0, len(tab_tokens) - 1
        nodes: List[TabNode] = []
        tabsets: List[TabsetNode] = []
        previous: Optional[TabNode] = None
        while True:
            pairs = get_pair(tab_tokens[open_index : close_index + 1], start=open_index)
            if pairs is None:
                break
            open_index, close_index = pairs
            if (
                previous is None
                or previous.key != tab_tokens[open_index]['key']
                or previous.end + 1 != tab_tokens[open_index]['index']
            ):
                tabset = TabsetNode(tab_tokens[open_index]['index'], parent)
                tabsets.append(tabset)
            node = TabNode(
                start=tab_tokens[open_index]['index'],
                end=tab_tokens[close_index]['index'],
                key=tab_tokens[open_index]['key'],
                info=tab_tokens[open_index]['info'],
                parent=tabset,
            )
            nodes.append(node)
            tabset.children.append(node)
            node.parent = tabset
            node.children = self.make(
                tab_tokens[open_index + 1 : close_index], parent=node
            )
            if close_index + 1 == len(tab_tokens):
                break
            open_index, close_index = close_index + 1, len(tab_tokens) - 1
            previous = node

        return tabsets

    def index(self, start: Optional[int] = None) -> Optional[TabNode]:
        if start is not None:
            try:
                return self._index[start]
            except KeyError:
                return None

        tabsets: List[TabsetNode] = []
        for tabset in self.tabsets:
            tabsets.append(tabset)
            for tab in tabset.children:
                tabsets = tabsets + tab.flatten()
        for i, tabset in enumerate(tabsets):
            tabset.tabset_id = str(i + 1)
        tabs: List[TabNode] = reduce(
            lambda tablist, tabset: tablist + tabset.flatten(), self.tabsets, []
        )
        for i, tab in enumerate(tabs):
            self._index[tab.start] = tab
            self._index[tab.end] = tab
            tab.tab_id = str(i + 1)
        return None
