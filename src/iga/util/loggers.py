# -*- coding: utf-8 -*-

"""
TODO: module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import logging

#: No automatic export
__all__ = []


class MyLogger(object):
    """docstring for MyLogger"""
    def __init__(self):
        self.logger = iga_logger()

    def __deepcopy__(self, *args, **kw):
        print("deepcopy", self, type(self))
        return self

    def notify(self, message):
        print("MyLogger::notify %s" % message)
        self.logger.info(message)


def create_logger():
    # create logger with 'bfootprint'
    logger = logging.getLogger('bfootprint')
    # logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('bfootprint.log')
    fh.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    return logger


def iga_logger():
    # create logger with 'bfootprint'
    logger = logging.getLogger('iga')
    # logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('iga.log')
    fh.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    return logger
