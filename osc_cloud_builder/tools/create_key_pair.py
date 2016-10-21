# -*- coding: utf-8 -*-
"""
Simple help to create and save a keypair
"""

__author__      = "Heckle"
__copyright__   = "BSD"

import os
from datetime import datetime
from OCBase import OCBase


def create_key_pair(key_pair_name=None, key_directory='/tmp/keytest.rsa.d/'):
    """
    :param key_pair_name: Key pair name
    :type key_pair_name: str
    :param key_directory: Directory path where keypair will be saved
    :type key_directory: str
    :return: keypair information
    :rtype: dict
    """
    ocb = OCBase()
    if not os.path.isdir(key_directory):
        os.makedirs(key_directory)
    if not key_pair_name:
        key_pair_name = ''.join(['test_key_', datetime.now().strftime("_%d_%m_%s")])
    kp = ocb.fcu.create_key_pair(key_pair_name)
    kp.save(key_directory)

    return {
        "name": key_pair_name,
        "directory": key_directory,
        "path": ''.join([key_directory, key_pair_name, '.pem'])
    }
