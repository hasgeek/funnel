from __future__ import annotations

from typing import Optional, Set, Union

from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint

from flask import current_app

from ..typing import OptionalMigratedTables
from .user import User, UserEmail, UserEmailClaim, UserExternalId, db

__all__ = ['getuser', 'getextid', 'merge_users', 'IncompleteUserMigration']


class IncompleteUserMigration(Exception):
    """Could not migrate users because of data conflicts."""


def getuser(name: str) -> Optional[User]:
    """Get a user with a matching name or email address."""
    # Treat an '@' or '~' prefix as a username lookup, removing the prefix
    if name.startswith('@') or name.startswith('~'):
        name = name[1:]
    # If there's an '@' in the middle, treat as an email address
    elif '@' in name:
        # TODO: This lookup may be more efficient for email claims if we query the
        # EmailAddress model directly, doing a join with UserEmail and UserEmailClaim.
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
            return useremail.user
        return None
    # If it wasn't an email address lookup, do a username lookup
    return User.get(username=name)


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
    # This used to retrieve session from the model's query, but that affects testing,
    # so, we're back to using the global session.
    # Old: session = old_instance.query.session
    session = db.session

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

        # TODO: If this table uses Flask-SQLAlchemy's bind_key mechanism,
        # session.execute won't bind to the correct engine, so the table cannot be
        # migrated. If we attempt to retrieve and connect to the correct engine, we may
        # lose the transaction. We need to confirm this.
        if table.info.get('bind_key'):
            current_app.logger.error(
                "do_migrate_table interrupted because table has bind_key: %s",
                table.name,
            )
            return False

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
                except IncompleteUserMigration:
                    safe_to_remove_instance = False
                    current_app.logger.error(
                        "_do_merge_into interrupted because IncompleteUserMigration"
                        " raised by %s",
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
