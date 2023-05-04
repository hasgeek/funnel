"""Helper functions for account delete validation."""

from dataclasses import dataclass
from typing import Callable, List, Optional

from baseframe import __

from ..models import Account, Organization, User
from ..typing import ReturnDecorator, WrappedFunc

# --- Delete validator registry --------------------------------------------------------


@dataclass
class DeleteValidator:
    """Delete validator metadata."""

    validate: Callable[[Account], bool]
    name: str
    title: str
    message: str


#: A list of validators that confirm there is no objection to deleting a user
#: account (returning True to allow deletion to proceed).
account_delete_validators: List[DeleteValidator] = []


def delete_validator(
    title: str, message: str, name: Optional[str] = None
) -> ReturnDecorator:
    """Register an account delete validator."""

    def decorator(func: WrappedFunc) -> WrappedFunc:
        """Create a DeleteValidator."""
        account_delete_validators.append(
            DeleteValidator(func, name or func.__name__, title, message)
        )
        return func

    return decorator


# --- Delete validator functions -------------------------------------------------------


@delete_validator(
    title=__("This account is protected"),
    message=__("Protected accounts cannot be deleted"),
)
def profile_is_protected(user: Account) -> bool:
    """Block deletion if the user has a protected account."""
    if user.is_protected:
        return False
    return True


@delete_validator(
    title=__("This account has organizations without co-owners"),
    message=__(
        "Organizations must be deleted or transferred to other owners before the"
        " account can be deleted"
    ),
)
def single_owner_organization(user: Account) -> bool:
    """Fail if user is the sole owner of one or more organizations."""
    # TODO: Optimize org.owner_users lookup for large organizations
    return all(tuple(org.owner_users) != (user,) for org in user.organizations_as_owner)


@delete_validator(
    title=__("This account has projects"),
    message=__(
        "Projects are collaborative spaces with other users. Projects must be"
        " transferred to a new host before the account can be deleted"
    ),
)
def profile_has_projects(user: Account) -> bool:
    """Fail if user has projects in their account."""
    return user.is_safe_to_delete()


@delete_validator(
    title=__("This account is the owner of client apps"),
    message=__(
        "Client apps must be deleted or transferred to other owners before the account"
        " can be deleted"
    ),
)
def user_owns_apps(user: Account) -> bool:
    """Fail if user is the owner of client apps."""
    if user.clients:
        return False
    return True


# --- Delete validator view helper -----------------------------------------------------


@Account.views()
@User.views()
@Organization.views()
def validate_account_delete(obj: Account) -> Optional[DeleteValidator]:
    """Validate if user account is safe to delete, returning an optional objection."""
    for validator in account_delete_validators:
        proceed = validator.validate(obj)
        if not proceed:
            return validator
    return None
