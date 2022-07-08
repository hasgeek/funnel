"""User, organization, team and user anchor models."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable, List, Optional, Union, cast, overload
from uuid import UUID
import hashlib

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql.expression import Select

from werkzeug.utils import cached_property

from passlib.hash import argon2, bcrypt
from typing_extensions import Literal
import base58
import phonenumbers

from baseframe import __
from coaster.sqlalchemy import (
    Query,
    RoleMixin,
    StateManager,
    add_primary_relationship,
    auto_init_default,
    failsafe_add,
    with_roles,
)
from coaster.utils import LabeledEnum, newsecret, require_one_of, utcnow

from ..typing import OptionalMigratedTables
from . import (
    BaseMixin,
    LocaleType,
    TimezoneType,
    TSVectorType,
    UuidMixin,
    db,
    hybrid_property,
)
from .email_address import EmailAddress, EmailAddressMixin
from .helpers import ImgeeFurl, add_search_trigger, quote_autocomplete_like

__all__ = [
    'USER_STATE',
    'deleted_user',
    'removed_user',
    'User',
    'DuckTypeUser',
    'UserOldId',
    'Organization',
    'Team',
    'UserEmail',
    'UserEmailClaim',
    'UserPhone',
    'UserExternalId',
    'Anchor',
]


class SharedProfileMixin:
    """Common methods between User and Organization to link to Profile."""

    # The `name` property in User and Organization is not over here because
    # of what seems to be a SQLAlchemy bug: we can't override the expression
    # (both models need separate expressions) without triggering an inspection
    # of the `profile` relationship, which does not exist yet as the backrefs
    # are only fully setup when module loading is finished.
    # Doc: https://docs.sqlalchemy.org/en/latest/orm/extensions/hybrid.html
    # #reusing-hybrid-properties-across-subclasses

    name: Optional[str]
    profile: Optional[Profile]

    def validate_name_candidate(self, name: str) -> Optional[str]:
        """Validate if name is valid for this object, returning an error identifier."""
        if name and self.name and name.lower() == self.name.lower():
            # Same name, or only a case change. No validation required
            return None
        return Profile.validate_name_candidate(name)

    @property
    def has_public_profile(self) -> bool:
        """Return the visibility state of a profile."""
        profile = self.profile
        return profile is not None and bool(profile.state.PUBLIC)

    with_roles(has_public_profile, read={'all'}, write={'owner'})

    @property
    def avatar(self) -> Optional[ImgeeFurl]:
        """Return avatar image URL."""
        profile = self.profile
        return (
            profile.logo_url
            if profile is not None
            and profile.logo_url is not None
            and profile.logo_url.url != ''
            else None
        )

    @property
    def profile_url(self) -> Optional[str]:
        """Return optional URL to profile page."""
        profile = self.profile
        return profile.url_for() if profile is not None else None

    with_roles(profile_url, read={'all'})


class USER_STATE(LabeledEnum):  # noqa: N801
    """State codes for user accounts."""

    #: Regular, active user
    ACTIVE = (0, __("Active"))  # XXX: Using 0 in a state code is a legacy mistake
    #: Suspended account (cause and explanation not included here)
    SUSPENDED = (1, __("Suspended"))
    #: Merged into another user
    MERGED = (2, __("Merged"))
    #: Invited to make an account, doesn't have one yet
    INVITED = (3, __("Invited"))
    #: Permanently deleted account
    DELETED = (4, __("Deleted"))


class ORGANIZATION_STATE(LabeledEnum):  # noqa: N801
    """State codes for organizations."""

    #: Regular, active organization
    ACTIVE = (1, __("Active"))
    #: Suspended organization (cause and explanation not included here)
    SUSPENDED = (2, __("Suspended"))


class User(SharedProfileMixin, UuidMixin, BaseMixin, db.Model):
    """User model."""

    __tablename__ = 'user'
    __title_length__ = 80

    #: The user's fullname
    fullname: db.Column = with_roles(
        db.Column(db.Unicode(__title_length__), default='', nullable=False),
        read={'all'},
    )
    #: Alias for the user's fullname
    title = db.synonym('fullname')
    #: Argon2 or Bcrypt hash of the user's password
    pw_hash = db.Column(db.Unicode, nullable=True)
    #: Timestamp for when the user's password last changed
    pw_set_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    #: Expiry date for the password (to prompt user to reset it)
    pw_expires_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    #: User's preferred/last known timezone
    timezone = with_roles(
        db.Column(TimezoneType(backend='pytz'), nullable=True), read={'owner'}
    )
    #: Update timezone automatically from browser activity
    auto_timezone = db.Column(db.Boolean, default=True, nullable=False)
    #: User's preferred/last known locale
    locale = with_roles(db.Column(LocaleType, nullable=True), read={'owner'})
    #: Update locale automatically from browser activity
    auto_locale = db.Column(db.Boolean, default=True, nullable=False)
    #: User's state code (active, suspended, merged, deleted)
    _state = db.Column(
        'state',
        db.SmallInteger,
        StateManager.check_constraint('state', USER_STATE),
        nullable=False,
        default=USER_STATE.ACTIVE,
    )
    #: User account state manager
    state = StateManager('_state', USER_STATE, doc="User account state")
    #: Other user accounts that were merged into this user account
    oldusers = association_proxy('oldids', 'olduser')

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'fullname',
                weights={'fullname': 'A'},
                regconfig='english',
                hltext=lambda: User.fullname,
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        db.Index(
            'ix_user_fullname_lower',
            db.func.lower(fullname).label('fullname_lower'),
            postgresql_ops={'fullname_lower': 'varchar_pattern_ops'},
        ),
        db.Index('ix_user_search_vector', 'search_vector', postgresql_using='gin'),
    )

    _defercols = [
        db.defer('created_at'),
        db.defer('updated_at'),
        db.defer('pw_hash'),
        db.defer('pw_set_at'),
        db.defer('pw_expires_at'),
        db.defer('timezone'),
    ]

    __roles__ = {
        'all': {
            'read': {
                'uuid',
                'name',
                'title',
                'fullname',
                'username',
                'pickername',
                'timezone',
                'avatar',
                'created_at',
                'profile',
                'profile_url',
                'urls',
            },
            'call': {'views', 'forms', 'features', 'url_for'},
        }
    }

    __datasets__ = {
        'primary': {
            'uuid',
            'name',
            'title',
            'fullname',
            'username',
            'pickername',
            'timezone',
            'avatar',
            'created_at',
            'profile',
            'profile_url',
            'urls',
        },
        'related': {
            'name',
            'title',
            'fullname',
            'username',
            'pickername',
            'timezone',
            'avatar',
            'created_at',
            'profile_url',
        },
    }

    primary_email: Optional[UserEmail]
    primary_phone: Optional[UserPhone]

    def __init__(self, password: str = None, **kwargs) -> None:
        self.password = password
        super().__init__(**kwargs)

    @hybrid_property  # type: ignore[override]
    def name(self) -> Optional[str]:  # type: ignore[override]
        """Return @name (username) from linked profile."""  # noqa: D402
        if self.profile:
            return self.profile.name
        return None

    @name.setter
    def name(self, value: Optional[str]):
        """Set @name."""
        if value is None or not value.strip():
            if self.profile is not None:
                raise ValueError("Name is required")
        else:
            if self.profile is not None:
                self.profile.name = value
            else:
                self.profile = Profile(name=value, user=self, uuid=self.uuid)

    @name.expression
    def name(cls):  # noqa: N805  # pylint: disable=no-self-argument
        """Return @name from linked profile as a SQL expression."""
        return db.select([Profile.name]).where(Profile.user_id == cls.id).label('name')

    with_roles(name, read={'all'})
    username: Optional[str] = name  # type: ignore[assignment]

    @cached_property
    def verified_contact_count(self) -> int:
        """Count of verified contact details."""
        return len(self.emails) + len(self.phones)

    @property
    def has_verified_contact_info(self) -> bool:
        """User has any verified contact info (email or phone)."""
        return bool(self.emails) or bool(self.phones)

    @property
    def has_contact_info(self) -> bool:
        """User has any contact information (including unverified)."""
        return self.has_verified_contact_info or bool(self.emailclaims)

    def merged_user(self) -> User:
        """Return the user account that this account was merged into (default: self)."""
        if self.state.MERGED:
            # If our state is MERGED, there _must_ be a corresponding UserOldId record
            return cast(UserOldId, UserOldId.get(self.uuid)).user
        return self

    def _set_password(self, password: Optional[str]):
        """Set a password (write-only property)."""
        if password is None:
            self.pw_hash = None
        else:
            self.pw_hash = argon2.hash(password)
            # Also see :meth:`password_is` for transparent upgrade
        self.pw_set_at = db.func.utcnow()
        # Expire passwords after one year. TODO: make this configurable
        self.pw_expires_at = self.pw_set_at + timedelta(days=365)

    #: Write-only property (passwords cannot be read back in plain text)
    password = property(fset=_set_password, doc=_set_password.__doc__)

    def password_has_expired(self) -> bool:
        """Verify if password expiry timestamp has passed."""
        return (
            self.pw_hash is not None
            and self.pw_expires_at is not None
            and self.pw_expires_at <= utcnow()
        )

    def password_is(self, password: str, upgrade_hash: bool = False) -> bool:
        """Test if the candidate password matches saved hash."""
        if self.pw_hash is None:
            return False

        # Passwords may use the current Argon2 scheme or the older Bcrypt scheme.
        # Bcrypt passwords are transparently upgraded if requested.
        if argon2.identify(self.pw_hash):
            return argon2.verify(password, self.pw_hash)
        if bcrypt.identify(self.pw_hash):
            verified = bcrypt.verify(password, self.pw_hash)
            if verified and upgrade_hash:
                self.pw_hash = argon2.hash(password)
            return verified
        return False

    def __repr__(self) -> str:
        """Represent :class:`User` as a string."""
        return f'<User {self.username or self.buid} "{self.fullname}">'

    def __str__(self) -> str:
        """Return picker name for user."""
        return self.pickername

    @property
    def pickername(self) -> str:
        """Return fullname and @name in a format suitable for identification."""
        if self.username:
            return f'{self.fullname} (@{self.username})'
        return self.fullname

    with_roles(pickername, read={'all'})

    def add_email(
        self,
        email: str,
        primary: bool = False,
        type: Optional[str] = None,  # noqa: A002  # pylint: disable=redefined-builtin
        private: bool = False,
    ) -> UserEmail:
        """Add an email address (assumed to be verified)."""
        useremail = UserEmail(user=self, email=email, type=type, private=private)
        useremail = failsafe_add(
            db.session, useremail, user=self, email_address=useremail.email_address
        )
        if primary:
            self.primary_email = useremail
        return useremail
        # FIXME: This should remove competing instances of UserEmailClaim

    def del_email(self, email: str) -> None:
        """Remove an email address from the user's account."""
        useremail = UserEmail.get_for(user=self, email=email)
        if useremail is not None:
            if self.primary_email in (useremail, None):
                self.primary_email = (
                    UserEmail.query.filter(
                        UserEmail.user == self, UserEmail.id != useremail.id
                    )
                    .order_by(UserEmail.created_at.desc())
                    .first()
                )
            db.session.delete(useremail)

    @property
    def email(self) -> Union[Literal[''], UserEmail]:
        """Return primary email address for user."""
        # Look for a primary address
        useremail = self.primary_email
        if useremail is not None:
            return useremail
        # No primary? Maybe there's one that's not set as primary?
        if self.emails:
            useremail = self.emails[0]
            # XXX: Mark as primary. This may or may not be saved depending on
            # whether the request ended in a database commit.
            self.primary_email = useremail
            return useremail
        # This user has no email address. Return a blank string instead of None
        # to support the common use case, where the caller will use str(user.email)
        # to get the email address as a string.
        return ''

    with_roles(email, read={'owner'})

    def add_phone(
        self,
        phone: str,
        primary: bool = False,
        type: Optional[str] = None,  # noqa: A002  # pylint: disable=redefined-builtin
        private: bool = False,
    ) -> UserPhone:
        """Add a phone number (assumed to be verified)."""
        userphone = UserPhone(user=self, phone=phone, type=type, private=private)
        userphone = failsafe_add(
            db.session, userphone, user=self, phone=userphone.phone
        )
        if primary:
            self.primary_phone = userphone
        return userphone

    def del_phone(self, phone: str) -> None:
        """Remove a phone number from the user's account."""
        userphone = UserPhone.get_for(user=self, phone=phone)
        if userphone is not None:
            if self.primary_phone in (userphone, None):
                self.primary_phone = (
                    UserPhone.query.filter(
                        UserPhone.user == self, UserPhone.id != userphone.id
                    )
                    .order_by(UserPhone.created_at.desc())
                    .first()
                )
            db.session.delete(userphone)

    @property
    def phone(self) -> Union[Literal[''], UserPhone]:
        """Return primary phone number for user."""
        # Look for a primary phone number
        userphone = self.primary_phone
        if userphone is not None:
            return userphone
        # No primary? Maybe there's one that's not set as primary?
        if self.phones:
            userphone = self.phones[0]
            # XXX: Mark as primary. This may or may not be saved depending on
            # whether the request ended in a database commit.
            self.primary_phone = userphone
            return userphone
        # This user has no phone number. Return a blank string instead of None
        # to support the common use case, where the caller will use str(user.phone)
        # to get the phone number as a string.
        return ''

    with_roles(phone, read={'owner'})

    def is_profile_complete(self) -> bool:
        """Verify if profile is complete (fullname, username and contacts present)."""
        return bool(self.fullname and self.username and self.has_verified_contact_info)

    # --- Transport details

    @with_roles(call={'owner'})
    def has_transport_email(self) -> bool:
        """User has an email transport address."""
        return self.state.ACTIVE and bool(self.email)

    @with_roles(call={'owner'})
    def has_transport_sms(self) -> bool:
        """User has an SMS transport address."""
        return self.state.ACTIVE and bool(self.phone)

    @with_roles(call={'owner'})
    def has_transport_webpush(self) -> bool:  # TODO  # pragma: no cover
        """User has a webpush transport address."""
        return False

    @with_roles(call={'owner'})
    def has_transport_telegram(self) -> bool:  # TODO  # pragma: no cover
        """User has a Telegram transport address."""
        return False

    @with_roles(call={'owner'})
    def has_transport_whatsapp(self) -> bool:  # TODO  # pragma: no cover
        """User has a WhatsApp transport address."""
        return False

    @with_roles(call={'owner'})
    def transport_for_email(self, context) -> Optional[UserEmail]:
        """Return user's preferred email address within a context."""
        # TODO: Per-profile/project customization is a future option
        if self.state.ACTIVE:
            return self.email or None
        return None

    @with_roles(call={'owner'})
    def transport_for_sms(self, context) -> Optional[UserPhone]:
        """Return user's preferred phone number within a context."""
        # TODO: Per-profile/project customization is a future option
        if self.state.ACTIVE:
            return self.phone or None
        return None

    @with_roles(call={'owner'})
    def transport_for_webpush(self, context):  # TODO  # pragma: no cover
        """Return user's preferred webpush transport address within a context."""
        return None

    @with_roles(call={'owner'})
    def transport_for_telegram(self, context):  # TODO  # pragma: no cover
        """Return user's preferred Telegram transport address within a context."""
        return None

    @with_roles(call={'owner'})
    def transport_for_whatsapp(self, context):  # TODO  # pragma: no cover
        """Return user's preferred WhatsApp transport address within a context."""
        return None

    @with_roles(call={'owner'})
    def has_transport(self, transport: str) -> bool:
        """
        Verify if user has a given transport address.

        Helper method to call ``self.has_transport_<transport>()``.

        ..note::
            Because this method does not accept a context, it may return True for a
            transport that has been muted in that context. This may cause an empty
            background job to be queued for a notification. Revisit this method when
            preference contexts are supported.
        """
        return getattr(self, 'has_transport_' + transport)()

    @with_roles(call={'owner'})
    def transport_for(
        self, transport: str, context: db.Model
    ) -> Optional[Union[UserEmail, UserPhone]]:
        """
        Get transport address for a given transport and context.

        Helper method to call ``self.transport_for_<transport>(context)``.
        """
        return getattr(self, 'transport_for_' + transport)(context)

    def default_email(self, context=None) -> Optional[Union[UserEmail, UserEmailClaim]]:
        """
        Return default email address (verified if present, else unverified).

        ..note::
            This is a temporary helper method, pending merger of :class:`UserEmailClaim`
            into :class:`UserEmail` with :attr:`~UserEmail.verified` ``== False``. The
            appropriate replacement is :meth:`User.transport_for_email` with a context.
        """
        email = self.transport_for_email(context=context)
        if email:
            return email
        # Fallback when ``transport_for_email`` returns None
        if self.email:
            return self.email
        if self.emailclaims:
            return self.emailclaims[0]
        # This user has no email addresses
        return None

    @property
    def _self_is_owner_and_admin_of_self(self):
        """
        Return self.

        Helper method for :meth:`roles_for` and :meth:`actors_with` to assert that the
        user is owner and admin of their own account.
        """
        return self

    with_roles(_self_is_owner_and_admin_of_self, grants={'owner', 'admin'})

    def organizations_as_owner_ids(self) -> List[int]:
        """
        Return the database ids of the organizations this user is an owner of.

        This is used for database queries.
        """
        return [
            membership.organization_id
            for membership in self.active_organization_owner_memberships
        ]

    @state.transition(state.ACTIVE, state.MERGED)
    def mark_merged_into(self, other_user):
        """Mark account as merged into another account."""
        db.session.add(UserOldId(id=self.uuid, user=other_user))

    @state.transition(state.ACTIVE, state.SUSPENDED)
    def mark_suspended(self):
        """Mark account as suspended on support or moderator request."""

    @state.transition(state.ACTIVE, state.DELETED)
    def do_delete(self):
        """Delete user account."""
        # 1. Delete profile
        if self.profile:
            if not self.profile.is_safe_to_delete():
                raise ValueError("Profile cannot be deleted")
            db.session.delete(self.profile)
        # FIXME: Ask for auth clients to be transferred
        # 2. Delete contact information
        for contact_source in (
            self.emails,
            self.emailclaims,
            self.phones,
            self.phoneclaims,
            self.externalids,
        ):
            for contact in contact_source:
                db.session.delete(contact)
        # 3. Revoke all active memberships
        for membership_source in (
            self.active_organization_admin_memberships,
            self.projects_as_crew_active_memberships,
            self.proposal_active_memberships,
        ):
            for membership in membership_source:
                membership.revoke(actor=self)
        if self.active_site_membership:
            self.active_site_membership.revoke(actor=self)

        # 6. Revoke auth tokens

        # 5. Clear fullname and stored password hash
        self.fullname = ''
        self.password = None

    @overload
    @classmethod
    def get(
        cls,
        *,
        username: str,
        defercols: bool = False,
    ) -> Optional[User]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        buid: str,
        defercols: bool = False,
    ) -> Optional[User]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        userid: str,
        defercols: bool = False,
    ) -> Optional[User]:
        ...

    @classmethod
    def get(
        cls,
        *,
        username: Optional[str] = None,
        buid: Optional[str] = None,
        userid: Optional[str] = None,
        defercols: bool = False,
    ) -> Optional[User]:
        """
        Return a User with the given username or buid.

        :param str username: Username to lookup
        :param str buid: Buid to lookup
        :param bool defercols: Defer loading non-critical columns
        """
        require_one_of(username=username, buid=buid, userid=userid)

        # userid parameter is temporary for Flask-Lastuser compatibility
        if userid:
            buid = userid

        if username is not None:
            query = cls.query.join(Profile).filter(
                db.func.lower(Profile.name) == db.func.lower(username)
            )
        else:
            query = cls.query.filter_by(buid=buid)
        if defercols:
            query = query.options(*cls._defercols)
        user = query.one_or_none()
        if user and user.state.MERGED:
            user = user.merged_user()
        if user and user.state.ACTIVE:
            return user
        return None

    @classmethod
    def all(  # noqa: A003
        cls,
        buids: Iterable[str] = None,
        usernames: Iterable[str] = None,
        defercols: bool = False,
    ) -> List[User]:
        """
        Return all matching users.

        :param list buids: Buids to look up
        :param list usernames: Usernames to look up
        :param bool defercols: Defer loading non-critical columns
        """
        users = set()
        if buids and usernames:
            # Use .outerjoin(Profile) or users without usernames will be excluded
            query = cls.query.outerjoin(Profile).filter(
                db.or_(
                    cls.buid.in_(buids),  # type: ignore[attr-defined]
                    db.func.lower(Profile.name).in_(
                        [username.lower() for username in usernames]
                    ),
                )
            )
        elif buids:
            query = cls.query.filter(cls.buid.in_(buids))  # type: ignore[attr-defined]
        elif usernames:
            query = cls.query.join(Profile).filter(
                db.func.lower(Profile.name).in_(
                    [username.lower() for username in usernames]
                )
            )
        else:
            raise TypeError("A parameter is required")

        if defercols:
            query = query.options(*cls._defercols)
        for user in query.all():
            user = user.merged_user()
            if user.state.ACTIVE:
                users.add(user)
        return list(users)

    @classmethod
    def autocomplete(cls, query: str) -> List[User]:
        """
        Return users whose names begin with the query, for autocomplete widgets.

        Looks up users by fullname, username, external ids and email addresses.

        :param str query: Letters to start matching with
        """
        # Escape the '%' and '_' wildcards in SQL LIKE clauses.
        # Some SQL dialects respond to '[' and ']', so remove them.
        like_query = quote_autocomplete_like(query)

        # We convert to lowercase and use the LIKE operator since ILIKE isn't standard
        # and doesn't use an index in PostgreSQL. There's a functional index for lower()
        # defined above in __table_args__ that also applies to LIKE lower(val) queries.

        if like_query in ('%', '@%'):
            return []

        # base_users is used in two of the three possible queries below
        base_users = (
            # Use outerjoin(Profile) to find users without profiles (not inner join)
            cls.query.outerjoin(Profile)
            .filter(
                cls.state.ACTIVE,
                db.or_(
                    db.func.lower(cls.fullname).like(db.func.lower(like_query)),
                    db.func.lower(Profile.name).like(db.func.lower(like_query)),
                ),
            )
            .options(*cls._defercols)
            .order_by(User.fullname)
            .limit(20)
        )

        if (
            query != '@'
            and query.startswith('@')
            and UserExternalId.__at_username_services__
        ):
            # @-prefixed, so look for usernames, including other @username-using
            # services like Twitter and GitHub. Make a union of three queries.
            users = (
                # Query 1: @query -> User.username
                cls.query.join(Profile)
                .filter(
                    cls.state.ACTIVE,
                    db.func.lower(Profile.name).like(db.func.lower(like_query[1:])),
                )
                .options(*cls._defercols)
                .limit(20)
                # FIXME: Still broken as of SQLAlchemy 1.4.23 (also see next block)
                # .union(
                #     # Query 2: @query -> UserExternalId.username
                #     cls.query.join(UserExternalId)
                #     .filter(
                #         cls.state.ACTIVE,
                #         UserExternalId.service.in_(
                #             UserExternalId.__at_username_services__
                #         ),
                #         db.func.lower(UserExternalId.username).like(
                #             db.func.lower(like_query[1:])
                #         ),
                #     )
                #     .options(*cls._defercols)
                #     .limit(20),
                #     # Query 3: like_query -> User.fullname
                #     cls.query.filter(
                #         cls.state.ACTIVE,
                #         db.func.lower(cls.fullname).like(db.func.lower(like_query)),
                #     )
                #     .options(*cls._defercols)
                #     .limit(20),
                # )
                .all()
            )
        elif '@' in query and not query.startswith('@'):
            # Query has an @ in the middle. Match email address (exact match only).
            # Use param `query` instead of `like_query` because it's not a LIKE query.
            # Combine results with regular user search
            users = (
                cls.query.join(UserEmail)
                .join(EmailAddress)
                .filter(
                    EmailAddress.get_filter(email=query),
                    cls.state.ACTIVE,
                )
                .options(*cls._defercols)
                .limit(20)
                # .union(base_users)  # FIXME: Broken in SQLAlchemy 1.4.17
                .all()
            )
        else:
            # No '@' in the query, so do a regular autocomplete
            users = base_users.all()
        return users

    @classmethod
    def active_user_count(cls) -> int:
        """Count of all active user accounts."""
        return cls.query.filter(cls.state.ACTIVE).count()

    #: FIXME: Temporary values for Baseframe compatibility
    def organization_links(self) -> List:
        """Return list of organizations affiliated with this user (deprecated)."""
        return []


