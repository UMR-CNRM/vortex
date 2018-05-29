#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Definitions of the Archive stores at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division


import footprints
from vortex.data.stores import Finder
from ecmwf.tools.interfaces import ECtrans, ECfs
from ecmwf.tools.ectrans_parameters import ectransparameters

logger = footprints.loggers.getLogger(__name__)


class FinderECMWF(Finder):
    """Derivate class Finder to be used at ECMWF."""
    _footprint = dict(
        info = "Miscellaneous file access on other servers from ECMWF",
        attr = dict(
            scheme = dict(
                values = ['ectrans', 'ecfs']
            )
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    def ectransfullpath(self, remote):
        return remote["path"]

    def ectranscheck(self, remote, options):
        raise NotImplementedError

    def ectranslocate(self, remote, options):
        return self.ectransfullpath(remote)

    def ectransget(self, remote, local, options):
        # Initializations
        rpath = self.ectransfullpath(remote)
        logger.info('ectransget on %s (to: %s)', rpath, local)
        ectrans = ECtrans(system=self.system)
        # Construct the different attributes
        list_args = list()
        list_options = ["get", "verbose", "overwrite"]
        dict_args = ectransparameters(sh=self.system, **options)
        dict_args["source"] = rpath
        dict_args["target"] = local
        # Call ECtrans
        rc = ectrans(
            list_args=list_args,
            list_options=list_options,
            dict_args=dict_args
        )
        del dict_args["source"]
        del dict_args["target"]
        return rc

    def ectransput(self, local, remote, options):
        # Initializations
        rpath = self.ectransfullpath(remote)
        logger.info('ectransput on %s (from: %s)', rpath, local)
        ectrans = ECtrans(system=self.system)
        # Construct the different attributes
        list_args = list()
        list_options = ["put", "verbose", "overwrite"]
        dict_args = ectransparameters(sh=self.system, **options)
        dict_args["source"] = local
        dict_args["target"] = rpath
        # Call ECtrans
        rc = ectrans(
            list_args=list_args,
            list_options=list_options,
            dict_args=dict_args
        )
        del dict_args["source"]
        del dict_args["target"]
        return rc

    def ectransdelete(self, remote, options):
        raise NotImplementedError

    def ecfsfullpath(self, remote):
        return "ec:{}".format(remote["path"])

    def ecfscheck(self, remote, options):
        rpath = self.ecfsfullpath(remote)
        ecfs = ECfs(self.system)
        command = "etest"
        list_args = [rpath, ]
        if "options" in options:
            list_options = options["options"]
        else:
            list_options = ["r", ]
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=dict(),
                      list_options=list_options)
        return rc

    def ecfslocate(self, remote, options):
        return self.ecfsfullpath(remote)

    def ecfsget(self, remote, local, options):
        rpath = self.ecfsfullpath(remote)
        ecfs = ECfs(system=self.system)
        command = "ecp"
        list_args = [rpath, local]
        if "options" in options:
            list_options = options["options"]
        else:
            list_options = list()
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=dict(),
                      list_options=list_options)
        return rc

    def ecfsput(self, local, remote, options):
        rpath = self.ecfsfullpath(remote)
        ecfs = ECfs(system=self.system)
        command = "ecp"
        list_args = [local, rpath]
        if "options" in options:
            list_options = options["options"]
        else:
            list_options = list()
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=dict(),
                      list_options=list_options)
        return rc

    def ecfsdelete(self, remote, options):
        rpath = self.ecfsfullpath(remote)
        ecfs = ECfs(system=self.system)
        command = "erm"
        list_args = [rpath, ]
        if "options" in options:
            list_options = options["options"]
        else:
            list_options = list()
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=dict(),
                      list_options=list_options)
        return rc
