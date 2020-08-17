from datetime import timedelta
import hashlib

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property

from werkzeug.utils import cached_property

from passlib.hash import argon2, bcrypt
import base58
import phonenumbers

from baseframe import __
from coaster.sqlalchemy import (
    RoleMixin,
    add_primary_relationship,
    auto_init_default,
    failsafe_add,
    with_roles,
)
from coaster.utils import LabeledEnum, newpin, newsecret, require_one_of, utcnow

from . import BaseMixin, TimezoneType, TSVectorType, UuidMixin, db
from .email_address import EmailAddress, EmailAddressMixin
from .helpers import add_search_trigger, valid_username

__all__ = [
    'USER_STATUS',
    'deleted_user',
    'removed_user',
    'User',
    'UserOldId',
    'Organization',
    'Team',
    'UserEmail',
    'UserEmailClaim',
    'UserPhone',
    'UserPhoneClaim',
    'UserExternalId',
]


class SharedProfileMixin:
    """
    Common methods between User and Organization to link to Profile
    """

    # The `name` property in User and Organization is not over here because
    # of what seems to be a SQLAlchemy bug: we can't override the expression
    # (both models need separate expressions) without triggering an inspection
    # of the `profile` relationship, which does not exist yet as the backrefs
    # are only fully setup when module loading is finished.
    # Doc: https://docs.sqlalchemy.org/en/latest/orm/extensions/hybrid.html#reusing-hybrid-properties-across-subclasses

    def is_valid_name(self, value):
        if not valid_username(value):
            return False
        existing = Profile.get(value)
        if existing and existing.owner != self:
            return False
        return True

    def validate_name_candidate(self, name):
        if name and self.name and name.lower() == self.name.lower():
            # Same name, or only a case change. No validation required
            return
        return Profile.validate_name_candidate(name)

    # TODO: This property is temporary while account and org edit forms have a checkbox
    # for determining profile visibility. Profile visibility should be controlled
    # through transitions, not as data in a form.

    @property
    def is_public_profile(self):
        """Controls the visibility state of a public profile"""
        return self.profile is not None and self.profile.state.PUBLIC

    @is_public_profile.setter
    def is_public_profile(self, value):
        if not self.profile:
            raise ValueError("There is no profile")
        if value:
            if not self.profile.state.PUBLIC:
                self.profile.make_public()
        else:
            if self.profile.state.PUBLIC:
                self.profile.make_private()


class USER_STATUS(LabeledEnum):  # NOQA: N801
    #: Regular, active user
    ACTIVE = (0, 'active', __("Active"))
    #: Suspended account
    SUSPENDED = (1, 'suspended', __("Suspended"))
    #: Merged into another user
    MERGED = (2, 'merged', __("Merged"))
    #: Invited to make an account, doesn't have one yet
    INVITED = (3, 'invited', __("Invited"))