# XXX: Deprecated, still here for Baseframe compatibility
User.userid = User.uuid_b64

auto_init_default(User._state)  # pylint: disable=protected-access
add_search_trigger(User, 'search_vector')


class UserOldId(UuidMixin, BaseMixin, db.Model):
    """Record of an older UUID for a user, after account merger."""

    __tablename__ = 'user_oldid'
    __uuid_primary_key__ = True

    #: Old user account, if still present
    olduser = db.relationship(
        User,
        primaryjoin='foreign(UserOldId.id) == remote(User.uuid)',
        backref=db.backref('oldid', uselist=False),
    )
    #: User id of new user
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    #: New user account
    user = db.relationship(
        User, foreign_keys=[user_id], backref=db.backref('oldids', cascade='all')
    )

    def __repr__(self) -> str:
        """Represent :class:`UserOldId` as a string."""
        return f'<UserOldId {self.buid} of {self.user!r}>'

    @classmethod
    def get(cls, uuid: UUID) -> Optional[UserOldId]:
        """Get an old user record given a UUID."""
        return cls.query.filter_by(id=uuid).one_or_none()


class DuckTypeUser(RoleMixin):
    """User singleton constructor. Ducktypes a regular user object."""

    id = None  # noqa: A003
    created_at = updated_at = None
    uuid = userid = buid = uuid_b58 = None
    username = name = None
    profile = None
    profile_url = None
    email = phone = None

    # Copy registries from User model
    views = User.views
    features = User.features
    forms = User.forms

    __roles__ = {
        'all': {
            'read': {
                'id',
                'uuid',
                'username',
                'fullname',
                'pickername',
                'profile',
                'profile_url',
            },
            'call': {'views', 'forms', 'features', 'url_for'},
        }
    }

    __datasets__ = {
        'related': {
            'username',
            'fullname',
            'pickername',
            'profile',
            'profile_url',
        }
    }

    #: Make obj.user from a referring object falsy
    def __bool__(self) -> bool:
        """Represent boolean state."""
        return False

    def __init__(self, representation: str) -> None:
        self.fullname = self.title = self.pickername = representation

    def __str__(self) -> str:
        """Represent user account as a string."""
        return self.pickername

    def url_for(self, *args, **kwargs) -> Literal['']:
        """Return blank URL for anything to do with this user."""
        return ''


