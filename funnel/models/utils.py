from __future__ import annotations

from typing import NamedTuple, Optional, Set, Union, overload

from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint

from flask import current_app

from typing_extensions import Literal
import phonenumbers

from ..typing import OptionalMigratedTables
from .user import User, UserEmail, UserEmailClaim, UserExternalId, UserPhone, db

__all__ = [
    'IncompleteUserMigrationError',
    'UserAndAnchor',
    'getextid',
    'getuser',
    'merge_users',
    'normalize_phone_number',
]


class IncompleteUserMigrationError(Exception):
    """Could not migrate users because of data conflicts."""


class UserAndAnchor(NamedTuple):
    user: Optional[User]
    anchor: Union[None, UserEmail, UserEmailClaim, UserPhone]


def normalize_phone_number(candidate: str) -> Optional[str]:
    """Attempt to parse a phone number from a candidate and return in E164 format."""
    # Assume unprefixed numbers to be a local number in India (+91) or US (+1).
    # Both IN and US numbers are 10 digits before prefixes. We start with IN and
    # return the _first_ candidate that is likely to be a valid number. This behaviour
    # differentiates it from similar code in :func:`getuser`, where the loop exits with
    # the _last_ valid candidate (as it's coupled with a UserPhone lookup)
    try:
        for region in ['IN', 'US']:  # This list repeats in :func:`getuser`
            parsed_number = phonenumbers.parse(candidate, region)
            if phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
    except phonenumbers.NumberParseException:
        pass
    return None


@overload
def getuser(name: str) -> Optional[User]:
    ...


@overload
def getuser(name: str, anchor: Literal[False]) -> Optional[User]:
    ...


@overload
def getuser(name: str, anchor: Literal[True]) -> UserAndAnchor:
    ...


def getuser(name: str, anchor: bool = False) -> Union[Optional[User], UserAndAnchor]:
    """
    Get a user with a matching name, email address or phone number.

    Optionally returns an anchor (phone or email) instead of the user account.
    """
    # Treat an '@' or '~' prefix as a username lookup, removing the prefix
    if name.startswith('@') or name.startswith('~'):
        name = name[1:]
    # If there's an '@' in the middle, treat as an email address
    elif '@' in name:
        useremail: Union[None, UserEmail, UserEmailClaim]
        useremail = UserEmail.get(email=name)
        if useremail is None:
            # If there's no verified email address, look for a claim.
            useremail = (
                UserEmailClaim.all(email=name)
                .order_by(UserEmailClaim.created_at)
                .first()
            )
        if useremail is not None and useremail.user.state.ACTIVE:
            # Return user only if in active state
            if anchor:
                return UserAndAnchor(useremail.user, useremail)
            return useremail.user
        if anchor:
            return UserAndAnchor(None, None)
        return None
    else:
        # If it wasn't an email address or an @username, check if it's a phone number
        try:
            # Assume unprefixed numbers to be a local number in India (+91) or US (+1).
            # Both IN and US numbers are 10 digits before prefixes; try IN first
            for region in ['IN', 'US']:
                parsed_number = phonenumbers.parse(name, region)
                if phonenumbers.is_valid_number(parsed_number):
                    number = phonenumbers.format_number(
                        parsed_number, phonenumbers.PhoneNumberFormat.E164
                    )
                    userphone = UserPhone.get(number)
                    if userphone is not None and userphone.user.state.ACTIVE:
                        if anchor:
                            return UserAndAnchor(userphone.user, userphone)
                        return userphone.user
            # No matching userphone? Continue to trying as a username
        except phonenumbers.NumberParseException:
            # This was not a parseable phone number. Continue to trying as a username
            pass

    # Last guess: username
    user = User.get(username=name)

    # If the caller wanted an anchor, try to return one (phone, then email) instead of
    # the user account
    if anchor:
        if user is None:
            return UserAndAnchor(None, None)
        if user.phone:
            return UserAndAnchor(user, user.phone)
        if user.email:
            return UserAndAnchor(user, user.email)
        if user.emailclaims:
            return UserAndAnchor(user, user.emailclaims[0])
        # This user has no anchors
        return UserAndAnchor(user, None)

    # Anchor not requested. Return the user account
    return user


def getextid(service: str, userid: str) -> Optional[UserExternalId]:
    return UserExternalId.get(service=service, userid=userid)


