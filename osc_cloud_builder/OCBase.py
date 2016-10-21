# -*- coding: utf-8 -*-
"""
OCBase setup FCU, OSU, EIM and LBU connection objects to Outscale Cloud.
"""

__author__      = "Heckle"
__copyright__   = "BSD"


import sys
import logging
import boto
import ConfigParser
import os.path
import os
import boto.s3.connection
from boto.vpc import VPCConnection
from boto.ec2.regioninfo import EC2RegionInfo
from boto.iam.connection import IAMConnection
from boto.ec2.elb import ELBConnection


SLEEP_SHORT = 5

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class OCBError(RuntimeError):
    """
    OCB error class
    """
    pass


class OCBase(object):
    """
    Manage API connections (FCU, OSU, EIM, LBU) and provide centralized logging system
    """

    __metaclass__ = Singleton

    def __init__(self, region='eu-west-2', settings_paths=['~/.osc_cloud_builder/services.ini', '/etc/osc_cloud_builder/services.ini'], is_secure=True, debug_filename='/tmp/ocb.log', debug_level='INFO'):
        """
        :param region: region choosen for loading settings.ini section
        :type region: str
        :param settings_paths: paths where services.init should be if needed
        :type settings_paths: list
        :param is_secure: allow connector without ssl
        :type is_secure: bool
        :param debug_filename: File to store logs
        :type debug_filename: str
        """
        self.__logger_setup(debug_filename, debug_level)
        self.region = region
        self.settings_paths = settings_paths
        self.__connections_setup(is_secure)

    def __logger_setup(self, debug_filename, debug_level):
        """
        Logger setup
        :param debug_filename: File to store logs
        :type debug_filename: str
        :param debug_level: level debug
        :type debug_level: str
        """
        debug_level = getattr(logging, debug_level)
        self.__logger = logging.getLogger()
        logging.basicConfig(filename=debug_filename,
                            filemode='a',
                            level=debug_level,
                            format='%(asctime)s.%(msecs)d %(levelname)s - %(message)s',
                            datefmt="%Y-%m-%d %H:%M:%S")

    def __load_config(self):
        """
        Load Cloud configuration from services.ini OR environment
        """
        fcu_endpoint = None
        lbu_endpoint = None
        eim_endpoint = None
        osu_endpoint = None
        settings = ConfigParser.ConfigParser()
        settings_path = None

        for set_path in self.settings_paths:
            if os.path.exists(set_path):
                settings_path = set_path
        if not settings_path:
            full_path = os.path.realpath(__file__)
            base_path = os.path.dirname(full_path)
            settings_path = '{0}/../services.ini'.format(base_path)
        settings.read(filenames=settings_path)

        fcu_endpoint = os.environ.get('FCU_ENDPOINT', None)
        if not fcu_endpoint:
            try:
                fcu_endpoint = settings.get(self.region, 'fcu_endpoint')
            except ConfigParser.Error:
                self.log('No fcu_endpoint set', 'warning')

        lbu_endpoint = os.environ.get('LBU_ENDPOINT', None)
        if not lbu_endpoint:
            try:
                lbu_endpoint = settings.get(self.region, 'lbu_endpoint')
            except ConfigParser.Error:
                self.log('No lbu_endpoint set', 'warning')

        eim_endpoint = os.environ.get('EIM_ENDPOINT', None)
        if not eim_endpoint:
            try:
                eim_endpoint = settings.get(self.region, 'eim_endpoint')
            except ConfigParser.Error:
                self.log('No eim_endpoint set', 'warning')

        osu_endpoint = os.environ.get('OSU_ENDPOINT', None)
        if not osu_endpoint:
            try:
                osu_endpoint = settings.get(self.region, 'osu_endpoint')
            except ConfigParser.Error:
                self.log('No osu_endpoint set', 'warning')

        return fcu_endpoint, lbu_endpoint, eim_endpoint, osu_endpoint


    def __connections_setup(self, is_secure):
        """
        Creates FCU, OSU and EIM connections if endpoints are configured
        :param is_secure: allow connection without SSL
        :type is_secure: bool
        :raises OCBError: When connections can not be created because AK and SK are not set up in environment variable
        """
        access_key_id = os.environ.get('AWS_ACCESS_KEY_ID', None)
        secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
        if not access_key_id or not secret_access_key:
            self.__logger.critical('You must setup both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variable')
            raise OCBError('Bad credential (access_key_id, secret_access_key) setup')

        fcu_endpoint, lbu_endpoint, eim_endpoint, osu_endpoint = self.__load_config()

        if fcu_endpoint:
            fcu_endpoint = EC2RegionInfo(endpoint=fcu_endpoint)
            self.fcu = VPCConnection(access_key_id, secret_access_key, region=fcu_endpoint, is_secure=is_secure)
        else:
            self.__logger.info('No FCU connection configured')
            self.fcu = None

        if lbu_endpoint:
            lbu_endpoint = EC2RegionInfo(endpoint=lbu_endpoint)
            self.lbu = ELBConnection(access_key_id, secret_access_key, region=lbu_endpoint)
        else:
            self.__logger.info('No LBU connection configured')
            self.lbu = None

        if eim_endpoint:
            self.eim = IAMConnection(access_key_id, secret_access_key, host=eim_endpoint)
        else:
            self.__logger.info('No EIM connection configured')
            self.eim = None

        if osu_endpoint:
            self.osu = boto.connect_s3(access_key_id, secret_access_key, host=osu_endpoint,
                                       calling_format=boto.s3.connection.ProtocolIndependentOrdinaryCallingFormat())
        else:
            self.__logger.info('No OSU connection configured')
            self.osu = None



    def log(self, message, level='debug', module_name=''):
        """
        Centralized log system
        :param message: Message to be logged
        :type message: str
        :param module_name: Module name where the message is coming
        :type module_name: str
        :param level: message level
        :type level: str
        """
        try:
            log = getattr(self.__logger, level)
        except AttributeError:
            log = getattr(self.__logger, 'debug')
        log('{0} - {1}'.format(module_name, message))


    def activate_stdout_logging(self):
        """
        Display logging messages in stdout
        """
        ch = logging.StreamHandler(sys.stdout)
        logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.__logger.addHandler(ch)
