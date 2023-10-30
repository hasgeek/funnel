"""Markdown escaper."""

from __future__ import annotations

import re
import string
from collections.abc import Callable, Iterable, Mapping
from functools import wraps
from typing import Any, Concatenate, SupportsIndex, TypeVar
from typing_extensions import ParamSpec, Protocol, Self

__all__ = ['HasMarkdown', 'MarkdownString', 'markdown_escape']


_P = ParamSpec('_P')
_ListOrDict = TypeVar('_ListOrDict', list, dict)


class HasMarkdown(Protocol):
    """Protocol for a class implementing :meth:`__markdown__`."""

    def __markdown__(self) -> str:
        """Return a Markdown string."""


#: Based on the ASCII punctuation list in the CommonMark spec at
#: https://spec.commonmark.org/0.30/#backslash-escapes
markdown_escape_re = re.compile(r"""([\[\\\]{|}\(\)`~!@#$%^&*=+;:'"<>/,.?_-])""")
#: Unescape regex has a `\` prefix and the same characters
markdown_unescape_re = re.compile(r"""\\([\[\\\]{|}\(\)`~!@#$%^&*=+;:'"<>/,.?_-])""")


class _MarkdownEscapeFormatter(string.Formatter):
    """Support class for :meth:`MarkdownString.format`."""

    __slots__ = ('escape',)

    def __init__(self, escape: Callable[[Any], MarkdownString]) -> None:
        self.escape = escape
        super().__init__()

    def format_field(self, value: Any, format_spec: str) -> str:
        if hasattr(value, '__markdown_format__'):
            rv = value.__markdown_format__(format_spec)
        elif hasattr(value, '__markdown__'):
            if format_spec:
                raise ValueError(
                    f"Format specifier {format_spec} given, but {type(value)} does not"
                    " define __markdown_format__. A class that defines __markdown__"
                    " must define __markdown_format__ to work with format specifiers."
                )
            rv = value.__markdown__()
        else:
            # We need to make sure the format spec is str here as
            # otherwise the wrong callback methods are invoked.
            rv = string.Formatter.format_field(self, value, str(format_spec))
        return str(self.escape(rv))


class _MarkdownEscapeHelper:
    """Helper for :meth:`MarkdownString.__mod__`."""

    __slots__ = ('obj', 'escape')

    def __init__(self, obj: Any, escape: Callable[[Any], MarkdownString]) -> None:
        self.obj = obj
        self.escape = escape

    def __getitem__(self, item: Any) -> Self:
        return self.__class__(self.obj[item], self.escape)

    def __str__(self) -> str:
        return str(self.escape(self.obj))

    def __repr__(self) -> str:
        return str(self.escape(repr(self.obj)))

    def __int__(self) -> int:
        return int(self.obj)

    def __float__(self) -> float:
        return float(self.obj)


def _escape_argspec(
    obj: _ListOrDict, iterable: Iterable[Any], escape: Callable[[Any], MarkdownString]
) -> _ListOrDict:
    """Escape all arguments."""
    for key, value in iterable:
        if isinstance(value, str) or hasattr(value, '__markdown__'):
            obj[key] = escape(value)

    return obj


def _simple_escaping_wrapper(
    func: Callable[Concatenate[str, _P], str]
) -> Callable[Concatenate[MarkdownString, _P], MarkdownString]:
    @wraps(func)
    def wrapped(
        self: MarkdownString, *args: _P.args, **kwargs: _P.kwargs
    ) -> MarkdownString:
        arg_list = _escape_argspec(list(args), enumerate(args), self.escape)
        _escape_argspec(kwargs, kwargs.items(), self.escape)
        return self.__class__(func(self, *arg_list, **kwargs))

    return wrapped


