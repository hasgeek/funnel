"""Shared fixtures and step definitions for view tests."""

from __future__ import annotations

import typing as t

from pytest_bdd import given, parsers, when

if t.TYPE_CHECKING:
    from funnel import models


@given(parsers.parse('{user} is logged in'), target_fixture='current_user')
def given_user_logged_in(getuser, login, user: str) -> models.User:
    user_obj = getuser(user)
    login.as_(user_obj)
    return user_obj


@given('they are logged in')
@given('he is logged in')
@given('she is logged in')
@when('they login')
@when('he logs in')
@when('she logs in')
def current_user_logged_in(login, current_user: models.User) -> None:
    login.as_(current_user)
