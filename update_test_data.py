#!/usr/bin/env python
"""Script to update test dataset output for markdown parser tests to current version."""

from copy import copy
from datetime import datetime
import json
import os

from bs4 import BeautifulSoup
import toml

DATA_ROOT = os.path.abspath(os.path.join('tests', 'data', 'markdown'))

from funnel.utils.markdown import markdown
from funnel.utils.markdown.helpers import MD_CONFIGS

with open(os.path.join(DATA_ROOT, 'template.html'), encoding='utf-8') as tf:
    template = BeautifulSoup(tf, 'html.parser')
    tbody = template.find('table').find('tbody')
    row_template = tbody.find(id='row_template')
    for file in os.listdir(DATA_ROOT):
        if file.endswith('.toml'):
            with open(os.path.join(DATA_ROOT, file), encoding='utf-8') as f:
                file_data = toml.load(f)
                data = file_data['data']
                config = file_data['config']
                file_data['results'] = {}
                for c in config['configs']:
                    if c in MD_CONFIGS:
                        row = copy(row_template)
                        del row['id']
                        cols = row.find_all('td')
                        cols[0].find('pre').string = (
                            'Test file: ' + file + '\n----\n' + data['markdown']
                        )
                        cols[1].find('pre').string = (
                            'Config: '
                            + c
                            + '\n----\n'
                            + json.dumps(MD_CONFIGS[c], indent=2)
                        )
                        file_data['results'][
                            c
                        ] = markdown(  # pylint: disable=unnecessary-dunder-call
                            data['markdown'], **MD_CONFIGS[c]
                        ).__str__()
                        cols[2].append(
                            BeautifulSoup(file_data['results'][c], 'html.parser')
                        )
                        row['id'] = '_'.join(file.split('.')[:-1] + [c])
                        tbody.append(row)
                f.close()
                with open(os.path.join(DATA_ROOT, file), 'w', encoding='utf-8') as f2:
                    toml.dump(file_data, f2)
                    f2.close()
    template.find(id='generated').string = datetime.now().strftime('%d %B, %Y %H:%M:%S')
    with open(os.path.join(DATA_ROOT, 'output.html'), 'w', encoding='utf-8') as output:
        output.write(template.prettify())