class MarkdownString(str):
    """Markdown string, implements a __markdown__ method."""

    __slots__ = ()

    def __new__(
        cls, base: Any = '', encoding: str | None = None, errors: str = 'strict'
    ) -> MarkdownString:
        if hasattr(base, '__markdown__'):
            base = base.__markdown__()

        if encoding is None:
            return super().__new__(cls, base)

        return super().__new__(cls, base, encoding, errors)

    def __markdown__(self) -> Self:
        """Return a markdown embed-compatible string."""
        return self

    def __markdown_format__(self, format_spec: str) -> Self:
        if format_spec:
            # MarkdownString cannot support format_spec because any manipulation may
            # remove an escape char, causing downstream damage with unwanted formatting
            raise ValueError("Unsupported format specification for MarkdownString.")

        return self

    def unescape(self) -> str:
        """Unescape the string."""
        return markdown_unescape_re.sub(r'\1', str(self))

    @classmethod
    def escape(cls, text: str | HasMarkdown, silent: bool = True) -> Self:
        """Escape a string, for internal use only. Use :func:`markdown_escape`."""
        if silent and text is None:
            return cls('')  # type: ignore[unreachable]
        if hasattr(text, '__markdown__'):
            return cls(text.__markdown__())
        return cls(markdown_escape_re.sub(r'\\\1', text))

    # These additional methods are borrowed from the implementation in markupsafe

    def __add__(self, other: str | HasMarkdown) -> Self:
        if isinstance(other, str) or hasattr(other, '__markdown__'):
            return self.__class__(super().__add__(self.escape(other)))

        return NotImplemented

    def __radd__(self, other: str | HasMarkdown) -> Self:
        if isinstance(other, str) or hasattr(other, '__markdown__'):
            return self.escape(other).__add__(self)

        return NotImplemented

    def __mul__(self, num: SupportsIndex) -> Self:
        if isinstance(num, int):
            return self.__class__(super().__mul__(num))

        return NotImplemented

    __rmul__ = __mul__

    def __mod__(self, arg: Any) -> Self:
        """Apply legacy `str % arg(s)` formatting."""
        if isinstance(arg, tuple):
            # a tuple of arguments, each wrapped
            arg = tuple(_MarkdownEscapeHelper(x, self.escape) for x in arg)
        elif hasattr(type(arg), '__getitem__') and not isinstance(arg, str):
            # a mapping of arguments, wrapped
            arg = _MarkdownEscapeHelper(arg, self.escape)
        else:
            # a single argument, wrapped with the helper and a tuple
            arg = (_MarkdownEscapeHelper(arg, self.escape),)

        return self.__class__(super().__mod__(arg))

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({super().__repr__()})'

    def join(self, iterable: Iterable[str | HasMarkdown]) -> Self:
        return self.__class__(super().join(map(self.escape, iterable)))

    join.__doc__ = str.join.__doc__

    def split(  # type: ignore[override]
        self, sep: str | None = None, maxsplit: SupportsIndex = -1
    ) -> list[Self]:
        return [self.__class__(v) for v in super().split(sep, maxsplit)]

    split.__doc__ = str.split.__doc__

    def rsplit(  # type: ignore[override]
        self, sep: str | None = None, maxsplit: SupportsIndex = -1
    ) -> list[Self]:
        return [self.__class__(v) for v in super().rsplit(sep, maxsplit)]

    rsplit.__doc__ = str.rsplit.__doc__

    def splitlines(  # type: ignore[override]
        self, keepends: bool = False
    ) -> list[Self]:
        return [self.__class__(v) for v in super().splitlines(keepends)]

    splitlines.__doc__ = str.splitlines.__doc__

    __getitem__ = _simple_escaping_wrapper(str.__getitem__)  # type: ignore[assignment]
    capitalize = _simple_escaping_wrapper(str.capitalize)  # type: ignore[assignment]
    title = _simple_escaping_wrapper(str.title)  # type: ignore[assignment]
    lower = _simple_escaping_wrapper(str.lower)  # type: ignore[assignment]
    upper = _simple_escaping_wrapper(str.upper)  # type: ignore[assignment]
    replace = _simple_escaping_wrapper(str.replace)  # type: ignore[assignment]
    ljust = _simple_escaping_wrapper(str.ljust)  # type: ignore[assignment]
    rjust = _simple_escaping_wrapper(str.rjust)  # type: ignore[assignment]
    lstrip = _simple_escaping_wrapper(str.lstrip)  # type: ignore[assignment]
    rstrip = _simple_escaping_wrapper(str.rstrip)  # type: ignore[assignment]
    center = _simple_escaping_wrapper(str.center)  # type: ignore[assignment]
    strip = _simple_escaping_wrapper(str.strip)  # type: ignore[assignment]
    translate = _simple_escaping_wrapper(str.translate)  # type: ignore[assignment]
    expandtabs = _simple_escaping_wrapper(str.expandtabs)  # type: ignore[assignment]
    swapcase = _simple_escaping_wrapper(str.swapcase)  # type: ignore[assignment]
    zfill = _simple_escaping_wrapper(str.zfill)  # type: ignore[assignment]
    casefold = _simple_escaping_wrapper(str.casefold)  # type: ignore[assignment]

    removeprefix = _simple_escaping_wrapper(  # type: ignore[assignment]
        str.removeprefix
    )
    removesuffix = _simple_escaping_wrapper(  # type: ignore[assignment]
        str.removesuffix
    )

    def partition(self, sep: str) -> tuple[Self, Self, Self]:
        left, sep, right = super().partition(self.escape(sep))
        cls = self.__class__
        return cls(left), cls(sep), cls(right)

    partition.__doc__ = str.partition.__doc__

    def rpartition(self, sep: str) -> tuple[Self, Self, Self]:
        left, sep, right = super().rpartition(self.escape(sep))
        cls = self.__class__
        return cls(left), cls(sep), cls(right)

    rpartition.__doc__ = str.rpartition.__doc__

    def format(self, *args: Any, **kwargs: Any) -> Self:  # noqa: A003
        formatter = _MarkdownEscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, args, kwargs))

    format.__doc__ = str.format.__doc__

    # pylint: disable=redefined-builtin
    def format_map(
        self, map: Mapping[str, Any]  # type: ignore[override]  # noqa: A002
    ) -> Self:
        formatter = _MarkdownEscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, (), map))

    format_map.__doc__ = str.format_map.__doc__


def markdown_escape(text: str) -> MarkdownString:
    """
    Escape all Markdown formatting characters and strip whitespace at ends.

    As per the CommonMark spec, all ASCII punctuation can be escaped with a backslash
    and compliant parsers will then render the punctuation mark as a literal character.
    However, escaping any other character will cause the backslash to be rendered. This
    escaper therefore targets only ASCII punctuation characters listed in the spec.

    Edge whitespace is significant in Markdown:

    * Four spaces at the start will initiate a code block
    * Two spaces at the end will cause a line-break in non-GFM Markdown

    The space and tab characters cannot be escaped, and replacing spaces with &nbsp; is
    not suitable because non-breaking spaces affect HTML rendering, specifically the
    CSS ``white-space: normal`` sequence collapsing behaviour. Since there is no way to
    predict adjacent whitespace when this escaped variable is placed in a Markdown
    document, it is safest to strip all edge whitespace.

    ..note::
        This function strips edge whitespace and calls :meth:`MarkdownString.escape`,
        and should be preferred over calling :meth:`MarkdownString.escape` directly.
        That classmethod is internal to :class:`MarkdownString`.

    :returns: Escaped text as an instance of :class:`MarkdownString`, to avoid
        double-escaping
    """
    return MarkdownString.escape(text.strip())
