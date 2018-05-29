#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package is used to implement the Archive Store class only used at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from vortex.tools.storage import Archive
from ecmwf.tools.interfaces import ECtrans, ECfs
from ecmwf.tools.ectrans_parameters import ectransparameters


class ArchiveECMWF(Archive):
    """The specific class to handle Archive from ECMWF super-computers"""

    _default_tube = 'ectrans'

    _collector = ('archive', )
    _footprint = dict(
        info = 'Default archive description from ECMWF',
        attr = dict(
            storage = dict(
                optional = True,
                default  = 'generic'
            ),
            tube = dict(
                info     = "How to communicate with the archive?",
                values   = ['ectrans', 'ecfs'],
                optional = True
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def _ectransfullpath(self, item, **kwargs):
        """Actual _fullpath using ectrans"""
        return item, dict()

    def _ectransprestageinfo(self, item, **kwargs):
        """Actual _prestageinfo using ectrans"""
        raise NotImplementedError

    def _ectranscheck(self, item, **kwargs):
        """Actual _check using ectrans"""
        raise NotImplementedError

    def _ectranslist(self, item, **kwargs):
        """Actual _list using ectrans"""
        raise NotImplementedError

    def _ectransretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ectrans"""
        ectrans = ECtrans(system=self.sh)
        # Construct the different attributes
        list_args = list()
        list_options = ["get", "verbose", "overwrite"]
        dict_args = ectransparameters(sh=self.sh, **kwargs)
        dict_args["source"] = item
        dict_args["target"] = local
        # Call ECtrans
        rc = ectrans(
            list_args=list_args,
            list_options=list_options,
            dict_args=dict_args
        )
        del dict_args["source"]
        del dict_args["target"]
        return rc, dict_args

    def _ectransinsert(self, item, local, **kwargs):
        """Actual _insert using ectrans"""
        ectrans = ECtrans(system=self.sh)
        # Construct the different attributes
        list_args = list()
        list_options = ["put", "verbose", "overwrite"]
        dict_args = ectransparameters(sh=self.sh, **kwargs)
        dict_args["source"] = local
        dict_args["target"] = item
        # Call ECtrans
        rc = ectrans(
            list_args=list_args,
            list_options=list_options,
            dict_args=dict_args
        )
        del dict_args["source"]
        del dict_args["target"]
        return rc, dict_args

    def _ectransdelete(self, item, **kwargs):
        """Actual _delete using ectrans"""
        raise NotImplementedError

    def _ecfsfullpath(self, item, **kwargs):
        """Actual _fullpath using ecfs"""
        actual_fullpath = None
        if self.actual_storage == "ecgate.ecmwf.int":
            actual_fullpath = "ec:{}".format(item)
        else:
            raise NotImplementedError
        return actual_fullpath, dict()

    def _ecfsprestageinfo(self, item, **kwargs):
        """Actual _prestageinfo using ecfs"""
        raise NotImplementedError

    def _ecfscheck(self, item, **kwargs):
        """Actual _check using ecfs"""
        ecfs = ECfs(system=self.sh)
        command = "etest"
        list_args = [item, ]
        if "options" in kwargs:
            list_options= kwargs["options"]
            del kwargs["options"]
        else:
            list_options = ["r", ]
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=kwargs,
                      list_options=list_options)
        return rc, dict()

    def _ecfslist(self, item, **kwargs):
        """Actual _list using ecfs"""
        ecfs = ECfs(system=self.sh)
        command = "els"
        list_args = [item, ]
        if "options" in kwargs:
            list_options= kwargs["options"]
            del kwargs["options"]
        else:
            list_options = ["l", ]
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=kwargs,
                      list_options=list_options)
        return rc, dict()

    def _ecfsretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ecfs"""
        ecfs = ECfs(system=self.sh)
        command = "ecp"
        list_args = [item, local]
        if "options" in kwargs:
            list_options = kwargs["options"]
            del kwargs["options"]
        else:
            list_options = list()
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=kwargs,
                      list_options=list_options)
        return rc, dict()

    def _ecfsinsert(self, item, local, **kwargs):
        """Actual _insert using ecfs"""
        ecfs = ECfs(system=self.sh)
        command = "ecp"
        list_args = [local, item]
        if "options" in kwargs:
            list_options = kwargs["options"]
            del kwargs["options"]
        else:
            list_options = list()
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=kwargs,
                      list_options=list_options)
        return rc, dict()

    def _ecfsdelete(self, item, **kwargs):
        """Actual _delete using ecfs"""
        ecfs = ECfs(system=self.sh)
        command = "erm"
        list_args = [item, ]
        if "options" in kwargs:
            list_options = kwargs["options"]
            del kwargs["options"]
        else:
            list_options = list()
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=kwargs,
                      list_options=list_options)
        return rc, dict()
