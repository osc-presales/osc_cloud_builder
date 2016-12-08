#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Collection of generic functions
"""

__author__      = "Heckle"
__copyright__   = "BSD"

import time
from osc_cloud_builder.OCBase import SLEEP_SHORT

def wait_state(objs, state_name, timeout=120):
    """
    Wait for cloud ressources to be in a given state.
    :param objs: list of boto object with update() method
    :type: list
    :param state_name: Instance state name expected
    :type state_name: str
    :param timeout: Timeout for instances to reach state_name
    :type timeout: int
    :return: boto objects which are not in the expected state_name
    :rtype: list

    """
    objs = [obj for obj in objs if hasattr(obj, 'update')]

    timeout = time.time() + timeout
    while time.time() < timeout and objs:
        for obj in objs:
            if obj.update() == state_name:
                objs.remove(obj)
            time.sleep(SLEEP_SHORT)

    return objs
