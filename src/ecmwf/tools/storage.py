#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package is used to implement the Archive Store class only used at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from vortex.tools.storage import Archive


class ArchiveECMWF(Archive):
    """The specific class to handle Archive from ECMWF super-computers"""

    _default_tube = 'ectrans'
    _footprint = dict(
        info = 'Default archive description from ECMWF',
        attr = dict(
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
        remote = self.sh.ectrans_remote_init(remote=kwargs.get("remote", None),
                                             inifile=self.inifile,
                                             storage=self.actual_storage)
        gateway = self.sh.ectrans_gateway_init(gateway=kwargs.get("gateway", None),
                                               inifile=self.inifile)
        return self.sh.ectransget(source=item,
                                  target=local,
                                  fmt=kwargs.get("fmt", "foo"),
                                  cpipeline=kwargs.get("compressionpipeline", None),
                                  gateway=gateway,
                                  remote=remote)

    def _ectransinsert(self, item, local, **kwargs):
        """Actual _insert using ectrans"""
        remote = self.sh.ectrans_remote_init(remote=kwargs.get("remote", None),
                                             inifile=self.inifile,
                                             storage=self.actual_storage)
        gateway = self.sh.ectrans_gateway_init(gateway=kwargs.get("gateway", None),
                                               inifile=self.inifile)
        return self.sh.ectransput(source=local,
                                  target=item,
                                  fmt=kwargs.get("fmt", "foo"),
                                  cpipeline=kwargs.get("compressionpipeline", None),
                                  gateway=gateway,
                                  remote=remote)

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
        options = kwargs.get("options", None)
        return self.sh.ecfstest(item=item,
                                otpions=options)

    def _ecfslist(self, item, **kwargs):
        """Actual _list using ecfs"""
        options = kwargs.get("options", None)
        return self.sh.ecfsls(item=item,
                              options=options)

    def _ecfsretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ecfs"""
        options = kwargs.get("options", None)
        cpipeline = kwargs.get("compressionpipeline", None)
        return self.sh.ecfsget(source=item,
                               target=local,
                               cpipeline=cpipeline,
                               options=options)

    def _ecfsinsert(self, item, local, **kwargs):
        """Actual _insert using ecfs"""
        options = kwargs.get("options", None)
        cpipeline = kwargs.get("compressionpipeline", None)
        return self.sh.ecfsput(source=local,
                               target=item,
                               cpipeline=cpipeline,
                               options=options)

    def _ecfsdelete(self, item, **kwargs):
        """Actual _delete using ecfs"""
        options = kwargs.get("options", None)
        return self.sh.ecfsrm(item=item,
                              options=options)