def merge_users(user1: User, user2: User) -> Optional[User]:
    """Merge two user accounts and return the new user account."""
    current_app.logger.info("Preparing to merge users %s and %s", user1, user2)
    # Always keep the older account and merge from the newer account
    if user1.created_at < user2.created_at:
        keep_user, merge_user = user1, user2
    else:
        keep_user, merge_user = user2, user1

    # 1. Inspect all tables for foreign key references to merge_user and switch to
    # keep_user.
    safe = do_migrate_instances(merge_user, keep_user, 'migrate_user')
    if safe:
        # 2. Add merge_user's uuid to olduserids and mark user as merged
        merge_user.mark_merged_into(keep_user)
        # 3. Commit all of this
        db.session.commit()

        # 4. Return keep_user.
        current_app.logger.info("User merge complete, keeping user %s", keep_user)
        return keep_user

    current_app.logger.error("User merge failed, aborting transaction")
    db.session.rollback()
    return None


def do_migrate_instances(
    old_instance: db.Model, new_instance: db.Model, helper_method: Optional[str] = None
) -> bool:
    """
    Migrate references to old instance of any model to provided new instance.

    The model must derive from :class:`db.Model` and must have a single primary key
    column named ``id`` (typically provided by :class:`BaseMixin`).
    """
    if old_instance == new_instance:
        raise ValueError("Old and new are the same")

    # User id column (for foreign keys)
    id_column = (
        old_instance.__class__.__table__.c.id
    )  # 'id' is from IdMixin via BaseMixin

    # Session (for queries)
    session = old_instance.query.session

    # Keep track of all migrated tables
    migrated_tables: Set[str] = set()
    safe_to_remove_instance = True

    def do_migrate_table(table):
        target_columns = []
        for column in table.columns:
            for fkey in column.foreign_keys:
                if fkey.column is id_column:
                    # This table needs migration on this column
                    target_columns.append(column)
                    break

        # Check for unique constraint on instance id columns (single or multi-index)
        # If so, return False (migration incomplete)
        for column in target_columns:
            if column.unique:
                # Note: This will fail for secondary relationship tables, which
                # will have a unique index but no model on which to place
                # helper_method, unless one of the related models handles
                # migrations AND signals a way for this table to be skipped
                # here. This is why model.helper_method below (migrate_user or
                # migrate_profile) returns a list of table names it has
                # processed.
                current_app.logger.error(
                    "do_migrate_table interrupted because column is unique: {column}",
                    extra={'column': column},
                )
                return False

        # Now check for multi-column indexes
        for constraint in table.constraints:
            if isinstance(constraint, (PrimaryKeyConstraint, UniqueConstraint)):
                for column in constraint.columns:
                    if column in target_columns:
                        # The target column (typically user_id) is part of a unique
                        # or primary key constraint. We can't migrate automatically.
                        current_app.logger.error(
                            "do_migrate_table interrupted because column is part of a"
                            " unique constraint: %s",
                            column,
                        )
                        return False

        # This following code is disabled but preserved because we don't fully
        # understand multi-db bind setups. It isn't a current requirement because we
        # don't have fkeys spanning databases, but we may in future (in which case it's
        # a relationship and not a db-enforced foreign key). Original comment follows:

        # If this table uses Flask-SQLAlchemy's bind_key mechanism,
        # session.execute won't bind to the correct engine, so the table cannot be
        # migrated. If we attempt to retrieve and connect to the correct engine, we may
        # lose the transaction. We need to confirm this.

        # if table.info.get('bind_key'):
        #     current_app.logger.error(
        #         "do_migrate_table interrupted because table has bind_key: %s",
        #         table.name,
        #     )
        #     return False

        for column in target_columns:
            session.execute(
                table.update()
                .where(column == old_instance.id)
                .values(**{column.name: new_instance.id})
            )
            session.flush()

        # All done, table successfully migrated. Hurrah!
        return True

    # Look up all subclasses of the base class
    for model in db.Model.__subclasses__():
        if model != old_instance.__class__:
            if helper_method and hasattr(model, helper_method):
                try:
                    result: OptionalMigratedTables = getattr(model, helper_method)(
                        old_instance, new_instance
                    )
                    session.flush()
                    if isinstance(result, (list, tuple, set)):
                        migrated_tables.update(result)
                    migrated_tables.add(model.__table__.name)
                except IncompleteUserMigrationError:
                    safe_to_remove_instance = False
                    current_app.logger.error(
                        "_do_merge_into interrupted because"
                        "  IncompleteUserMigrationError raised by %s",
                        model,
                    )
            else:
                # No model-backed migration. Figure out all foreign key references to
                # user table
                if not do_migrate_table(model.__table__):
                    safe_to_remove_instance = False
                migrated_tables.add(model.__table__.name)

    # Now look in the metadata for any tables we missed
    for table in db.Model.metadata.tables.values():
        if table.name not in migrated_tables:
            if not do_migrate_table(table):
                safe_to_remove_instance = False
            migrated_tables.add(table.name)

    return safe_to_remove_instance
