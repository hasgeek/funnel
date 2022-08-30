#!/usr/bin/env python
"""Script to update test dataset output for markdown parser tests to current version."""

from copy import copy, deepcopy
import os

import toml

DATA_ROOT = os.path.abspath(os.path.join('tests', 'data', 'markdown'))

from funnel.utils.markdown import markdown
from funnel.utils.markdown.helpers import MD_CONFIGS

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
                    file_data['results'][
                        c
                    ] = markdown(  # pylint: disable=unnecessary-dunder-call
                        data['markdown'], **md_configs[c]
                    ).__str__()
            f.close()
            with open(os.path.join(DATA_ROOT, file), 'w', encoding='utf-8') as f2:
                toml.dump(file_data, f2)
                f2.close()
