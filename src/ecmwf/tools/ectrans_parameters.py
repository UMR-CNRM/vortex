#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module contains the generic interface used for ECtrans and ECfs.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

logger = footprints.loggers.getLogger(__name__)


def ectransparameters(sh, **kwargs):
    """
    Build the dictionnary containing the parameters used in the ECtrans interface from the stores.
    :param sh: the system object
    :param kwargs: options which can be useful in the interface
    :return: a dictionnary containing all the relevant options to be passed to the interface
    """
    """Format the options used for ectrans"""
    optionsdict = dict()
    # Find the gateway attribute of ectrans
    gateway = kwargs.get("gateway", sh.env['ECTRANS_GATEWAY_HOST'])
    optionsdict["gateway"] = gateway
    # Find the remote attribute of ectrans
    association = kwargs.get("association", sh.env["ECTRANS_GATEWAY_ARCHIVE_NAME"])
    plugin = kwargs.get("plugin", sh.env["ECTRANS_GATEWAY_ARCHIVE_PLUGIN"])
    if plugin is None:
        plugin = "genericFtp"
    optionsdict["remote"] = '@'.join([association, plugin])
    # Set other options
    optionsdict['delay'] = '120'
    optionsdict['priority'] = 60
    optionsdict['retryCnt'] = 0
    return optionsdict
