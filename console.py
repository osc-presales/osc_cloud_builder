# -*- coding: utf-8 -*-
"""
File to be loaded in a python interpreter. AK, SK and endpoints are loaded following OCBase rules

for instance:
    $>[pt|b]python -i console.py
"""

__author__      = "Heckle"
__copyright__   = "BSD"

import os
import sys

base_path = '{0}/osc_cloud_builder'.format(os.path.dirname(os.path.realpath('__file__')))
sys.path.append(base_path)

from OCBase import OCBase

ocb = OCBase()
ocb.activate_stdout_logging()

print '\n[0;35mYou can use:\n[0;0m',
if ocb.fcu:
    print '\t[1;32m- ocb.fcu[0;0m'

if ocb.lbu:
    print '\t[1;32m- ocb.lbu[0;0m'

if ocb.eim:
    print '\t[1;32m- ocb.eim[0;0m'

if ocb.osu:
    print '\t[1;32m- ocb.osu[0;0m'