class User(SharedProfileMixin, UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'user'
    __title_length__ = 80

    # XXX: Deprecated, still here for Baseframe compatibility
    userid = db.synonym('buid')
    #: The user's fullname
    fullname = with_roles(
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
    #: User's timezone
    timezone = with_roles(
        db.Column(TimezoneType(backend='pytz'), nullable=True), read={'owner'}
    )
    #: User's status (active, suspended, merged, etc)
    status = db.Column(db.SmallInteger, nullable=False, default=USER_STATUS.ACTIVE)

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
                'name',
                'title',
                'fullname',
                'username',
                'pickername',
                'timezone',
                'status',
                'avatar',
                'created_at',
            }
        }
    }

    __datasets__ = {
        'related': {
            'name',
            'title',
            'fullname',
            'username',
            'pickername',
            'timezone',
            'status',
            'avatar',
            'created_at',
        }
    }

    def __init__(self, password=None, **kwargs):
        self.password = password
        super(User, self).__init__(**kwargs)

    @hybrid_property
    def name(self):
        if self.profile:
            return self.profile.name

    @name.setter
    def name(self, value):
        if not value:
            if self.profile is not None:
                raise ValueError("Name is required")
        else:
            if self.profile is not None:
                self.profile.name = value
            else:
                self.profile = Profile(name=value, user=self, uuid=self.uuid)

    @name.expression
    def name(cls):  # NOQA: N805
        return db.select([Profile.name]).where(Profile.user_id == cls.id).label('name')

    with_roles(name, read={'all'})
    username = name

    @hybrid_property
    def is_active(self):
        return self.status == USER_STATUS.ACTIVE

    @cached_property
    def verified_contact_count(self):
        count = 0
        count += len(self.emails)
        count += len(self.phones)
        return count

    @property
    def has_verified_contact_info(self):
        return self.verified_contact_count > 0

    def merged_user(self):
        if self.status == USER_STATUS.MERGED:
            return UserOldId.get(self.uuid).user
        else:
            return self

    def _set_password(self, password):
        if password is None:
            self.pw_hash = None
        else:
            self.pw_hash = argon2.hash(password)
            # Also see :meth:`password_is` for transparent upgrade
        self.pw_set_at = db.func.utcnow()
        # Expire passwords after one year. TODO: make this configurable
        self.pw_expires_at = self.pw_set_at + timedelta(days=365)

    #: Write-only property (passwords cannot be read back in plain text)
    password = property(fset=_set_password)

    def password_has_expired(self):
        """True if password expiry timestamp has passed."""
        return (
            self.pw_hash is not None
            and self.pw_expires_at is not None
            and self.pw_expires_at <= utcnow()
        )

    def password_is(self, password, upgrade_hash=False):
        """Test if the candidate password matches saved hash."""
        if self.pw_hash is None:
            return False

        # Passwords may use the current Argon2 scheme or the older Bcrypt scheme.
        # Bcrypt passwords are transparently upgraded if requested.
        if argon2.identify(self.pw_hash):
            return argon2.verify(password, self.pw_hash)
        elif bcrypt.identify(self.pw_hash):
            verified = bcrypt.verify(password, self.pw_hash)
            if verified and upgrade_hash:
                self.pw_hash = argon2.hash(password)
            return verified
        return False

    def __repr__(self):
        return '<User {username} "{fullname}">'.format(
            username=self.username or self.buid, fullname=self.fullname
        )

    def __str__(self):
        return self.pickername

    @with_roles(read={'all'})
    @property
    def pickername(self):
        if self.username:
            return '{fullname} (@{username})'.format(
                fullname=self.fullname, username=self.username
            )
        else:
            return self.fullname

    @with_roles(read={'all'})
    @property
    def avatar(self):
        return (
            self.profile.logo_url
            if self.profile and self.profile.logo_url and self.profile.logo_url.url
            else ''
        )

    def add_email(self, email, primary=False, type=None, private=False):  # NOQA: A002
        useremail = UserEmail(user=self, email=email, type=type, private=private)
        useremail = failsafe_add(
            db.session, useremail, user=self, email_address=useremail.email_address
        )
        if primary:
            self.primary_email = useremail
        return useremail
        # FIXME: This should remove competing instances of UserEmailClaim

    def del_email(self, email):
        useremail = UserEmail.get_for(user=self, email=email)
        if self.primary_email in (useremail, None):
            self.primary_email = (
                UserEmail.query.filter(
                    UserEmail.user == self, UserEmail.id != useremail.id
                )
                .order_by(UserEmail.created_at.desc())
                .first()
            )
        db.session.delete(useremail)

    @with_roles(read={'owner'})
    @cached_property
    def email(self):
        """
        Returns primary email address for user.
        """
        # Look for a primary address
        useremail = self.primary_email
        if useremail:
            return useremail
        # No primary? Maybe there's one that's not set as primary?
        useremail = UserEmail.query.filter_by(user=self).first()
        if useremail:
            # XXX: Mark as primary. This may or may not be saved depending on
            # whether the request ended in a database commit.
            self.primary_email = useremail
            return useremail
        # This user has no email address. Return a blank string instead of None
        # to support the common use case, where the caller will use str(user.email)
        # to get the email address as a string.
        return ''

    @with_roles(read={'owner'})
    @cached_property
    def phone(self):
        """
        Returns primary phone number for user.
        """
        # Look for a primary phone number
        userphone = self.primary_phone
        if userphone:
            return userphone
        # No primary? Maybe there's one that's not set as primary?
        userphone = UserPhone.query.filter_by(user=self).first()
        if userphone:
            # XXX: Mark as primary. This may or may not be saved depending on
            # whether the request ended in a database commit.
            self.primary_phone = userphone
            return userphone
        # This user has no phone number. Return a blank string instead of None
        # to support the common use case, where the caller will use str(user.phone)
        # to get the phone number as a string.
        return ''

    def is_profile_complete(self):
        """
        Return True if profile is complete (fullname, username and one contact are
        present), False otherwise.
        """
        return bool(self.fullname and self.username and self.has_verified_contact_info)

    # --- Transport details

    @with_roles(call={'owner'})
    def has_transport_email(self):
        return self.is_active and self.email is not None

    @with_roles(call={'owner'})
    def has_transport_sms(self):
        return self.is_active and self.phone is not None

    @with_roles(call={'owner'})
    def has_transport_webpush(self):  # TODO  # pragma: no cover
        return False

    @with_roles(call={'owner'})
    def has_transport_telegram(self):  # TODO  # pragma: no cover
        return False

    @with_roles(call={'owner'})
    def has_transport_whatsapp(self):  # TODO  # pragma: no cover
        return False

    @with_roles(call={'owner'})
    def transport_for_email(self, context):
        """Return user's preferred email address within a context."""
        # Per-profile/project customization is a future option
        return self.email if self.is_active else None

    @with_roles(call={'owner'})
    def transport_for_sms(self, context):
        """Return user's preferred phone number within a context."""
        # Per-profile/project customization is a future option
        return self.phone if self.is_active else None

    @with_roles(call={'owner'})
    def transport_for_webpush(self, context):  # TODO  # pragma: no cover
        return None

    @with_roles(call={'owner'})
    def transport_for_telegram(self, context):  # TODO  # pragma: no cover
        return None

    @with_roles(call={'owner'})
    def transport_for_whatsapp(self, context):  # TODO  # pragma: no cover
        return None

    @with_roles(call={'owner'})
    def has_transport(self, transport):
        """
        Helper method to call ``self.has_transport_<transport>()``.

        ..note::
            Because this method does not accept a context, it may return True for a
            transport that has been muted in that context. This may cause an empty
            background job to be queued for a notification. Revisit this method when
            preference contexts are supported.
        """
        return getattr(self, 'has_transport_' + transport)()

    @with_roles(call={'owner'})
    def transport_for(self, transport, context):
        """Helper method to call ``self.transport_for_<transport>(context)``."""
        return getattr(self, 'transport_for_' + transport)(context)

    def roles_for(self, actor, anchors=()):
        roles = super().roles_for(actor, anchors)
        if actor == self:
            # Owner because the user owns their own account
            roles.add('owner')
            # Admin because it's relevant in the Profile model
            roles.add('admin')
        return roles

    def organizations_as_owner_ids(self):
        """
        Return the database ids of the organizations this user is an owner of. This is
        used for database queries.
        """
        return [
            membership.organization_id
            for membership in self.active_organization_owner_memberships
        ]

    @classmethod
    def get(cls, username=None, buid=None, userid=None, defercols=False):
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
        if user and user.status == USER_STATUS.MERGED:
            user = user.merged_user()
        if user and user.is_active:
            return user

    @classmethod  # NOQA: A003
    def all(  # NOQA: A003
        cls, buids=None, userids=None, usernames=None, defercols=False
    ):
        """
        Return all matching users.

        :param list buids: Buids to look up
        :param list userids: Alias for ``buids`` (deprecated)
        :param list usernames: Usernames to look up
        :param bool defercols: Defer loading non-critical columns
        """
        users = set()
        if userids and not buids:
            buids = userids
        if buids and usernames:
            query = cls.query.join(Profile).filter(
                db.or_(
                    cls.buid.in_(buids),
                    db.func.lower(Profile.name).in_(
                        [username.lower() for username in usernames]
                    ),
                )
            )
        elif buids:
            query = cls.query.filter(cls.buid.in_(buids))
        elif usernames:
            query = cls.query.join(Profile).filter(
                db.func.lower(Profile.name).in_(
                    [username.lower() for username in usernames]
                )
            )
        else:
            raise Exception

        if defercols:
            query = query.options(*cls._defercols)
        for user in query.all():
            user = user.merged_user()
            if user.is_active:
                users.add(user)
        return list(users)

    @classmethod
    def autocomplete(cls, query):
        """
        Return users whose names begin with the query, for autocomplete widgets.
        Looks up users by fullname, username, external ids and email addresses.

        :param str query: Letters to start matching with
        """
        # Escape the '%' and '_' wildcards in SQL LIKE clauses.
        # Some SQL dialects respond to '[' and ']', so remove them.
        like_query = (
            query.replace('%', r'\%')
            .replace('_', r'\_')
            .replace('[', '')
            .replace(']', '')
            + '%'
        )

        # We convert to lowercase and use the LIKE operator since ILIKE isn't standard
        # and doesn't use an index in PostgreSQL. There's a functional index for lower()
        # defined above in __table_args__ that also applies to LIKE lower(val) queries.

        if like_query in ('%', '@%'):
            return []

        # base_users is used in two of the three possible queries below
        base_users = (
            cls.query.join(Profile)
            .filter(
                cls.status == USER_STATUS.ACTIVE,
                db.or_(
                    db.func.lower(cls.fullname).like(db.func.lower(like_query)),
                    db.func.lower(Profile.name).like(db.func.lower(like_query)),
                ),
            )
            .options(*cls._defercols)
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
                    cls.status == USER_STATUS.ACTIVE,
                    db.func.lower(Profile.name).like(db.func.lower(like_query[1:])),
                )
                .options(*cls._defercols)
                .limit(20)
                .union(
                    # Query 2: @query -> UserExternalId.username
                    cls.query.join(UserExternalId)
                    .filter(
                        cls.status == USER_STATUS.ACTIVE,
                        UserExternalId.service.in_(
                            UserExternalId.__at_username_services__
                        ),
                        db.func.lower(UserExternalId.username).like(
                            db.func.lower(like_query[1:])
                        ),
                    )
                    .options(*cls._defercols)
                    .limit(20),
                    # Query 3: like_query -> User.fullname
                    cls.query.filter(
                        cls.status == USER_STATUS.ACTIVE,
                        db.func.lower(cls.fullname).like(db.func.lower(like_query)),
                    )
                    .options(*cls._defercols)
                    .limit(20),
                )
                .all()
            )
        elif '@' in query and not query.startswith('@'):
            # Query has an @ in the middle. Match email address (exact match only).
            # Use `query` instead of `like_query` because it's not a LIKE query.
            # Combine results with regular user search
            users = (
                cls.query.join(UserEmail, EmailAddress)
                .filter(
                    UserEmail.user_id == cls.id,
                    UserEmail.email_address_id == EmailAddress.id,
                    EmailAddress.get_filter(email=query),
                    cls.status == USER_STATUS.ACTIVE,
                )
                .options(*cls._defercols)
                .limit(20)
                .union(base_users)
                .all()
            )
        else:
            # No '@' in the query, so do a regular autocomplete
            users = base_users.all()
        return users

    @classmethod
    def active_user_count(cls):
        return cls.query.filter_by(status=USER_STATUS.ACTIVE).count()

    #: FIXME: Temporary values for Baseframe compatibility
    def organization_links(self):
        return []


