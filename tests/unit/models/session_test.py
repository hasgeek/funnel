"""Test sessions."""
# pylint: disable=possibly-unused-variable,redefined-outer-name

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Dict, List, Optional

from pytz import utc
from sqlalchemy.exc import IntegrityError
import pytest
import sqlalchemy as sa

from funnel import models

# TODO: Create a second parallel project and confirm they don't clash


@pytest.fixture()
def block_of_sessions(db_session, new_project) -> SimpleNamespace:
    # DocType HTML5's schedule, but using UTC to simplify testing
    # https://hasgeek.com/doctypehtml5/bangalore/schedule
    session1 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 10, 0)),
        title="Registration",
        is_break=True,
    )
    session2 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 10, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 10, 15)),
        title="Introduction",
    )
    session3 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 10, 15)),
        end_at=utc.localize(datetime(2010, 10, 9, 11, 15)),
        title="Business Case for HTML5",
    )
    session4 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 11, 15)),
        end_at=utc.localize(datetime(2010, 10, 9, 12, 15)),
        title="New Ideas in HTML5",
    )
    session5 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 12, 15)),
        end_at=utc.localize(datetime(2010, 10, 9, 12, 30)),
        title="Tea & Coffee Break",
        is_break=True,
    )
    session6 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 12, 30)),
        end_at=utc.localize(datetime(2010, 10, 9, 13, 30)),
        title="CSS3 and Presentation",
    )
    # Deliberately leave out lunch break at session 7 to break the block
    session8 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 14, 30)),
        end_at=utc.localize(datetime(2010, 10, 9, 14, 45)),
        title="Quiz",
    )
    session9 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 14, 45)),
        end_at=utc.localize(datetime(2010, 10, 9, 15, 45)),
        title="Multimedia Kit",
    )
    session10 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 15, 45)),
        end_at=utc.localize(datetime(2010, 10, 9, 16, 0)),
        title="Tea & Coffee Break",
        is_break=True,
    )
    session11 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 16, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 17, 0)),
        title="Location, Offline and Mobile",
    )
    session12 = models.Session(
        project=new_project,
        start_at=utc.localize(datetime(2010, 10, 9, 17, 0)),
        end_at=utc.localize(datetime(2010, 10, 9, 17, 15)),
        title="Closing Remarks",
    )

    refresh_attrs = [
        attr for attr in locals().values() if isinstance(attr, models.Model)
    ]
    db_session.add_all(refresh_attrs)
    db_session.commit()

    def refresh():
        for attr in refresh_attrs:
            db_session.add(attr)

    return SimpleNamespace(**locals())


def find_projects(starting_times, within, gap) -> Dict[datetime, List[models.Project]]:
    # Keep the timestamps at which projects were found, plus the project. Criteria:
    # starts at `timestamp` + up to `within` period, with `gap` from prior sessions
    return {
        timestamp: found
        for timestamp, found in {
            timestamp: models.Project.starting_at(timestamp, within, gap).all()
            for timestamp in starting_times
        }.items()
        if found
    }


def test_project_starting_at(block_of_sessions) -> None:
    """Test Project.starting_at finds projects by starting time accurately."""
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


def test_long_session_fail(db_session, new_project) -> None:
    """Confirm sessions cannot exceed 24 hours."""
    # Less than 24 hours is fine:
    db_session.add(
        models.Session(
            project=new_project,
            start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
            end_at=utc.localize(datetime(2010, 10, 10, 8, 59, 59)),
            title="Less than 24 hours by 1 second",
        )
    )
    db_session.commit()

    # Exactly 24 hours is fine:
    db_session.add(
        models.Session(
            project=new_project,
            start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
            end_at=utc.localize(datetime(2010, 10, 10, 9, 0)),
            title="Exactly 24 hours",
        )
    )
    db_session.commit()

    # Anything above 24 hours will fail:
    db_session.add(
        models.Session(
            project=new_project,
            start_at=utc.localize(datetime(2010, 10, 9, 9, 0)),
            end_at=utc.localize(datetime(2010, 10, 10, 9, 0, 1)),
            title="Longer than 24 hours by 1 second",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


project_session_dates = [
    pytest.param(None, [], None, id='no-dates'),
    pytest.param(
        (
            sa.func.utcnow() - timedelta(minutes=2),
            sa.func.utcnow() - timedelta(minutes=1),
        ),
        [],
        None,
        id='past-project',
    ),
    pytest.param(
        (
            sa.func.utcnow() - timedelta(minutes=1),
            sa.func.utcnow() + timedelta(minutes=1),
        ),
        [],
        None,
        id='live-project',
    ),
    pytest.param(
        (
            sa.func.utcnow() + timedelta(minutes=1),
            sa.func.utcnow() + timedelta(minutes=2),
        ),
        [],
        -1,  # Signifies match with project.start_at
        id='future-project',
    ),
    pytest.param(
        None,
        [
            (
                sa.func.utcnow() - timedelta(minutes=2),
                sa.func.utcnow() - timedelta(minutes=1),
            ),
        ],
        None,
        id='past-session',
    ),
    pytest.param(
        None,
        [
            (
                sa.func.utcnow() - timedelta(minutes=2),
                sa.func.utcnow() - timedelta(minutes=1),
            ),
            (
                sa.func.utcnow() - timedelta(minutes=1),
                sa.func.utcnow() + timedelta(minutes=1),
            ),
            (
                sa.func.utcnow() + timedelta(minutes=1),
                sa.func.utcnow() + timedelta(minutes=2),
            ),
            (
                sa.func.utcnow() + timedelta(minutes=2),
                sa.func.utcnow() + timedelta(minutes=3),
            ),
        ],
        2,  # Matches immediate next session, skipping past (0) and ongoing (1)
        id='next-session',
    ),
]


@pytest.mark.parametrize(
    ('project_dates', 'session_dates', 'expected_session'), project_session_dates
)
@pytest.mark.parametrize(
    ('project2_dates', 'session2_dates', 'expected2_session'), project_session_dates
)
def test_next_session_at_property(
    db_session,
    project_expo2010,
    project_expo2011,
    project_dates: Optional[tuple],
    session_dates: List[tuple],
    expected_session: Optional[int],
    project2_dates: Optional[tuple],
    session2_dates: List[tuple],
    expected2_session: Optional[int],
) -> None:
    """Test next_session_at to work for projects with sessions and without."""
    if project_dates:
        project_expo2010.start_at, project_expo2010.end_at = project_dates
    if project2_dates:
        # Add dates to unrelated project, to confirm it has no bearing on first project
        project_expo2011.start_at, project_expo2011.end_at = project2_dates
    sessions = []
    for counter, dates in enumerate(session_dates):
        new_session = models.Session(
            project=project_expo2010,
            start_at=dates[0],
            end_at=dates[1],
            title=str(counter),
            description=str(counter),
        )
        db_session.add(new_session)
        sessions.append(new_session)
    for counter, dates in enumerate(session2_dates):
        # Add sessions to unrelated project, to confirm it has no bearing on first
        # project
        db_session.add(
            models.Session(
                project=project_expo2011,
                start_at=dates[0],
                end_at=dates[1],
                title=str(counter),
                description=str(counter),
            )
        )
    db_session.commit()  # This forces conversion from SQL dates to datetimes

    if expected_session is None:
        assert project_expo2010.next_session_at is None
    elif expected_session == -1:
        assert project_expo2010.next_session_at == project_expo2010.start_at
    else:
        assert project_expo2010.next_session_at == sessions[expected_session].start_at


# TODO: Test next_session_at as a SQL expression, as used in in the index view's
# order_by clause
