# -*- coding: utf-8 -*-

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

    @staticmethod
    def ectransfullpath(remote):
        return remote["path"]

    def ectranscheck(self, remote, options):
        raise NotImplementedError()

    def ectranslocate(self, remote, options):
        return self.ectransfullpath(remote)

    def ectransget(self, remote, local, options):
        # Initializations
        rpath = self.ectransfullpath(remote)
        logger.info('ectransget on %s (to: %s)', rpath, local)
        ectrans_remote = self.system.ectrans_remote_init(remote=options.get("remote", None),
                                                         storage=self.hostname())
        ectrans_gateway = self.system.ectrans_gateway_init(gateway=options.get("gateway", None))
        rc = self.system.ectransget(source=rpath,
                                    target=local,
                                    fmt=options.get("fmt", "foo"),
                                    cpipeline=options.get("compressionpipeline", None),
                                    gateway=ectrans_gateway,
                                    remote=ectrans_remote)
        if rc:
            self._localtarfix(local)
        return rc

    def ectransput(self, local, remote, options):
        # Initializations
        rpath = self.ectransfullpath(remote)
        logger.info('ectransput on %s (from: %s)', rpath, local)
        ectrans_remote = self.system.ectrans_remote_init(remote=options.get("remote", None),
                                                         storage=self.hostname())
        ectrans_gateway = self.system.ectrans_gateway_init(gateway=options.get("gateway", None))
        return self.system.ectransput(source=local,
                                      target=rpath,
                                      fmt=options.get("fmt", "foo"),
                                      cpipeline=options.get("compressionpipeline", None),
                                      gateway=ectrans_gateway,
                                      remote=ectrans_remote,
                                      sync=options.get('enforcesync', False))

    def ectransdelete(self, remote, options):
        raise NotImplementedError

    @staticmethod
    def ecfsfullpath(remote):
        return "ec:{}".format(remote["path"])

    def ecfscheck(self, remote, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        return self.system.ecfstest(item=rpath,
                                    options=list_options)

    def ecfslocate(self, remote, options):
        return self.ecfsfullpath(remote)

    def ecfsget(self, remote, local, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        cpipeline = options.get("compressionpipeline")
        rc = self.system.ecfsget(source=rpath,
                                 target=local,
                                 fmt=options.get("fmt", "foo"),
                                 cpipeline=cpipeline,
                                 options=list_options)
        if rc:
            self._localtarfix(local)
        return rc

    def ecfsput(self, local, remote, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        cpipeline = options.get("compressionpipeline")
        return self.system.ecfsput(source=local,
                                   target=rpath,
                                   fmt=options.get("fmt", "foo"),
                                   cpipeline=cpipeline,
                                   options=list_options)

    def ecfsdelete(self, remote, options):
        rpath = self.ecfsfullpath(remote)
        list_options = options.get("options", list())
        return self.system.ecfsrm(item=rpath,
                                  fmt=options.get("fmt", "foo"),
                                  options=list_options)