deleted_user = DuckTypeUser(__("[deleted]"))
removed_user = DuckTypeUser(__("[removed]"))


# --- Organizations and teams -------------------------------------------------

team_membership = db.Table(
    'team_membership',
    db.Model.metadata,
    db.Column(
        'user_id', None, db.ForeignKey('user.id'), nullable=False, primary_key=True
    ),
    db.Column(
        'team_id', None, db.ForeignKey('team.id'), nullable=False, primary_key=True
    ),
    db.Column(
        'created_at',
        db.TIMESTAMP(timezone=True),
        nullable=False,
        default=db.func.utcnow(),
    ),
)


class Organization(SharedProfileMixin, UuidMixin, BaseMixin, db.Model):
    """An organization of one or more users with distinct roles."""

    __tablename__ = 'organization'
    __title_length__ = 80

    profile: Profile

    title = with_roles(
        db.Column(db.Unicode(__title_length__), default='', nullable=False),
        read={'all'},
    )

    #: Organization's state (active, suspended)
    _state = db.Column(
        'state',
        db.SmallInteger,
        StateManager.check_constraint('state', ORGANIZATION_STATE),
        nullable=False,
        default=ORGANIZATION_STATE.ACTIVE,
    )
    #: Organization state manager
    state = StateManager('_state', ORGANIZATION_STATE, doc="Organization state")

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'title',
                weights={'title': 'A'},
                regconfig='english',
                hltext=lambda: Organization.title,
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        db.Index(
            'ix_organization_search_vector', 'search_vector', postgresql_using='gin'
        ),
    )

    __roles__ = {
        'all': {
            'read': {
                'name',
                'title',
                'pickername',
                'created_at',
                'profile',
                'profile_url',
                'urls',
            },
            'call': {'views', 'features', 'forms', 'url_for'},
        }
    }

    __datasets__ = {
        'primary': {
            'name',
            'title',
            'username',
            'pickername',
            'avatar',
            'created_at',
            'profile',
            'profile_url',
        },
        'related': {'name', 'title', 'pickername', 'created_at'},
    }

    _defercols = [db.defer('created_at'), db.defer('updated_at')]

    def __init__(self, owner: User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        db.session.add(
            OrganizationMembership(
                organization=self, user=owner, granted_by=owner, is_owner=True
            )
        )

    @hybrid_property  # type: ignore[override]
    def name(self) -> str:  # type: ignore[override]
        """Return @name (username) from linked profile."""  # noqa: D402
        return self.profile.name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        """Set a new @name for the organization."""
        if value is None or not value.strip():
            raise ValueError("Name is required")
        if self.profile is not None:
            self.profile.name = value
        else:
            # This code will only be reachable during `__init__`
            self.profile = Profile(  # type: ignore[unreachable]
                name=value, organization=self, uuid=self.uuid
            )

    @name.expression
    def name(cls) -> Select:  # noqa: N805  # pylint: disable=no-self-argument
        """Return @name from linked profile as a SQL expression."""
        return (
            db.select([Profile.name])
            .where(Profile.organization_id == cls.id)
            .label('name')
        )

    with_roles(name, read={'all'})

    def __repr__(self) -> str:
        """Represent :class:`Organization` as a string."""
        return f'<Organization {self.name} "{self.title}">'

    @property
    def pickername(self) -> str:
        """Return title and @name in a format suitable for identification."""
        if self.name:
            return f'{self.title} (@{self.name})'
        return self.title

    with_roles(pickername, read={'all'})

    def people(self) -> Query:
        """Return a list of users from across the public teams they are in."""
        return (
            User.query.join(team_membership)
            .join(Team)
            .filter(Team.organization == self, Team.is_public.is_(True))
            .options(db.joinedload(User.teams))
            .order_by(db.func.lower(User.fullname))
        )

    @state.transition(state.ACTIVE, state.SUSPENDED)
    def mark_suspended(self):
        """Mark organization as suspended on support request."""

    @state.transition(state.SUSPENDED, state.ACTIVE)
    def mark_active(self):
        """Mark organization as active on support request."""

    @overload
    @classmethod
    def get(
        cls,
        *,
        name: str,
        defercols: bool = False,
    ) -> Optional[Organization]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        buid: str,
        defercols: bool = False,
    ) -> Optional[Organization]:
        ...

    @classmethod
    def get(
        cls,
        *,
        name: Optional[str] = None,
        buid: Optional[str] = None,
        defercols: bool = False,
    ) -> Optional[Organization]:
        """
        Return an Organization with matching name or buid.

        Note that ``name`` is the username, not the title.

        :param str name: Name of the organization
        :param str buid: Buid of the organization
        :param bool defercols: Defer loading non-critical columns
        """
        require_one_of(name=name, buid=buid)

        if name is not None:
            query = cls.query.join(Profile).filter(
                db.func.lower(Profile.name) == db.func.lower(name)
            )
        else:
            query = cls.query.filter_by(buid=buid)
        if defercols:
            query = query.options(*cls._defercols)
        return query.one_or_none()

    @classmethod
    def all(  # noqa: A003
        cls,
        buids: Iterable[str] = None,
        names: Iterable[str] = None,
        defercols: bool = False,
    ) -> List[Organization]:
        """Get all organizations with matching `buids` and `names`."""
        orgs = []
        if buids:
            query = cls.query.filter(cls.buid.in_(buids))  # type: ignore[attr-defined]
            if defercols:
                query = query.options(*cls._defercols)
            orgs.extend(query.all())
        if names:
            query = cls.query.join(Profile).filter(
                db.func.lower(Profile.name).in_([name.lower() for name in names])
            )
            if defercols:
                query = query.options(*cls._defercols)
            orgs.extend(query.all())
        return orgs


