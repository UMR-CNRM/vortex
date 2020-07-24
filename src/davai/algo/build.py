#!/usr/bin/env python
# -*- coding:Utf-8 -*-
"""
DAVAI sources build (branch export, compilation&link) AlgoComponents.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from footprints import FPList, FPDict
from bronx.fancies import loggers

from vortex.syntax import stdattrs
from vortex.algo.components import (AlgoComponent, AlgoComponentDecoMixin,
                                    AlgoComponentError)
from vortex.algo.components import algo_component_deco_mixin_autodoc
from gco.tools import uenv, genv

from .mixins import _CrashWitnessDecoMixin


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@algo_component_deco_mixin_autodoc
class GmkpackDecoMixin(AlgoComponentDecoMixin):
    
    _MIXIN_EXTRA_FOOTPRINTS = (footprints.Footprint(
        info="Abstract mbdetect footprint",
        attr=dict(
            homepack = dict(
                info = "Home directory for pack.",
                optional = True,
                default = None
            ),
            cleanpack = dict(
                info = "Whether to cleanpack a pack before modifying it.",
                type = bool,
                optional = True,
                default = True
            )
        )
    ),)
    
    def _set_gmkpack(self, rh, opts):  # @UnusedVariable
        gmk_installdir = self.target.config.get('gmkpack', 'gmkpack_installdir')
        self.env['PATH'] = ':'.join([self.system.path.join(gmk_installdir, 'util'),
                                     self.env['PATH']])
        self.env['GMKROOT'] = self.system.path.join(gmk_installdir)
        self.env['GMKTMP'] = self.system.getcwd() 
    
    _MIXIN_PREPARE_HOOKS = (_set_gmkpack, )


class IA4H_gitref_to_Pack(AlgoComponent, GmkpackDecoMixin,
                          _CrashWitnessDecoMixin):
    """Make a pack (gmkpack) with sources from a IA4H Git ref."""

    _footprint = [
        dict(
            info = "Make a pack (gmkpack) with sources from a IA4H Git ref.",
            attr = dict(
                kind = dict(
                    values   = ['ia4h_gitref2pack'],
                ),
                git_ref = dict(
                    info = "The Git ref (branch, tag, commit) to be exported to the pack.",
                ),
                repository = dict(
                    info = "The git repository to be used (on the target machine).",
                ),
                packname = dict(
                    info = "Name of the pack; defaults to self.git_ref.",
                    optional = True,
                    default = None,
                ),
                preexisting_pack = dict(
                    info = "Set to True if the pack preexists.",
                    type = bool,
                    optional = True,
                    default = False,
                ),
                rootpacks_dir = dict(
                    info = "Directory in which to find rootpacks.",
                    optional = True,
                    default = None,
                ),
                other_pack_options = dict(
                    info = "Other options to be passed to gmkpack command.",
                    type = FPDict,
                    optional = True,
                    default = dict(),
                ),
            )
        )
    ]

    def prepare(self, rh, opts):  # @UnusedVariable
        # git
        git_installdir = self.target.config.get('git', 'git_installdir')
        self.env['PATH'] = ':'.join([self.system.path.join(git_installdir, 'bin'),
                                     self.env['PATH']])
        self.env['GIT_EXEC_PATH'] = self.system.path.join(git_installdir,
                                                          'libexec',
                                                          'git-core')
        # gmkpack
        if self.rootpacks_dir is None:
            rootpack = self.target.config.get('gmkpack', 'ROOTPACK')
            self.env['ROOTPACK'] = rootpack
            self._attributes['rootpacks_dir'] = rootpack
        else:
            self.env['ROOTPACK'] = self.rootpacks_dir
            self._attributes['rootpacks_dir'] = self.rootpacks_dir

    def execute(self, rh, kw):  # @UnusedVariable
        from ia4h_scm.algos import IA4H_gitref_to_pack
        pack = IA4H_gitref_to_pack(self.repository,
                                   self.git_ref,
                                   self.packname,
                                   preexisting_pack=self.preexisting_pack,
                                   clean_if_preexisting=self.cleanpack,
                                   rootpacks_dir=self.rootpacks_dir,
                                   homepack=self.homepack,
                                   other_pack_options=self.other_pack_options)


class PackBuildExecutables(AlgoComponent, GmkpackDecoMixin,
                           _CrashWitnessDecoMixin):
    """Compile sources and link executables within a pack (gmkpack)."""

    _footprint = [
        dict(
            info = "Compile sources and link executables within a pack (gmkpack).",
            attr = dict(
                kind = dict(
                    values   = ['pack_build_executables'],
                ),
                packname = dict(
                    info = "The pack to be compiled.",
                ),
                programs = dict(
                    info = "Programs to be built.",
                    optional = True,
                    default = '__usual__'
                ),
                regenerate_ics = dict(
                    info = "Whether to regenerate or not the ics_<program> scripts.",
                    type = bool,
                    optional = True,
                    default = True
                    ),
                other_options = dict(
                    info = "Other options (cf. ics_build_for()).",
                    type = FPDict,
                    optional = True,
                    default = dict(),
                ),
                fatal_build_failure = dict(
                    info = "Whether to make fatal build errors, for any or at the end.",
                    optional = True,
                    default = '__any__',
                    values = ['__any__', '__finally__', '__none__']
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from ia4h_scm.algos import pack_build_executables
        pack_build_executables(self.packname,
                               programs=self.programs,
                               silent=True,  # so that output goes in a file
                               regenerate_ics=self.regenerate_ics,
                               cleanpack=self.cleanpack,
                               other_options=self.other_options,
                               homepack=self.homepack,
                               fatal_build_failure=self.fatal_build_failure,
                               dump_build_report=True)
