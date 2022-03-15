from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask_executor import Executor
from flask_executor.executor import ExecutorJob, FutureProxy

# https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
F = TypeVar('F', bound=Callable[..., Any])


def remove_db_session(f: F) -> F:
    """
    Remove the database session after calling the wrapped function.

    A transaction error in a background job will affect future queries, so the
    transaction must be rolled back.

    Required until this underlying issue is resolved:
    https://github.com/dchevell/flask-executor/issues/15
    """
    from .models import db  # Don't import models at top-level before app is ready

    @wraps(f)
    def wrapper(*args, **kwargs):
        """Remove database session regardless of outcome."""
        try:
            result = f(*args, **kwargs)
        finally:
            db.session.remove()
        return result

    return cast(F, wrapper)


class ExecutorWrapper:
    """
    Executor wrapper that wraps functions with :func:remove_db_session.

    Consult the Flask-Executor documentation for usage notes.
    """

    def __init__(self, *args, **kwargs):
        """Create an Executor."""
        self.executor = Executor(*args, **kwargs)

    def init_app(self, app):
        """Initialize executor with an app."""
        return self.executor.init_app(app)

    def submit(self, fn: F, *args, **kwargs) -> FutureProxy:
        """Submit a parallel task."""
        return self.executor.submit(remove_db_session(fn), *args, **kwargs)

    def submit_stored(self, future_key, fn: F, *args, **kwargs) -> FutureProxy:
        """Submit a parallel task and store the result against the given future_key."""
        return self.executor.submit_stored(
            future_key, remove_db_session(fn), *args, **kwargs
        )

    def map(self, fn: F, *iterables, **kwargs):
        """Perform a map operation."""
        return self.executor.map(remove_db_session(fn), *iterables, **kwargs)

    def job(self, fn: F) -> ExecutorJob:
        """Decorate a job worker."""
        return self.executor.job(remove_db_session(fn))
