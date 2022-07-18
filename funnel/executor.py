"""Wrapper for Flask-Executor that manages database sessions."""

from __future__ import annotations

from functools import wraps
from typing import Any, cast

from flask_executor import Executor
from flask_executor.executor import ExecutorJob, FutureProxy

from .typing import WrappedFunc


def remove_db_session(f: WrappedFunc) -> WrappedFunc:
    """
    Remove the database session after calling the wrapped function.

    A transaction error in a background job will affect future queries, so the
    transaction must be rolled back.

    Required until this underlying issue is resolved:
    https://github.com/dchevell/flask-executor/issues/15
    """
    # Don't import models at top-level before app is ready
    from .models import db  # pylint: disable=import-outside-toplevel

    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        """Remove database session regardless of outcome."""
        try:
            result = f(*args, **kwargs)
        finally:
            db.session.remove()
        return result

    return cast(WrappedFunc, wrapper)


class ExecutorWrapper:
    """
    Executor wrapper that wraps functions with :func:remove_db_session.

    Consult the Flask-Executor documentation for usage notes.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Create an Executor."""
        self.executor = Executor(*args, **kwargs)

    def init_app(self, app):
        """Initialize executor with an app."""
        return self.executor.init_app(app)

    def submit(self, fn: WrappedFunc, *args, **kwargs) -> FutureProxy:
        """Submit a parallel task."""
        return self.executor.submit(remove_db_session(fn), *args, **kwargs)

    def submit_stored(
        self, future_key, fn: WrappedFunc, *args, **kwargs
    ) -> FutureProxy:
        """Submit a parallel task and store the result against the given future_key."""
        return self.executor.submit_stored(
            future_key, remove_db_session(fn), *args, **kwargs
        )

    def map(self, fn: WrappedFunc, *iterables, **kwargs):  # noqa: A003
        """Perform a map operation."""
        return self.executor.map(remove_db_session(fn), *iterables, **kwargs)

    def job(self, fn: WrappedFunc) -> ExecutorJob:
        """Decorate a job worker."""
        return self.executor.job(remove_db_session(fn))
