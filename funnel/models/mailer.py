"""Mailer models."""

from __future__ import annotations

import re
from collections.abc import Collection, Iterator
from datetime import datetime
from enum import IntEnum
from typing import Any
from uuid import UUID

from flask import request
from markupsafe import Markup, escape
from premailer import transform as email_transform
from sqlalchemy.orm import defer

from coaster.utils import MARKDOWN_HTML_TAGS, buid, md5sum, newsecret

from .. import __
from ..utils.markdown import MarkdownString, markdown_mailer
from ..utils.mustache import mustache_md
from . import (
    BaseNameMixin,
    BaseScopedIdMixin,
    DynamicMapped,
    Mapped,
    Model,
    db,
    relationship,
    sa,
)
from .account import Account
from .helpers import reopen
from .types import jsonb

__all__ = [
    'MailerState',
    'Mailer',
    'MailerDraft',
    'MailerRecipient',
]

NAMESPLIT_RE = re.compile(r'[\W\.]+')

EMAIL_TAGS = dict(MARKDOWN_HTML_TAGS)
for _key in EMAIL_TAGS:
    EMAIL_TAGS[_key].append('class')
    EMAIL_TAGS[_key].append('style')


class MailerState(IntEnum):
    """Send state for :class:`Mailer`."""

    DRAFT = 0
    QUEUED = 1
    SENDING = 2
    SENT = 3

    __titles__ = {
        DRAFT: __("Draft"),
        QUEUED: __("Queued"),
        SENDING: __("Sending"),
        SENT: __("Sent"),
    }

    def __init__(self, value: int) -> None:
        self.title = self.__titles__[value]


