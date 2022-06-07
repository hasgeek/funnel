"""Test sessions."""
# pylint: disable=possibly-unused-variable
from datetime import datetime, timedelta
from types import SimpleNamespace

import sqlalchemy.exc

from pytz import utc
import pytest

from funnel.models import Project, Session, db

# TODO: Create a second parallel project and confirm they don't clash


@pytest.fixture()
def block_of_sessions(db_session, new_project):

    # DocType HTML5's schedule, but using UTC to simplify testing
    # https://hasgeek.com/doctypehtml5/bangalore/schedule
    session1 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 10, 0)),
        title="Registration",
        is_break=True,
    )
    session2 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 10, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 10, 15)),
        title="Introduction",
    )
    session3 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 10, 15)),
        end_at=utc.localize(datetime(2010, 10, 9, 11, 15)),
        title="Business Case for HTML5",
    )
    session4 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 11, 15)),
        end_at=utc.localize(datetime(2010, 10, 9, 12, 15)),
        title="New Ideas in HTML5",
    )
    session5 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 12, 15)),
        end_at=utc.localize(datetime(2010, 10, 9, 12, 30)),
        title="Tea & Coffee Break",
        is_break=True,
    )
    session6 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 12, 30)),
        end_at=utc.localize(datetime(2010, 10, 9, 13, 30)),
        title="CSS3 and Presentation",
    )
    # Deliberately leave out lunch break at session 7 to break the block
    session8 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 14, 30)),
        end_at=utc.localize(datetime(2010, 10, 9, 14, 45)),
        title="Quiz",
    )
    session9 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 14, 45)),
        end_at=utc.localize(datetime(2010, 10, 9, 15, 45)),
        title="Multimedia Kit",
    )
    session10 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 15, 45)),
        end_at=utc.localize(datetime(2010, 10, 9, 16, 0)),
        title="Tea & Coffee Break",
        is_break=True,
    )
    session11 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 16, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 17, 0)),
        title="Location, Offline and Mobile",
    )
    session12 = Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 17, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 17, 15)),
        title="Closing Remarks",
    )

    refresh_attrs = [attr for attr in locals().values() if isinstance(attr, db.Model)]
    db_session.add_all(refresh_attrs)
    db_session.commit()

    def refresh():
        for attr in refresh_attrs:
            db_session.add(attr)

    return SimpleNamespace(**locals())


def find_projects(starting_times, within, gap):
    # Keep the timestamps at which projects were found, plus the project. Criteria:
    # starts at `timestamp` + up to `within` period, with `gap` from prior sessions
    return {
        timestamp: found
        for timestamp, found in {
            timestamp: Project.starting_at(timestamp, within, gap).all()
            for timestamp in starting_times
        }.items()
        if found
    }


def test_project_starting_at(db_session, block_of_sessions):
    block_of_sessions.refresh()

    # Loop through the day at 5 min intervals from 8 AM, looking for start time
    starting_times = [
        utc.localize(datetime(2010, 10, 9, 8, 0)) + timedelta(minutes=5) * multipler
        for multipler in range(100)
    ]

    # At first nothing will match because the project is not published
    assert (
        find_projects(starting_times, timedelta(minutes=5), timedelta(minutes=60)) == {}
    )

    # Publishing the project makes it work
    block_of_sessions.new_project.publish()
    found_projects = find_projects(
        starting_times, timedelta(minutes=5), timedelta(minutes=60)
    )

    # Confirm we found two starting times at 9 AM and 2:30 PM
    assert found_projects == {
        utc.localize(datetime(2010, 10, 9, 9, 0)): [block_of_sessions.new_project],
        utc.localize(datetime(2010, 10, 9, 14, 30)): [block_of_sessions.new_project],
    }

    # Confirm we can retrieve the session as well
    found_sessions = {
        timestamp: [project.next_session_from(timestamp) for project in project_list]
        for timestamp, project_list in found_projects.items()
    }
    assert found_sessions == {
        utc.localize(datetime(2010, 10, 9, 9, 0)): [block_of_sessions.session1],
        utc.localize(datetime(2010, 10, 9, 14, 30)): [block_of_sessions.session8],
    }

    # Repeat search with 120 minute gap requirement instead of 60. Now we find a single
    # match
    found_projects = find_projects(
        starting_times, timedelta(minutes=5), timedelta(minutes=120)
    )

    # Confirm we found a single starting time at 9 AM
    assert found_projects == {
        utc.localize(datetime(2010, 10, 9, 9, 0)): [block_of_sessions.new_project],
    }

    # Use an an odd offset on the starting time. We're looking for 1 hour gap before the
    # query time and not session starting time, so this will miss the second block
    starting_times = [
        utc.localize(datetime(2010, 10, 9, 7, 59)) + timedelta(minutes=5) * multipler
        for multipler in range(100)
    ]

    found_projects = find_projects(
        starting_times, timedelta(minutes=5), timedelta(minutes=60)
    )

    # Confirm:
    # 1. The first block is found (test uses query timestamp, not session timestamp)
    # 2. The second block was missed because 13:29 to 14:29 has a match at 13:30 end_at.
    assert found_projects == {
        utc.localize(datetime(2010, 10, 9, 8, 59)): [block_of_sessions.new_project],
    }


def test_long_session_fail(db_session, new_project):
    """Sessions cannot exceed 24 hours."""
    # Less than 24 hours is fine:
    db_session.add(
        Session(
            project=new_project,
            start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
            end_at=utc.localize(datetime(2010, 10, 10, 8, 59, 59)),
            title="Less than 24 hours by 1 second",
        )
    )
    db_session.commit()

    # Exactly 24 hours is fine:
    db_session.add(
        Session(
            project=new_project,
            start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
            end_at=utc.localize(datetime(2010, 10, 10, 9, 0)),
            title="Exactly 24 hours",
        )
    )
    db_session.commit()

    # Anything above 24 hours will fail:
    db_session.add(
        Session(
            project=new_project,
            start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
            end_at=utc.localize(datetime(2010, 10, 10, 9, 0, 1)),
            title="Longer than 24 hours by 1 second",
        )
    )
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.commit()
