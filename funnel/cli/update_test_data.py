#!/usr/bin/env python
"""Script to update test dataset output for markdown parser tests to current version."""

from .. import app
from ..utils.markdown.testhelpers import update_test_data


@app.cli.command('update_test_data')
def utd():
    """
    Update test data.

    Currently updates markdown test data.
    Can be used to club any other requirements to automatically update static test data.
    """
    update_test_data()