class Mailer(BaseNameMixin, Model):
    """A mailer sent via email to multiple recipients."""

    __tablename__ = 'mailer'

    user_uuid: Mapped[UUID] = sa.orm.mapped_column(sa.ForeignKey('account.uuid'))
    user: Mapped[Account] = relationship(Account, back_populates='mailers')
    status: Mapped[int] = sa.orm.mapped_column(
        sa.Integer, nullable=False, default=MailerState.DRAFT
    )
    _fields: Mapped[str] = sa.orm.mapped_column(
        'fields', sa.UnicodeText, nullable=False, default=''
    )
    trackopens: Mapped[bool] = sa.orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    stylesheet: Mapped[str] = sa.orm.mapped_column(
        sa.UnicodeText, nullable=False, default=''
    )
    _cc: Mapped[str] = sa.orm.mapped_column('cc', sa.UnicodeText, nullable=True)
    _bcc: Mapped[str] = sa.orm.mapped_column('bcc', sa.UnicodeText, nullable=True)

    recipients: DynamicMapped[MailerRecipient] = relationship(
        lazy='dynamic',
        back_populates='mailer',
        order_by='(MailerRecipient.draft_id, MailerRecipient._fullname,'
        ' MailerRecipient._firstname, MailerRecipient._lastname)',
    )
    drafts: Mapped[list[MailerDraft]] = relationship(
        back_populates='mailer',
        order_by='MailerDraft.url_id',
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if 'name' not in kwargs:  # Use random name unless one was provided
            self.name = buid()

    def __repr__(self) -> str:
        return f'<Mailer "{self.title}" ({MailerState(self.status).title})>'

    @property
    def fields(self) -> Collection[str]:
        """Set or return template fields."""
        flist = self._fields.split(' ')
        while '' in flist:
            flist.remove('')
        return tuple(flist)

    @fields.setter
    def fields(self, value: Collection[str]) -> None:
        self._fields = ' '.join(sorted(set(value)))

    @property
    def cc(self) -> str:
        """Set or return CC recipients on email."""
        return self._cc

    @cc.setter
    def cc(self, value: str | Collection[str]) -> None:
        if isinstance(value, str):
            value = [
                _l.strip()
                for _l in value.replace('\r\n', '\n').replace('\r', '\n').split('\n')
                if _l
            ]
        self._cc = '\n'.join(sorted(set(value)))

    @property
    def bcc(self) -> str:
        """Set or return BCC recipients on email."""
        return self._bcc

    @bcc.setter
    def bcc(self, value: str | Collection[str]) -> None:
        if isinstance(value, str):
            value = [
                _l.strip()
                for _l in value.replace('\r\n', '\n').replace('\r', '\n').split('\n')
                if _l
            ]
        self._bcc = '\n'.join(sorted(set(value)))

    def recipients_iter(self) -> Iterator[MailerRecipient]:
        """Iterate through recipients."""
        ids = [
            i.id
            for i in db.session.query(MailerRecipient.id)
            .filter(MailerRecipient.mailer_id == self.id)
            .order_by(MailerRecipient.id)
            .all()
        ]
        for rid in ids:
            recipient = MailerRecipient.query.get(rid)
            if recipient:
                yield recipient

    def permissions(
        self, actor: Account | None, inherited: set[str] | None = None
    ) -> set[str]:
        perms = super().permissions(actor, inherited)
        if actor is not None and actor == self.user:
            perms.update(['edit', 'delete', 'send', 'new-recipient', 'report'])
        return perms

    def draft(self) -> MailerDraft | None:
        if self.drafts:
            return self.drafts[-1]
        return None

    def render_preview(self, text: str) -> str:
        if self.stylesheet is not None and self.stylesheet.strip():
            stylesheet = f'<style type="text/css">{escape(self.stylesheet)}</style>\n'
        else:
            stylesheet = ''
        rendered_text = Markup(stylesheet) + markdown_mailer.render(text)
        if rendered_text:
            # email_transform uses LXML, which does not like empty strings
            return email_transform(rendered_text, base_url=request.url_root)
        return ''


class MailerDraft(BaseScopedIdMixin, Model):
    """Revision-controlled draft of mailer text (a Mustache template)."""

    __tablename__ = 'mailer_draft'

    mailer_id: Mapped[int] = sa.orm.mapped_column(
        sa.ForeignKey('mailer.id'), nullable=False
    )
    mailer: Mapped[Mailer] = relationship(Mailer, back_populates='drafts')
    parent: Mapped[Mailer] = sa.orm.synonym('mailer')
    revision_id: Mapped[int] = sa.orm.synonym('url_id')

    subject: Mapped[str] = sa.orm.mapped_column(
        sa.Unicode(250), nullable=False, default="", deferred=True
    )

    template: Mapped[str] = sa.orm.mapped_column(
        sa.UnicodeText, nullable=False, default="", deferred=True
    )

    __table_args__ = (sa.UniqueConstraint('mailer_id', 'url_id'),)

    def __repr__(self) -> str:
        return f'<MailerDraft {self.revision_id} of {self.mailer!r}>'

    def get_preview(self) -> str:
        return self.mailer.render_preview(self.template)


class MailerRecipient(BaseScopedIdMixin, Model):
    """Recipient of a mailer."""

    __tablename__ = 'mailer_recipient'

    # Mailer this recipient is a part of
    mailer_id: Mapped[int] = sa.orm.mapped_column(sa.ForeignKey('mailer.id'))
    mailer: Mapped[Mailer] = relationship(Mailer, back_populates='recipients')
    parent: Mapped[Mailer] = sa.orm.synonym('mailer')

    _fullname: Mapped[str | None] = sa.orm.mapped_column(
        'fullname', sa.Unicode(80), nullable=True
    )
    _firstname: Mapped[str | None] = sa.orm.mapped_column(
        'firstname', sa.Unicode(80), nullable=True
    )
    _lastname: Mapped[str | None] = sa.orm.mapped_column(
        'lastname', sa.Unicode(80), nullable=True
    )
    _nickname: Mapped[str | None] = sa.orm.mapped_column(
        'nickname', sa.Unicode(80), nullable=True
    )

    _email: Mapped[str] = sa.orm.mapped_column(
        'email', sa.Unicode(80), nullable=False, index=True
    )
    md5sum: Mapped[str] = sa.orm.mapped_column(
        sa.String(32), nullable=False, index=True
    )

    data: Mapped[jsonb] = sa.orm.mapped_column()

    is_sent: Mapped[bool] = sa.orm.mapped_column(default=False)

    # Support email open tracking
    opentoken: Mapped[str] = sa.orm.mapped_column(
        sa.Unicode(44), nullable=False, default=newsecret, unique=True
    )
    opened: Mapped[bool] = sa.orm.mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    opened_ipaddr: Mapped[str | None] = sa.orm.mapped_column(
        sa.Unicode(45), nullable=True
    )
    opened_first_at: Mapped[datetime | None] = sa.orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    opened_last_at: Mapped[datetime | None] = sa.orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    opened_count: Mapped[int] = sa.orm.mapped_column(
        sa.Integer, nullable=False, default=0
    )

    # Support RSVP if the email requires it
    rsvptoken: Mapped[str] = sa.orm.mapped_column(
        sa.Unicode(44), nullable=False, default=newsecret, unique=True
    )
    # Y/N/M response
    rsvp: Mapped[str | None] = sa.orm.mapped_column(sa.Unicode(1), nullable=True)

    # Customised template for this recipient
    subject: Mapped[str | None] = sa.orm.mapped_column(sa.Unicode(250), nullable=True)
    template: Mapped[str | None] = sa.orm.mapped_column(
        sa.UnicodeText, nullable=True, deferred=True
    )

    # Rendered version of user's template, for archival
    rendered_text: Mapped[str | None] = sa.orm.mapped_column(
        sa.UnicodeText, nullable=True, deferred=True
    )
    rendered_html: Mapped[str | None] = sa.orm.mapped_column(
        sa.UnicodeText, nullable=True, deferred=True
    )

    # Draft of the mailer template that the custom template is linked to (for updating
    # before finalising)
    draft_id: Mapped[int | None] = sa.orm.mapped_column(
        sa.ForeignKey('mailer_draft.id')
    )
    draft: Mapped[MailerDraft | None] = relationship(MailerDraft)

    __table_args__ = (sa.UniqueConstraint('mailer_id', 'url_id'),)

    def __repr__(self) -> str:
        return f'<MailerRecipient {self.fullname} {self.email} of {self.mailer!r}>'

    @property
    def fullname(self) -> str | None:
        """Recipient's fullname, constructed from first and last names if required."""
        if self._fullname:
            return self._fullname
        if self._firstname:
            if self._lastname:
                # FIXME: Cultural assumption of <first> <space> <last> name.
                return f"{self._firstname} {self._lastname}"
            return self._firstname
        if self._lastname:
            return self._lastname
        return None

    @fullname.setter
    def fullname(self, value: str | None) -> None:
        self._fullname = value

    @property
    def firstname(self) -> str | None:
        if self._firstname:
            return self._firstname
        if self._fullname:
            return NAMESPLIT_RE.split(self._fullname)[0]
        return None

    @firstname.setter
    def firstname(self, value: str | None) -> None:
        self._firstname = value

    @property
    def lastname(self) -> str | None:
        if self._lastname:
            return self._lastname
        if self._fullname:
            return NAMESPLIT_RE.split(self._fullname)[-1]
        return None

    @lastname.setter
    def lastname(self, value: str | None) -> None:
        self._lastname = value

    @property
    def nickname(self) -> str | None:
        return self._nickname or self.firstname

    @nickname.setter
    def nickname(self, value: str | None) -> None:
        self._nickname = value

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        self._email = value.lower()
        self.md5sum = md5sum(value)

    @property
    def revision_id(self) -> int | None:
        return self.draft.revision_id if self.draft else None

    def is_latest_draft(self) -> bool:
        if not self.draft:
            return True
        return self.draft == self.mailer.draft()

    def template_data(self) -> dict[str, Any]:
        tdata = {
            'fullname': self.fullname,
            'email': self.email,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'nickname': self.nickname,
            'RSVP_Y': self.url_for('rsvp', status='Y', _external=True),
            'RSVP_N': self.url_for('rsvp', status='N', _external=True),
            'RSVP_M': self.url_for('rsvp', status='M', _external=True),
        }
        if self.data:
            tdata.update(self.data)
        return tdata

    def get_rendered(self) -> MarkdownString:
        """Get Mustache-rendered Markdown text."""
        if self.draft:
            return mustache_md(self.template or '', self.template_data())
        draft = self.mailer.draft()
        if draft is not None:
            return mustache_md(draft.template or '', self.template_data())
        return MarkdownString('')

    def get_preview(self) -> str:
        """Get HTML preview."""
        return self.mailer.render_preview(self.get_rendered())

    def openmarkup(self) -> Markup:
        if self.mailer.trackopens:
            return Markup(
                f'\n<img src="{self.url_for("trackopen")}" width="1" height="1" alt=""'
                f' border="0" style="height:1px !important;width:1px !important;'
                f'border-width:0 !important;margin-top:0 !important;'
                f'margin-bottom:0 !important;margin-right:0 !important;'
                f'margin-left:0 !important;padding-top:0 !important;'
                f'padding-bottom:0 !important;padding-right:0 !important;'
                f'padding-left:0 !important;"/>'
            )
        return Markup('')

    @property
    def custom_draft(self) -> bool:
        """Check if this recipient has a custom draft."""
        return self.draft is not None

    @classmethod
    def custom_draft_in(cls, mailer: Mailer) -> list[MailerRecipient]:
        return (
            cls.query.filter(
                cls.mailer == mailer,
                cls.draft.isnot(None),
            )
            .options(
                defer(cls.created_at),
                defer(cls.updated_at),
                defer(cls._email),
                defer(cls.md5sum),
                defer(cls._fullname),
                defer(cls._firstname),
                defer(cls._lastname),
                defer(cls.data),
                defer(cls.opentoken),
                defer(cls.opened),
                defer(cls.rsvptoken),
                defer(cls.rsvp),
                defer(cls._nickname),
            )
            .all()
        )


@reopen(Account)
class __Account:
    mailers: Mapped[list[Mailer]] = relationship(
        Mailer, back_populates='user', order_by='Mailer.updated_at.desc()'
    )