add_search_trigger(Organization, 'search_vector')


class Team(UuidMixin, BaseMixin, db.Model):
    """A team of users within an organization."""

    __tablename__ = 'team'
    __title_length__ = 250
    #: Displayed name
    title = db.Column(db.Unicode(__title_length__), nullable=False)
    #: Organization
    organization_id = db.Column(None, db.ForeignKey('organization.id'), nullable=False)
    organization = with_roles(
        db.relationship(
            Organization,
            backref=db.backref('teams', order_by=db.func.lower(title), cascade='all'),
        ),
        grants_via={None: {'owner': 'owner', 'admin': 'admin'}},
    )
    users = with_roles(
        db.relationship(
            User, secondary=team_membership, lazy='dynamic', backref='teams'
        ),
        grants={'subject'},
    )

    is_public = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        """Represent :class:`Team` as a string."""
        return f'<Team {self.title} of {self.organization!r}>'

    @property
    def pickername(self) -> str:
        """Return team's title in a format suitable for identification."""
        return self.title

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> Optional[Iterable[str]]:
        """Migrate one user account to another when merging user accounts."""
        for team in list(old_user.teams):
            if team not in new_user.teams:
                # FIXME: This creates new memberships, updating `created_at`.
                # Unfortunately, we can't work with model instances as in the other
                # `migrate_user` methods as team_membership is an unmapped table.
                new_user.teams.append(team)
            old_user.teams.remove(team)
        return [cls.__table__.name, team_membership.name]

    @classmethod
    def get(cls, buid: str, with_parent: bool = False) -> Optional[Team]:
        """
        Return a Team with matching buid.

        :param str buid: Buid of the team
        """
        if with_parent:
            query = cls.query.options(db.joinedload(cls.organization))
        else:
            query = cls.query
        return query.filter_by(buid=buid).one_or_none()