add_search_trigger(User, 'search_vector')


class UserOldId(UuidMixin, BaseMixin, db.Model):
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
        User, foreign_keys=[user_id], backref=db.backref('oldids', cascade='all'),
    )

    def __repr__(self):
        return '<UserOldId {buid} of {user}>'.format(
            buid=self.buid, user=repr(self.user)[1:-1]
        )

    @classmethod
    def get(cls, uuid):
        return cls.query.filter_by(id=uuid).one_or_none()


class DuckTypeUser(RoleMixin):
    """User singleton constructor. Ducktypes a regular user object."""

    id = None  # NOQA: A003
    uuid = userid = buid = uuid_b58 = None
    username = name = None
    profile = None
    email = phone = None
    is_active = False

    __roles__ = {
        'all': {
            'read': {
                'id',
                'uuid',
                'username',
                'fullname',
                'pickername',
                'profile',
                'is_active',
            }
        }
    }

    __datasets__ = {
        'related': {'username', 'fullname', 'pickername', 'profile', 'is_active'}
    }

    #: Make obj.user from a referring object falsy
    def __bool__(self):
        return False

    def __init__(self, representation):
        self.fullname = self.title = self.pickername = representation

    def __str__(self):
        return self.pickername


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
    __tablename__ = 'organization'
    __title_length__ = 80

    title = with_roles(
        db.Column(db.Unicode(__title_length__), default='', nullable=False),
        read={'all'},
    )

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
            'read': {'name', 'title', 'pickername', 'created_at'},
            'call': {'views', 'features', 'forms'},
        }
    }

    __datasets__ = {'related': {'name', 'title', 'pickername', 'created_at'}}

    _defercols = [db.defer('created_at'), db.defer('updated_at')]

    def __init__(self, owner, *args, **kwargs):
        super(Organization, self).__init__(*args, **kwargs)
        db.session.add(
            OrganizationMembership(
                organization=self, user=owner, granted_by=owner, is_owner=True
            )
        )

    @hybrid_property
    def name(self):
        if self.profile:
            return self.profile.name

    @name.setter
    def name(self, value):
        if not value:
            if self.profile is not None:
                raise ValueError("Name is required")
        else:
            if self.profile is not None:
                self.profile.name = value
            else:
                self.profile = Profile(name=value, organization=self, uuid=self.uuid)

    @name.expression
    def name(cls):  # NOQA: N805
        return (
            db.select([Profile.name])
            .where(Profile.organization_id == cls.id)
            .label('name')
        )

    with_roles(name, read={'all'})

    def __repr__(self):
        return '<Organization {name} "{title}">'.format(
            name=self.name or self.buid, title=self.title
        )

    @with_roles(read={'all'})
    @property
    def pickername(self):
        if self.name:
            return '{title} (@{name})'.format(title=self.title, name=self.name)
        else:
            return self.title

    def people(self):
        """Return a list of users from across the public teams they are in."""
        return (
            User.query.join(team_membership)
            .join(Team)
            .filter(Team.organization == self, Team.is_public.is_(True))
            .options(db.joinedload(User.teams))
            .order_by(db.func.lower(User.fullname))
        )

    def permissions(self, user, inherited=None):
        perms = super().permissions(user, inherited)
        if 'view' in perms:
            perms.remove('view')
        if 'edit' in perms:
            perms.remove('edit')
        if 'delete' in perms:
            perms.remove('delete')

        if user and user in self.admin_users:
            perms.add('view')
            perms.add('edit')
            perms.add('view-teams')
            perms.add('new-team')
        if user and user in self.owner_users:
            perms.add('delete')
        return perms

    @classmethod
    def get(cls, name=None, buid=None, defercols=False):
        """
        Return an Organization with matching name or buid. Note that ``name`` is the username, not the title.

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

    @classmethod  # NOQA: A003
    def all(cls, buids=None, names=None, defercols=False):  # NOQA: A003
        orgs = []
        if buids:
            query = cls.query.filter(cls.buid.in_(buids))
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

    def __repr__(self):
        return '<Team {team} of {organization}>'.format(
            team=self.title, organization=repr(self.organization)[1:-1]
        )

    @property
    def pickername(self):
        return self.title

    def permissions(self, user, inherited=None):
        perms = super(Team, self).permissions(user, inherited)
        if user and user in self.organization.admin_users:
            perms.add('edit')
            perms.add('delete')
        return perms

    @classmethod
    def migrate_user(cls, olduser, newuser):
        for team in list(olduser.teams):
            if team not in newuser.teams:
                # FIXME: This creates new memberships, updating `created_at`.
                # Unfortunately, we can't work with model instances as in the other
                # `migrate_user` methods as team_membership is an unmapped table.
                newuser.teams.append(team)
            olduser.teams.remove(team)
        return [cls.__table__.name, team_membership.name]

    @classmethod
    def get(cls, buid, with_parent=False):
        """
        Return a Team with matching buid.

        :param str buid: Buid of the team
        """
        if with_parent:
            query = cls.query.options(db.joinedload(cls.organization))
        else:
            query = cls.query
        return query.filter_by(buid=buid).one_or_none()


# -- User email/phone and misc


class UserEmail(EmailAddressMixin, BaseMixin, db.Model):
    __tablename__ = 'user_email'
    __email_optional__ = False
    __email_unique__ = True
    __email_for__ = 'user'
    __email_is_exclusive__ = True

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('emails', cascade='all'),)

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # NOQA: A003

    def __init__(self, user, **kwargs):
        email = kwargs.pop('email', None)
        if email:
            kwargs['email_address'] = EmailAddress.add_for(user, email)
        super().__init__(user=user, **kwargs)

    def __repr__(self):
        return '<UserEmail {email} of {user}>'.format(
            email=self.email, user=repr(self.user)[1:-1]
        )

    def __str__(self):
        return self.email

    @property
    def primary(self):
        return self.user.primary_email == self

    @primary.setter
    def primary(self, value):
        if value:
            self.user.primary_email = self
        else:
            if self.user.primary_email == self:
                self.user.primary_email = None

    @classmethod
    def get(cls, email=None, blake2b160=None, email_hash=None):
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

    @classmethod
    def get_for(cls, user, email=None, blake2b160=None, email_hash=None):
        """
        Return a UserEmail with matching email or hash if it belongs to the given user

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
    def migrate_user(cls, old_user, new_user):
        primary_email = old_user.primary_email
        for useremail in list(old_user.emails):
            useremail.user = new_user
        if new_user.primary_email is None:
            new_user.primary_email = primary_email
        old_user.primary_email = None
        return [cls.__table__.name, user_email_primary_table.name]


