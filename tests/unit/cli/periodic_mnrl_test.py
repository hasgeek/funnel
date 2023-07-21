"""Tests for the periodic CLI stats commands."""
# pylint: disable=redefined-outer-name

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from click.testing import CliRunner
from respx import MockRouter

from funnel.cli.periodic import mnrl as cli_mnrl, periodic

MNRL_FILES_URL = 'https://mnrl.trai.gov.in/api/mnrl/files/{apikey}'
MNRL_JSON_URL = 'https://mnrl.trai.gov.in/api/mnrl/json/{filename}/{apikey}'


@pytest.fixture(scope='module')
def mnrl_files_response() -> bytes:
    """Sample response for MNRL files API."""
    return (
        b'{"status":200,"message":"Success","mnrl_files":{'
        b'"zip":[{"file_name":"test.rar","size_in_kb":1}],'
        b'"json":[{"file_name":"test.json","size_in_kb":1}]'
        b'}}'
    )


@pytest.fixture(scope='module')
def mnrl_files_response_keyinvalid() -> bytes:
    return b'{"status": 401, "message": "Invalid Key"}'


@pytest.fixture(scope='module')
def mnrl_files_response_keyexpired() -> bytes:
    return b'{"status": 407,"message": "Key Expired"}'


@pytest.fixture(scope='module')
def mnrl_json_response() -> bytes:
    """Sample response for MNRL JSON API."""
    return (
        b'{"status":200,"file_name":"test.json",'
        b'"payload":[{"n":"1111111111"},{"n":"2222222222"},{"n":"3333333333"}]}'
    )


@pytest.mark.asyncio()
@pytest.mark.parametrize('status_code', [200, 401])
async def test_mnrl_file_list_apikey_invalid(
    respx_mock: MockRouter, mnrl_files_response_keyinvalid: bytes, status_code: int
) -> None:
    """MNRL file list getter raises KeyInvalidError if the API key is invalid."""
    respx_mock.get(MNRL_FILES_URL.format(apikey='invalid')).mock(
        return_value=httpx.Response(status_code, content=mnrl_files_response_keyinvalid)
    )
    with pytest.raises(cli_mnrl.KeyInvalidError):
        await cli_mnrl.get_mnrl_json_file_list('invalid')


@pytest.mark.asyncio()
@pytest.mark.parametrize('status_code', [200, 407])
async def test_mnrl_file_list_apikey_expired(
    respx_mock: MockRouter, mnrl_files_response_keyexpired: bytes, status_code: int
) -> None:
    """MNRL file list getter raises KeyExpiredError if the API key has expired."""
    respx_mock.get(MNRL_FILES_URL.format(apikey='expired')).mock(
        return_value=httpx.Response(status_code, content=mnrl_files_response_keyexpired)
    )
    with pytest.raises(cli_mnrl.KeyExpiredError):
        await cli_mnrl.get_mnrl_json_file_list('expired')


@pytest.mark.asyncio()
async def test_mnrl_file_list(
    respx_mock: MockRouter, mnrl_files_response: bytes
) -> None:
    """MNRL file list getter returns a list."""
    respx_mock.get(MNRL_FILES_URL.format(apikey='12345')).mock(
        return_value=httpx.Response(200, content=mnrl_files_response)
    )
    assert await cli_mnrl.get_mnrl_json_file_list('12345') == ['test.json']


@pytest.mark.asyncio()
@pytest.mark.mock_config('app', {'MNRL_API_KEY': '12345'})
async def test_mnrl_file_numbers(
    respx_mock: MockRouter, mnrl_json_response: bytes
) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        respx_mock.get(MNRL_JSON_URL.format(apikey='12345', filename='test.json')).mock(
            return_value=httpx.Response(200, content=mnrl_json_response)
        )
        assert await cli_mnrl.get_mnrl_json_file_numbers(
            client, apikey='12345', filename='test.json'
        ) == ('test.json', {'1111111111', '2222222222', '3333333333'})


# --- CLI interface


@pytest.mark.mock_config('app', {'MNRL_API_KEY': ...})
def test_cli_mnrl_needs_api_key() -> None:
    """CLI command requires API key in config."""
    runner = CliRunner()
    result = runner.invoke(periodic, ['mnrl'])
    assert "App config is missing `MNRL_API_KEY`" in result.output
    assert result.exit_code == 2  # click exits with 2 for UsageError


@pytest.mark.mock_config('app', {'MNRL_API_KEY': '12345'})
def test_cli_mnrl_accepts_api_key() -> None:
    """CLI command runs if an API key is present."""
    with patch('funnel.cli.periodic.mnrl.process_mnrl', return_value=None) as mock:
        runner = CliRunner()
        runner.invoke(periodic, ['mnrl'])
        assert mock.called


@pytest.mark.mock_config('app', {'MNRL_API_KEY': 'invalid'})
@pytest.mark.usefixtures('db_session')
def test_cli_mnrl_invalid_api_key(
    respx_mock: MockRouter, mnrl_files_response_keyinvalid: bytes
) -> None:
    """CLI command prints an exception given an invalid API key."""
    respx_mock.get(MNRL_FILES_URL.format(apikey='invalid')).mock(
        return_value=httpx.Response(200, content=mnrl_files_response_keyinvalid)
    )
    runner = CliRunner()
    result = runner.invoke(periodic, ['mnrl'])
    assert "key is invalid" in result.output
    assert result.exit_code == 1  # click exits with 1 for ClickException
