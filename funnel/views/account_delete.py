"""Helper functions for account delete validation."""

from typing import Callable, NamedTuple

from baseframe import __

from ..models import User

# --- Delete validator registry --------------------------------------------------------


class DeleteValidator(NamedTuple):
    validate: Callable[[User], bool]
    name: str
    title: str
    message: str


#: A list of validators that confirm there is no objection to deleting a user
#: account (returning True to allow deletion to proceed).
account_delete_validators = []


def delete_validator(title: str, message: str, name: str = None):
    """Register an account delete validator."""

    def decorator(func: Callable[[User], bool]):
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
def profile_is_protected(user: User) -> bool:
    """Block deletion if the user has a protected profile."""
    if user.profile is not None and user.profile.is_protected:
        return False
    return True


@delete_validator(
    title=__("This account has organizations without co-owners"),
    message=__(
        "Organizations must be deleted or transferred to other owners before the"
        " account can be deleted"
    ),
)
def single_owner_organization(user):
    for org in user.organizations_as_owner:
        # TODO: Optimize query for large organizations
        if list(org.owner_users) == [user]:
            return False
    return True


@delete_validator(
    title=__("This account has projects"),
    message=__(
        "Projects are collaborative spaces with other users.  Projects must be"
        " transferred to a new host before the account can be deleted"
    ),
)
def profile_has_projects(user):
    if user.profile is not None:
        # TODO: Break down `is_safe_to_delete()` into individual components
        # and apply to org delete as well
        return user.profile.is_safe_to_delete()
    return True


# --- Delete validator view helper -----------------------------------------------------
@User.views()
def validate_account_delete(obj):
    for validator in account_delete_validators:
        proceed = validator.validate(obj)
        if not proceed:
            return validator