class UserEmailClaim(EmailAddressMixin, BaseMixin, db.Model):
    __tablename__ = 'user_email_claim'
    __email_optional__ = False
    __email_unique__ = False
    __email_for__ = 'user'
    __email_is_exclusive__ = False

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('emailclaims', cascade='all'),)
    verification_code = db.Column(db.String(44), nullable=False, default=newsecret)
    blake2b = db.Column(db.LargeBinary, nullable=False, index=True)

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # NOQA: A003

    __table_args__ = (db.UniqueConstraint('user_id', 'email_address_id'),)

    def __init__(self, user, **kwargs):
        email = kwargs.pop('email', None)
        if email:
            kwargs['email_address'] = EmailAddress.add_for(user, email)
        super().__init__(user=user, **kwargs)
        self.blake2b = hashlib.blake2b(
            self.email.lower().encode(), digest_size=16
        ).digest()

    @cached_property
    def blake2b_b58(self):
        return base58.b58encode(self.blake2b)

    def __repr__(self):
        return '<UserEmailClaim {email} of {user}>'.format(
            email=self.email, user=repr(self.user)[1:-1]
        )

    def __str__(self):
        return self.email

    def permissions(self, user, inherited=None):
        perms = super(UserEmailClaim, self).permissions(user, inherited)
        if user and user == self.user:
            perms.add('verify')
        return perms

    @classmethod
    def migrate_user(cls, old_user, new_user):
        emails = {claim.email for claim in new_user.emailclaims}
        for claim in list(old_user.emailclaims):
            if claim.email not in emails:
                claim.user = new_user
            else:
                # New user also made the same claim. Delete old user's claim
                db.session.delete(claim)

    @classmethod
    def get_for(cls, user, email=None, blake2b160=None, blake2b=None, email_hash=None):
        """
        Return a UserEmailClaim with matching email address for the given user.

        :param User user: User who claimed this email address
        :param str email: Email address to look up
        :param bytes blake2b160: 160-bit blake2b of email address to look up
        :param bytes blake2b: 128-bit blake2b of email address to look up (deprecated)
        :param str email_hash: Base58 rendering of 160-bit blake2b hash
        """
        require_one_of(
            email=email, blake2b160=blake2b160, email_hash=email_hash, blake2b=blake2b
        )
        if blake2b:
            return cls.query.filter_by(blake2b=blake2b, user=user).one_or_none()
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
    def get_by(cls, verification_code, blake2b=None, blake2b160=None, email_hash=None):
        require_one_of(blake2b=blake2b, blake2b160=blake2b160, email_hash=email_hash)
        if blake2b:
            return cls.query.filter_by(
                blake2b=blake2b, verification_code=verification_code
            ).one_or_none()
        return (
            cls.query.join(EmailAddress)
            .filter(
                cls.verification_code == verification_code,
                EmailAddress.get_filter(blake2b160=blake2b160, email_hash=email_hash),
            )
            .one_or_none()
        )

    @classmethod  # NOQA: A003
    def all(cls, email):  # NOQA: A003
        """
        Return all UserEmailClaim instances with matching email address.

        :param str email: Email address to lookup
        """
        return cls.query.join(EmailAddress).filter(EmailAddress.get_filter(email=email))


