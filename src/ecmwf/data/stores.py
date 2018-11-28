#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Definitions of the Archive stores at ECMWF.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
import footprints

from vortex.data.stores import Finder

logger = loggers.getLogger(__name__)


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
        raise NotImplementedError()

    def ectranslocate(self, remote, options):
        return self.ectransfullpath(remote)

    def ectransget(self, remote, local, options):
        # Initializations
        rpath = self.ectransfullpath(remote)
        logger.info('ectransget on %s (to: %s)', rpath, local)
        ectrans_remote = self.sh.ectrans_remote_init(remote=options.get("remote", None),
                                                     storage=self.hostname())
        ectrans_gateway = self.sh.ectrans_gateway_init(gateway=options.get("gateway", None))
        rc, dict_args = self.system.ectransget(source=rpath,  # @UnusedVariable
                                               target=local,
                                               fmt=options.get("fmt", "foo"),
                                               cpipeline=options.get("compressionpipeline", None),
                                               gateway=ectrans_gateway,
                                               remote=ectrans_remote)
        return rc

    def ectransput(self, local, remote, options):
        # Initializations
        rpath = self.ectransfullpath(remote)
        logger.info('ectransput on %s (from: %s)', rpath, local)
        ectrans_remote = self.sh.ectrans_remote_init(remote=options.get("remote", None),
                                                     storage=self.hostname())
        ectrans_gateway = self.sh.ectrans_gateway_init(gateway=options.get("gateway", None))
        rc, dict_args = self.system.ectransput(source=local,  # @UnusedVariable
                                               target=rpath,
                                               fmt=options.get("fmt", "foo"),
                                               cpipeline=options.get("compressionpipeline", None),
                                               gateway=ectrans_gateway,
                                               remote=ectrans_remote)
        return rc

    def ectransdelete(self, remote, options):
        raise NotImplementedError

    def ecfsfullpath(self, remote):
        return "ec:{}".format(remote["path"])

    def ecfscheck(self, remote, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        rc, dict_args = self.system.ecfstest(item=rpath,  # @UnusedVariable
                                             options=list_options)
        return rc

    def ecfslocate(self, remote, options):
        return self.ecfsfullpath(remote)

    def ecfsget(self, remote, local, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        cpipeline = options.get("compressionpipeline")
        rc, dict_args = self.system.ecfsget(source=rpath,  # @UnusedVariable
                                            target=local,
                                            cpipeline=cpipeline,
                                            options=list_options)
        return rc

    def ecfsput(self, local, remote, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        cpipeline = options.get("compressionpipeline")
        rc, dict_args = self.system.ecfsput(source=local,  # @UnusedVariable
                                            target=rpath,
                                            cpipeline=cpipeline,
                                            options=list_options)
        return rc

    def ecfsdelete(self, remote, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        rc, dict_args = self.system.ecfsrm(item=rpath,  # @UnusedVariable
                                           options=list_options)
        return rc
