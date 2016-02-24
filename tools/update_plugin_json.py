#! /usr/bin/env python

from ConfigParser import SafeConfigParser
import os
import json
import re

PLUGIN_DIR = '../lib/assembly/plugins/'
OUT_JSON = 'ar_modules.json'

plugin_configs = [p for p in sorted(os.listdir(PLUGIN_DIR))
                  if re.search('-plugin', p)]

plugins_data = []
for plugin_config in plugin_configs:
    pfile = os.path.join(PLUGIN_DIR, plugin_config)
    parser = SafeConfigParser()
    parser.read(pfile)
    pd = dict(dict(parser.items('Core')).items() +
              dict(parser.items('Settings')).items() +
              dict({'parameters' : dict(parser.items('Parameters')).items()}).items() +
              dict(parser.items('Documentation')).items())

    plugins_data.append(pd)

with open(OUT_JSON, 'w') as outfile:
    json.dump(plugins_data, outfile, indent = 4, separators=(',', ': '))
