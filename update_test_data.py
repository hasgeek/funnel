#!/usr/bin/env python
"""Script to update test dataset output for markdown parser tests to current version."""

from copy import copy, deepcopy
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
    output_template = template.find(id='output_template')
    for file in os.listdir(DATA_ROOT):
        if file.endswith('.toml'):
            with open(os.path.join(DATA_ROOT, file), encoding='utf-8') as f:
                file_data = toml.load(f)
                data = file_data['data']
                conf = file_data['config']
                file_data['results'] = {}
                configs = copy(conf['configs'])
                md_configs = deepcopy(MD_CONFIGS)
                if 'extra_configs' in conf:
                    for c in conf['extra_configs']:
                        if c not in md_configs:
                            md_configs[c] = conf['extra_configs'][c]
                            configs.append(c)
                for c in configs:
                    if c in md_configs:
                        op = copy(output_template)
                        del op['id']
                        op.select('.filename')[0].string = file
                        op.select('.configname')[0].string = c
                        op.select('.config')[0].string = json.dumps(
                            md_configs[c], indent=2
                        )
                        op.select('.markdown .output')[0].append(data['markdown'])
                        file_data['results'][
                            c
                        ] = markdown(  # pylint: disable=unnecessary-dunder-call
                            data['markdown'], **md_configs[c]
                        ).__str__()
                        op.select('.expected .output')[0].append(
                            BeautifulSoup(file_data['results'][c], 'html.parser')
                        )

                        op['id'] = '_'.join(file.split('.')[:-1] + [c])
                        template.find('body').append(op)
                f.close()
                with open(os.path.join(DATA_ROOT, file), 'w', encoding='utf-8') as f2:
                    toml.dump(file_data, f2)
                    f2.close()
    template.find(id='generated').string = datetime.now().strftime('%d %B, %Y %H:%M:%S')
    with open(os.path.join(DATA_ROOT, 'output.html'), 'w', encoding='utf-8') as output:
        output.write(template.prettify())