# --- User email/phone and misc


class UserEmail(EmailAddressMixin, BaseMixin, db.Model):
    """An email address linked to a user account."""

    __tablename__ = 'user_email'
    __email_optional__ = False
    __email_unique__ = True
    __email_for__ = 'user'
    __email_is_exclusive__ = True

    # Tell mypy that these are not optional
    email_address: EmailAddress
    email: str

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('emails', cascade='all'))

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # noqa: A003

    __datasets__ = {
        'primary': {'user', 'email', 'private', 'type'},
        'without_parent': {'email', 'private', 'type'},
        'related': {'email', 'private', 'type'},
    }

    def __init__(self, user: User, **kwargs) -> None:
        email = kwargs.pop('email', None)
        if email:
            kwargs['email_address'] = EmailAddress.add_for(user, email)
        super().__init__(user=user, **kwargs)

    def __repr__(self) -> str:
        """Represent :class:`UserEmail` as a string."""
        return f'<UserEmail {self.email} of {self.user!r}>'

    def __str__(self) -> str:
        """Email address as a string."""
        return self.email

    @property
    def primary(self) -> bool:
        """Check whether this email address is the user's primary."""
        return self.user.primary_email == self

    @primary.setter
    def primary(self, value: bool) -> None:
        """Set or unset this email address as primary."""
        if value:
            self.user.primary_email = self
        else:
            if self.user.primary_email == self:
                self.user.primary_email = None

    @overload
    @classmethod
    def get(
        cls,
        email: str,
    ) -> Optional[UserEmail]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        blake2b160: bytes,
    ) -> Optional[UserEmail]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        email_hash: str,
    ) -> Optional[UserEmail]:
        ...

    @classmethod
    def get(
        cls,
        email: Optional[str] = None,
        *,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[UserEmail]:
        """
        Return a UserEmail with matching email or blake2b160 hash.

        :param str email: Email address to look up
        :param bytes blake2b160: blake2b of email address to look up
        :param str email_hash: blake2b hash rendered in Base58
        """
        return (
            cls.query.join(EmailAddress)
            .filter(
                EmailAddress.get_filter(
                    email=email, blake2b160=blake2b160, email_hash=email_hash
                )
            )
            .one_or_none()
        )

    @overload
    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        email: str,
    ) -> Optional[UserEmail]:
        ...

    @overload
    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        blake2b160: bytes,
    ) -> Optional[UserEmail]:
        ...

    @overload
    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        email_hash: str,
    ) -> Optional[UserEmail]:
        ...

    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        email: Optional[str] = None,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[UserEmail]:
        """
        Return a UserEmail with matching email or hash if it belongs to the given user.

        :param User user: User to look up for
        :param str email: Email address to look up
        :param bytes blake2b160: 160-bit blake2b of email address
        :param str email_hash: blake2b hash rendered in Base58
        """
        return (
            cls.query.join(EmailAddress)
            .filter(
                cls.user == user,
                EmailAddress.get_filter(
                    email=email, blake2b160=blake2b160, email_hash=email_hash
                ),
            )
            .one_or_none()
        )

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        primary_email = old_user.primary_email
        for useremail in list(old_user.emails):
            useremail.user = new_user
        if new_user.primary_email is None:
            new_user.primary_email = primary_email
        old_user.primary_email = None
        return [cls.__table__.name, user_email_primary_table.name]


