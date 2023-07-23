"""
Validate Indian phone numbers against the Mobile Number Revocation List.

About MNRL: https://mnrl.trai.gov.in/homepage
API details (requires login): https://mnrl.trai.gov.in/api_details, contents reproduced
here:

.. list-table:: API Description
    :header-rows: 1

    * - №
      - API Name
      - API URL
      - Method
      - Remark
    * - 1
      - Get MNRL Status
      - https://mnrl.trai.gov.in/api/mnrl/status/{key}
      - GET
      - Returns the current status of MNRL.
    * - 2
      - Get MNRL Files
      - https://mnrl.trai.gov.in/api/mnrl/files/{key}
      - GET
      - Returns the summary of MNRL files, to be used for further API calls to get the
        list of mobile numbers or download the file.
    * - 3
      - Get MNRL
      - https://mnrl.trai.gov.in/api/mnrl/json/{file_name}/{key}
      - GET
      - Returns the list of mobile numbers of the requested (.json) file.
    * - 4
      - Download MNRL
      - https://mnrl.trai.gov.in/api/mnrl/download/{file_name}/{key}
      - GET
      - Can be used to download the file. (xlsx, pdf, json, rar)
"""

import asyncio
from typing import List, Set, Tuple

import click
import httpx
import ijson
from rich import get_console, print as rprint
from rich.progress import Progress

from ... import app
from ...models import PhoneNumber, UserPhone, db
from . import periodic


class KeyInvalidError(ValueError):
    """MNRL API key is invalid."""

    message = "MNRL API key is invalid"


class KeyExpiredError(ValueError):
    """MNRL API key has expired."""

    message = "MNRL API key has expired"


class AsyncStreamAsFile:
    """Provide a :meth:`read` interface to a HTTPX async stream response for ijson."""

    def __init__(self, response: httpx.Response) -> None:
        self.data = response.aiter_bytes()

    async def read(self, size: int) -> bytes:
        """Async read method for ijson (which expects this to be 'read' not 'aread')."""
        if size == 0:
            # ijson calls with size 0 and expect b'', using it only to
            # print a warning if the return value is '' (str instead of bytes)
            return b''
        # Python >= 3.10 supports `return await anext(self.data, b'')` but for older
        # versions we need this try/except block
        try:
            # Ignore size parameter since anext doesn't take it
            # pylint: disable=unnecessary-dunder-call
            return await self.data.__anext__()
        except StopAsyncIteration:
            return b''


async def get_existing_phone_numbers(prefix: str) -> Set[str]:
    """Async wrapper for PhoneNumber.get_numbers."""
    # TODO: This is actually an async-blocking call. We need full stack async here.
    return PhoneNumber.get_numbers(prefix=prefix, remove=True)


async def get_mnrl_json_file_list(apikey: str) -> List[str]:
    """
    Return filenames for the currently published MNRL JSON files.

    TRAI publishes the MNRL as a monthly series of files in Excel, PDF and JSON
    formats, of which we'll use JSON (plaintext format isn't offered).
    """
    response = await httpx.AsyncClient(http2=True).get(
        f'https://mnrl.trai.gov.in/api/mnrl/files/{apikey}', timeout=300
    )
    if response.status_code == 401:
        raise KeyInvalidError()
    if response.status_code == 407:
        raise KeyExpiredError()
    response.raise_for_status()

    result = response.json()
    # Fallback tests for non-200 status codes in a 200 response (current API behaviour)
    if result['status'] == 401:
        raise KeyInvalidError()
    if result['status'] == 407:
        raise KeyExpiredError()
    return [row['file_name'] for row in result['mnrl_files']['json']]


async def get_mnrl_json_file_numbers(
    client: httpx.AsyncClient, apikey: str, filename: str
) -> Tuple[str, Set[str]]:
    """Return phone numbers from an MNRL JSON file URL."""
    async with client.stream(
        'GET',
        f'https://mnrl.trai.gov.in/api/mnrl/json/{filename}/{apikey}',
        timeout=300,
    ) as response:
        response.raise_for_status()
        # The JSON structure is {"payload": [{"n": "number"}, ...]}
        # The 'item' in 'payload.item' is ijson's code for array elements
        return filename, {
            value
            async for key, value in ijson.kvitems(
                AsyncStreamAsFile(response), 'payload.item'
            )
            if key == 'n' and value is not None
        }


async def forget_phone_numbers(phone_numbers: Set[str], prefix: str) -> None:
    """Mark phone numbers as forgotten."""
    for unprefixed in phone_numbers:
        number = prefix + unprefixed
        userphone = UserPhone.get(number)
        if userphone is not None:
            # TODO: Dispatch a notification to userphone.user, but since the
            # notification will not know the phone number (it'll already be forgotten),
            # we need a new db model to contain custom messages
            # TODO: Also delay dispatch until the full MNRL scan is complete -- their
            # backup contact phone number may also have expired. That means this
            # function will create notifications and return them, leaving dispatch to
            # the outermost function
            rprint(f"{userphone} - owned by {userphone.user.pickername}")
            # TODO: MNRL isn't foolproof. Don't delete! Instead, notify the user and
            # only delete if they don't respond (How? Maybe delete and send them a
            # re-add token?)
            # db.session.delete(userphone)
        phone_number = PhoneNumber.get(number)
        if phone_number is not None:
            rprint(
                f"{phone_number} - since {phone_number.created_at:%Y-%m-%d}, updated"
                f" {phone_number.updated_at:%Y-%m-%d}"
            )
            # phone_number.mark_forgotten()
    db.session.commit()