auto_init_default(UserEmailClaim.verification_code)


class UserPhone(BaseMixin, db.Model):
    __tablename__ = 'user_phone'
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('phones', cascade='all'))
    _phone = db.Column('phone', db.UnicodeText, unique=True, nullable=False)
    gets_text = db.Column(db.Boolean, nullable=False, default=True)

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # NOQA: A003

    def __init__(self, phone, **kwargs):
        super(UserPhone, self).__init__(**kwargs)
        self._phone = phone

    @hybrid_property
    def phone(self):
        return self._phone

    phone = db.synonym('_phone', descriptor=phone)

    def __repr__(self):
        return '<UserPhone {phone} of {user}>'.format(
            phone=self.phone, user=repr(self.user)[1:-1]
        )

    def __str__(self):
        return self.phone

    def parsed(self):
        return phonenumbers.parse(self._phone)

    def formatted(self):
        return phonenumbers.format_number(
            self.parsed(), phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

    @property
    def primary(self):
        return self.user.primary_phone == self

    @primary.setter
    def primary(self, value):
        if value:
            self.user.primary_phone = self
        else:
            if self.user.primary_phone == self:
                self.user.primary_phone = None

    @classmethod
    def get(cls, phone):
        """
        Return a UserPhone with matching phone number.

        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(phone=phone).one_or_none()

    @classmethod
    def get_for(cls, user, phone):
        """
        Return a UserPhone with matching phone number if it belongs to the given user

        :param User user: User to check against
        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(user=user, phone=phone).one_or_none()

    @classmethod
    def migrate_user(cls, old_user, new_user):
        primary_phone = old_user.primary_phone
        for userphone in list(old_user.phones):
            userphone.user = new_user
        if new_user.primary_phone is None:
            new_user.primary_phone = primary_phone
        old_user.primary_phone = None
        return [cls.__table__.name, user_phone_primary_table.name]


class UserPhoneClaim(BaseMixin, db.Model):
    __tablename__ = 'user_phone_claim'
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('phoneclaims', cascade='all'),)
    _phone = db.Column('phone', db.UnicodeText, nullable=False, index=True)
    gets_text = db.Column(db.Boolean, nullable=False, default=True)
    verification_code = db.Column(db.Unicode(4), nullable=False, default=newpin)
    verification_attempts = db.Column(db.Integer, nullable=False, default=0)

    private = db.Column(db.Boolean, nullable=False, default=False)
    type = db.Column(db.Unicode(30), nullable=True)  # NOQA: A003

    __table_args__ = (db.UniqueConstraint('user_id', 'phone'),)

    def __init__(self, phone, **kwargs):
        super(UserPhoneClaim, self).__init__(**kwargs)
        self.verification_code = newpin()
        self._phone = phone

    @hybrid_property
    def phone(self):
        return self._phone

    phone = db.synonym('_phone', descriptor=phone)

    def __repr__(self):
        return '<UserPhoneClaim {phone} of {user}>'.format(
            phone=self.phone, user=repr(self.user)[1:-1]
        )

    def __str__(self):
        return self.phone

    def parsed(self):
        return phonenumbers.parse(self._phone)

    def formatted(self):
        return phonenumbers.format_number(
            self.parsed(), phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

    @classmethod
    def migrate_user(cls, old_user, new_user):
        phones = {claim.email for claim in new_user.phoneclaims}
        for claim in list(old_user.phoneclaims):
            if claim.phone not in phones:
                claim.user = new_user
            else:
                # New user also made the same claim. Delete old user's claim
                db.session.delete(claim)

    @hybrid_property
    def verification_expired(self):
        return self.verification_attempts >= 3

    def permissions(self, user, inherited=None):
        perms = super(UserPhoneClaim, self).permissions(user, inherited)
        if user and user == self.user:
            perms.add('verify')
        return perms

    @classmethod
    def get_for(cls, user, phone):
        """
        Return a UserPhoneClaim with matching phone number for the given user.

        :param str phone: Phone number to lookup (must be an exact match)
        :param User user: User who claimed this phone number
        """
        return cls.query.filter_by(phone=phone, user=user).one_or_none()

    @classmethod  # NOQA: A003
    def all(cls, phone):  # NOQA: A003
        """
        Return all UserPhoneClaim instances with matching phone number.

        :param str phone: Phone number to lookup (must be an exact match)
        """
        return cls.query.filter_by(phone=phone).all()

    @classmethod
    def delete_expired(cls):
        """Delete expired phone claims"""
        # Delete if:
        # 1. The claim is > 1 hour old
        # 2. Too many unsuccessful verification attempts
        cls.query.filter(
            db.or_(
                cls.updated_at < (utcnow() - timedelta(hours=1)),
                cls.verification_expired,
            )
        ).delete(synchronize_session=False)


class UserExternalId(BaseMixin, db.Model):
    __tablename__ = 'user_externalid'
    __at_username_services__ = []
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, backref=db.backref('externalids', cascade='all'),)
    service = db.Column(db.UnicodeText, nullable=False)
    userid = db.Column(db.UnicodeText, nullable=False)  # Unique id (or obsolete OpenID)
    username = db.Column(db.UnicodeText, nullable=True)  # LinkedIn returns full URLs
    oauth_token = db.Column(db.UnicodeText, nullable=True)
    oauth_token_secret = db.Column(db.UnicodeText, nullable=True)
    oauth_token_type = db.Column(db.UnicodeText, nullable=True)

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

    def __repr__(self):
        return '<UserExternalId {service}:{username} of {user}>'.format(
            service=self.service, username=self.username, user=repr(self.user)[1:-1]
        )

    @classmethod
    def get(cls, service, userid=None, username=None):
        """
        Return a UserExternalId with the given service and userid or username.

        :param str service: Service to lookup
        :param str userid: Userid to lookup
        :param str username: Username to lookup (may be non-unique)

        Usernames are not guaranteed to be unique within a service. An example is with Google,
        where the userid is a directed OpenID URL, unique but subject to change if the Lastuser
        site URL changes. The username is the email address, which will be the same despite
        different userids.
        """
        param, value = require_one_of(True, userid=userid, username=username)
        return cls.query.filter_by(**{param: value, 'service': service}).one_or_none()

    def permissions(self, user, inherited=None):
        perms = super(UserExternalId, self).permissions(user, inherited)
        if user and user == self.user:
            perms.add('delete_extid')
        return perms


user_email_primary_table = add_primary_relationship(
    User, 'primary_email', UserEmail, 'user', 'user_id'
)
user_phone_primary_table = add_primary_relationship(
    User, 'primary_phone', UserPhone, 'user', 'user_id'
)

# Tail imports
from .profile import Profile  # isort:skip
from .organization_membership import OrganizationMembership  # isort:skip