class UserEmailClaim(EmailAddressMixin, BaseMixin, db.Model):
    """Claimed but unverified email address for a user."""

    __tablename__ = 'user_email_claim'
    __email_optional__ = False
    __email_unique__ = False
    __email_for__ = 'user'
    __email_is_exclusive__ = False

    # Tell mypy that these are not optional
    email_address: EmailAddress
    email: str

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('emailclaims', cascade='all'))
    verification_code = db.Column(db.String(44), nullable=False, default=newsecret)

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # noqa: A003

    __table_args__ = (db.UniqueConstraint('user_id', 'email_address_id'),)

    __datasets__ = {
        'primary': {'user', 'email', 'private', 'type'},
        'without_parent': {'email', 'private', 'type'},
        'related': {'email', 'private', 'type'},
    }

    def __init__(self, user: User, **kwargs) -> None:
        email = kwargs.pop('email', None)
        if email:
            kwargs['email_address'] = EmailAddress.add_for(user, email)
        super().__init__(user=user, **kwargs)
        self.blake2b = hashlib.blake2b(
            self.email.lower().encode(), digest_size=16
        ).digest()

    def __repr__(self) -> str:
        """Represent :class:`UserEmailClaim` as a string."""
        return f'<UserEmailClaim {self.email} of {self.user!r}>'

    def __str__(self):
        """Return email as a string."""
        return self.email

    @classmethod
    def migrate_user(  # type: ignore[return]
        cls, old_user: User, new_user: User
    ) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        emails = {claim.email for claim in new_user.emailclaims}
        for claim in list(old_user.emailclaims):
            if claim.email not in emails:
                claim.user = new_user
            else:
                # New user also made the same claim. Delete old user's claim
                db.session.delete(claim)

    @overload
    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        email: str,
    ) -> Optional[UserEmailClaim]:
        ...

    @overload
    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        blake2b160: bytes,
    ) -> Optional[UserEmailClaim]:
        ...

    @overload
    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        email_hash: str,
    ) -> Optional[UserEmailClaim]:
        ...

    @classmethod
    def get_for(
        cls,
        user: User,
        *,
        email: Optional[str] = None,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[UserEmailClaim]:
        """
        Return a UserEmailClaim with matching email address for the given user.

        :param User user: User who claimed this email address
        :param str email: Email address to look up
        :param bytes blake2b160: 160-bit blake2b of email address to look up
        :param str email_hash: Base58 rendering of 160-bit blake2b hash
        """
        return (
            cls.query.join(EmailAddress)
            .filter(
                cls.user == user,
                EmailAddress.get_filter(
                    email=email, blake2b160=blake2b160, email_hash=email_hash
                ),
            )
            .one_or_none()
        )

    @overload
    @classmethod
    def get_by(
        cls,
        verification_code: str,
        *,
        email: str,
    ) -> Optional[UserEmailClaim]:
        ...

    @overload
    @classmethod
    def get_by(
        cls,
        verification_code: str,
        *,
        blake2b160: bytes,
    ) -> Optional[UserEmailClaim]:
        ...

    @overload
    @classmethod
    def get_by(
        cls,
        verification_code: str,
        *,
        email_hash: str,
    ) -> Optional[UserEmailClaim]:
        ...

    @classmethod
    def get_by(
        cls,
        verification_code: str,
        *,
        email: Optional[str] = None,
        blake2b160: Optional[bytes] = None,
        email_hash: Optional[str] = None,
    ) -> Optional[UserEmailClaim]:
        """Return UserEmailClaim instance given verification code and email or hash."""
        return (
            cls.query.join(EmailAddress)
            .filter(
                cls.verification_code == verification_code,
                EmailAddress.get_filter(
                    email=email, blake2b160=blake2b160, email_hash=email_hash
                ),
            )
            .one_or_none()
        )

    @classmethod
    def all(cls, email: str) -> Query:  # noqa: A003
        """
        Return all UserEmailClaim instances with matching email address.

        :param str email: Email address to lookup
        """
        return cls.query.join(EmailAddress).filter(EmailAddress.get_filter(email=email))


auto_init_default(UserEmailClaim.verification_code)


class PhoneHashMixin:
    """Temporary mixin until blake2b160 is a stored pre-hashed column."""

    # TODO: Add migration to include blake2b160 column and phone_hash comparator

    phone: str

    @property
    def blake2b160(self) -> bytes:
        """Blake2b 160-bit hash of phone number."""
        return hashlib.blake2b(self.phone.encode('utf-8'), digest_size=20).digest()

    @cached_property
    def transport_hash(self) -> str:
        """Hash of phone number for notifications framework."""
        return base58.b58encode(self.blake2b160).decode()


class UserPhone(PhoneHashMixin, BaseMixin, db.Model):
    """A phone number linked to a user account."""

    __tablename__ = 'user_phone'
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('phones', cascade='all'))
    _phone = db.Column('phone', db.UnicodeText, unique=True, nullable=False)
    gets_text = db.Column(db.Boolean, nullable=False, default=True)

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # noqa: A003

    __datasets__ = {
        'primary': {'user', 'phone', 'private', 'type'},
        'without_parent': {'phone', 'private', 'type'},
        'related': {'phone', 'private', 'type'},
    }

    def __init__(self, phone: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._phone = phone

    @hybrid_property
    def phone(self):
        """Return raw phone number."""
        return self._phone

    phone = db.synonym('_phone', descriptor=phone)

    def __repr__(self) -> str:
        """Represent :class:`UserPhone` as a string."""
        return f'<UserPhone {self.phone} of {self.user!r}>'

    def __str__(self) -> str:
        """Return phone number as a string."""
        return self.phone

    def parsed(self) -> phonenumbers.PhoneNumber:
        """Return parsed phone number using libphonenumbers."""
        return phonenumbers.parse(self._phone)

    def formatted(self) -> str:
        """Return a phone number formatted for user display."""
        return phonenumbers.format_number(
            self.parsed(), phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

    @property
    def primary(self) -> bool:
        """Check if this is the user's primary phone number."""
        return self.user.primary_phone == self

    @primary.setter
    def primary(self, value: bool) -> None:
        if value:
            self.user.primary_phone = self
        else:
            if self.user.primary_phone == self:
                self.user.primary_phone = None

    @classmethod
    def get(cls, phone: str) -> Optional[UserPhone]:
        """
        Return a UserPhone with matching phone number.

        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(phone=phone).one_or_none()

    @classmethod
    def get_for(cls, user: User, phone: str) -> Optional[UserPhone]:
        """
        Return a UserPhone with matching phone number if it belongs to the given user.

        :param User user: User to check against
        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(user=user, phone=phone).one_or_none()

    @classmethod
    def migrate_user(cls, old_user: User, new_user: User) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        primary_phone = old_user.primary_phone
        for userphone in list(old_user.phones):
            userphone.user = new_user
        if new_user.primary_phone is None:
            new_user.primary_phone = primary_phone
        old_user.primary_phone = None
        return [cls.__table__.name, user_phone_primary_table.name]


class UserExternalId(BaseMixin, db.Model):
    """An external connected account for a user."""

    __tablename__ = 'user_externalid'
    __at_username_services__: List[str] = []
    #: Foreign key to user table
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    #: User that this connected account belongs to
    user = db.relationship(User, backref=db.backref('externalids', cascade='all'))
    #: Identity of the external service (in app's login provider registry)
    service = db.Column(db.UnicodeText, nullable=False)
    #: Unique user id as per external service, used for identifying related accounts
    userid = db.Column(db.UnicodeText, nullable=False)  # Unique id (or obsolete OpenID)
    #: Optional public-facing username on the external service
    username = db.Column(db.UnicodeText, nullable=True)  # LinkedIn once used full URLs
    #: OAuth or OAuth2 access token
    oauth_token = db.Column(db.UnicodeText, nullable=True)
    #: Optional token secret (not used in OAuth2, used by Twitter with OAuth1a)
    oauth_token_secret = db.Column(db.UnicodeText, nullable=True)
    #: OAuth token type (typically 'bearer')
    oauth_token_type = db.Column(db.UnicodeText, nullable=True)
    #: OAuth2 refresh token
    oauth_refresh_token = db.Column(db.UnicodeText, nullable=True)
    #: OAuth2 token expiry in seconds, as sent by service provider
    oauth_expires_in = db.Column(db.Integer, nullable=True)
    #: OAuth2 token expiry timestamp, estimate from created_at + oauth_expires_in
    oauth_expires_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)

    #: Timestamp of when this connected account was last (re-)authorised by the user
    last_used_at = db.Column(
        db.TIMESTAMP(timezone=True), default=db.func.utcnow(), nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint('service', 'userid'),
        db.Index(
            'ix_user_externalid_username_lower',
            db.func.lower(username).label('username_lower'),
            postgresql_ops={'username_lower': 'varchar_pattern_ops'},
        ),
    )

    def __repr__(self) -> str:
        """Represent :class:`UserExternalId` as a string."""
        return f'<UserExternalId {self.service}:{self.username} of {self.user!r}>'

    @overload
    @classmethod
    def get(
        cls,
        service: str,
        *,
        userid: str,
    ) -> Optional[UserExternalId]:
        ...

    @overload
    @classmethod
    def get(
        cls,
        service: str,
        *,
        username: str,
    ) -> Optional[UserExternalId]:
        ...

    @classmethod
    def get(
        cls,
        service: str,
        *,
        userid: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Optional[UserExternalId]:
        """
        Return a UserExternalId with the given service and userid or username.

        :param str service: Service to lookup
        :param str userid: Userid to lookup
        :param str username: Username to lookup (may be non-unique)

        Usernames are not guaranteed to be unique within a service. An example is with
        Google, where the userid is a directed OpenID URL, unique but subject to change
        if the Lastuser site URL changes. The username is the email address, which will
        be the same despite different userids.
        """
        param, value = require_one_of(True, userid=userid, username=username)
        return cls.query.filter_by(**{param: value, 'service': service}).one_or_none()


user_email_primary_table = add_primary_relationship(
    User, 'primary_email', UserEmail, 'user', 'user_id'
)
user_phone_primary_table = add_primary_relationship(
    User, 'primary_phone', UserPhone, 'user', 'user_id'
)

#: Anchor type
Anchor = Union[UserEmail, UserEmailClaim, UserPhone, EmailAddress]

# Tail imports
# pylint: disable=wrong-import-position
from .profile import Profile  # isort:skip
from .organization_membership import OrganizationMembership  # isort:skip