async def process_mnrl_files(
    apikey: str,
    existing_phone_numbers: Set[str],
    phone_prefix: str,
    mnrl_filenames: List[str],
) -> Tuple[Set[str], int, int]:
    """
    Scan all MNRL files and return a tuple of results.

    :return: Tuple of number to be revoked (set), total expired numbers in the MNRL,
        and count of failures when accessing the MNRL lists
    """
    revoked_phone_numbers: Set[str] = set()
    mnrl_total_count = 0
    failures = 0
    async_tasks: Set[asyncio.Task] = set()
    with Progress(transient=True) as progress:
        ptask = progress.add_task(
            f"Processing {len(mnrl_filenames)} MNRL files", total=len(mnrl_filenames)
        )
        async with httpx.AsyncClient(
            http2=True, limits=httpx.Limits(max_connections=3)
        ) as client:
            for future in asyncio.as_completed(
                [
                    get_mnrl_json_file_numbers(client, apikey, filename)
                    for filename in mnrl_filenames
                ]
            ):
                try:
                    filename, mnrl_set = await future
                except httpx.HTTPError as exc:
                    progress.advance(ptask)
                    failures += 1
                    # Extract filename from the URL (ends with /filename/apikey) as we
                    # can't get any context from asyncio.as_completed's future
                    filename = exc.request.url.path.split('/')[-2]
                    progress.update(ptask, description=f"Error in {filename}...")
                    if isinstance(exc, httpx.HTTPStatusError):
                        rprint(
                            f"[red]{filename}: Server returned HTTP status code"
                            f" {exc.response.status_code}"
                        )
                    else:
                        rprint(f"[red]{filename}: Failed with {exc!r}")
                else:
                    progress.advance(ptask)
                    mnrl_total_count += len(mnrl_set)
                    progress.update(ptask, description=f"Processing {filename}...")
                    found_expired = existing_phone_numbers.intersection(mnrl_set)
                    if found_expired:
                        revoked_phone_numbers.update(found_expired)
                        rprint(
                            f"[blue]{filename}: {len(found_expired):,} matches in"
                            f" {len(mnrl_set):,} total"
                        )
                        async_tasks.add(
                            asyncio.create_task(
                                forget_phone_numbers(found_expired, phone_prefix)
                            )
                        )
                    else:
                        rprint(
                            f"[cyan]{filename}: No matches in {len(mnrl_set):,} total"
                        )

    # Await all the background tasks
    for task in async_tasks:
        try:
            # TODO: Change this to `notifications = await task` then return them too
            await task
        except Exception as exc:  # noqa: B902  # pylint: disable=broad-except
            app.logger.exception("%s in forget_phone_numbers", repr(exc))
    return revoked_phone_numbers, mnrl_total_count, failures


async def process_mnrl(apikey: str) -> None:
    """Process MNRL data using the API key."""
    console = get_console()
    phone_prefix = '+91'
    task_numbers = asyncio.create_task(get_existing_phone_numbers(phone_prefix))
    task_files = asyncio.create_task(get_mnrl_json_file_list(apikey))
    with console.status("Loading phone numbers..."):
        existing_phone_numbers = await task_numbers
    rprint(f"Evaluating {len(existing_phone_numbers):,} phone numbers for expiry")
    try:
        with console.status("Getting MNRL download list..."):
            mnrl_filenames = await task_files
    except httpx.HTTPError as exc:
        err = f"{exc!r} in MNRL API getting download list"
        rprint(f"[red]{err}")
        raise click.ClickException(err)

    revoked_phone_numbers, mnrl_total_count, failures = await process_mnrl_files(
        apikey, existing_phone_numbers, phone_prefix, mnrl_filenames
    )
    rprint(
        f"Processed {mnrl_total_count:,} expired phone numbers in MNRL with"
        f" {failures:,} failure(s) and revoked {len(revoked_phone_numbers):,} phone"
        f" numbers"
    )


@periodic.command('mnrl')
def periodic_mnrl() -> None:
    """Remove expired phone numbers using TRAI's MNRL (1 week)."""
    apikey = app.config.get('MNRL_API_KEY')
    if not apikey:
        raise click.UsageError("App config is missing `MNRL_API_KEY`")
    try:
        asyncio.run(process_mnrl(apikey))
    except (KeyInvalidError, KeyExpiredError) as exc:
        app.logger.error(exc.message)
        raise click.ClickException(exc.message) from exc
