"""Process mnrl phonenumbers."""

import requests
from flask.cli import AppGroup
from rich.progress import Progress

from .. import app
from ..models import PhoneNumber

mnrl = AppGroup('mnrl', help="Process mnrl phonenumbers.")


def get_mnrl_file_list() -> list:
    # Returns the summary of MNRL files
    mnrl_files_url = (
        f'https://mnrl.trai.gov.in/api/mnrl/files/{app.config["MNRL_API_KEY"]}'
    )
    rv = requests.get(mnrl_files_url).json()
    return [i['file_name'] for i in rv['mnrl_files']['json']]


def load_mnrl_phonenumbers() -> set:
    # Returns the set of mobile numbers of all the requested (.json) file.
    file_list = get_mnrl_file_list()
    mnrl_set = set()
    with Progress() as progress:
        task = progress.add_task("Processing MNRL files", total=len(file_list))
        for file in file_list:
            progress.console.print(f"Working on file {file}")
            mnrl_details_url = f"https://mnrl.trai.gov.in/api/mnrl/json/{file}/{app.config['MNRL_API_KEY']}"
            rv = requests.get(mnrl_details_url).json()
            payload = rv['payload']
            for i in payload:
                if isinstance(i["n"], str):
                    mnrl_set.add(int(i['n']))
            progress.advance(task)
    return mnrl_set


def load_hg_phonenumbers() -> set:
    # Returns the set of mobile numbers of all the users in the database.
    hg_phonenumbers = set()
    phone_numbers = PhoneNumber.query.all()
    for phone_number in phone_numbers:
        if isinstance(phone_number.number, str):
            hg_phonenumbers.add(int(phone_number.number[3:]))
    return hg_phonenumbers


@mnrl.command('revoked_phonenumbers')
def check_revoked_phonenumbers() -> set:
    # Check if hg_phonenumbers are in mnrl_phonenumbers and return the revoked phone numbers
    hg_phone_numbers = load_hg_phonenumbers()
    mnrl_phone_numbers = load_mnrl_phonenumbers()
    revoked_phone_numbers = set()
    for phone_number in hg_phone_numbers:
        if phone_number in mnrl_phone_numbers:
            revoked_phone_numbers.add(phone_number)
    return revoked_phone_numbers


@mnrl.command('notify_revoked_phonenumbers')
def notify_revoked_phonenumbers():
    # TODO: Send email to users with revoked phone numbers
    check_revoked_phonenumbers()
    return ''


app.cli.add_command(mnrl)
