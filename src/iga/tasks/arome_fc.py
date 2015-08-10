#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex
from vortex import toolbox
from vortex.layout.nodes import Driver

from iga.tools.apps import OpTask


def setup(t, **kw):
    return Driver(tag='aromefc', ticket=t, nodes=[Forecast(tag='forecast', ticket=t, **kw)])

class Forecast(OpTask):

    _tag_topcls = False

    def refill(self):
        """Cold start for AROME forecast: AROME Analysis and ARPEGE boundaries"""

        t = self.ticket

        self.reshape_starter(full=('analysis', 'boundaries'), analysis=('init', 'surfan'))

        if 'init' in self.starter:
            self.sh.title('Refill Analysis')
            tb01 = toolbox.input(
                role         = 'Analysis',
                block        = 'pseudotraj',
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT',
                namespace    = '[suite].archive.fr',
                suite        = self.conf.suitebg,
            )
            print t.prompt, 'tb01 =', tb01
            print

            tb01 = toolbox.output(
                role         = 'Analysis',
                block        = 'pseudotraj',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT',
            )
            print t.prompt, 'tb01 =', tb01
            print

        if 'surfan' in self.starter:
            self.sh.title('Refill Surface Analysis')
            tb02 = toolbox.input(
                role         = 'SurfaceAnalysis',
                block        = 'surfan',
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT.sfx',
                model        = 'surfex',
                namespace    = '[suite].archive.fr',
                suite        = self.conf.suitebg,
            )
            print t.prompt, 'tb02 =', tb02
            print

            tb02 = toolbox.output(
                role         = 'SurfaceAnalysis',
                block        = 'surfan',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT.sfx',
                model        = 'surfex',
            )
            print t.prompt, 'tb02 =', tb02
            print

        if 'boundaries' in self.starter:
            cpl0 = list(sorted(set([ 0 ] + self.conf.cpl_terms)))
            self.sh.title('Refill Boundaries')
            tb03 = toolbox.input(
                role         = 'BoundaryConditions',
                block        = self.conf.cpl_block,
                format       = 'fa',
                kind         = 'boundary',
                local        = 'CPLIN+[term:fmthm]',
                source       = self.conf.cpl_model,
                namespace    = '[suite].archive.fr',
                suite        = self.conf.suitebg,
                term         = cpl0,
            )
            print t.prompt, 'tb03 =', tb03
            print

            tb03 = toolbox.output(
                role         = 'BoundaryConditions',
                block        = self.conf.cpl_block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'boundary',
                local        = 'CPLIN+[term:fmthm]',
                source       = self.conf.cpl_model,
                term         = cpl0,
            )
            print t.prompt, 'tb03 =', tb03
            print

    def process(self):
        """Core processing of an arome forecast experiment."""

        t = self.ticket

        if self.fetch in self.steps:

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb01')
            tb01 = toolbox.input(
                role         = 'Analysis',
                block        = 'pseudotraj',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT',
            )
            print t.prompt, 'tb01 =', tb01
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb02')
            tb02 = toolbox.input(
                role         = 'SurfaceAnalysis',
                block        = 'surfan',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT.sfx',
                model        = 'surfex',
            )
            print t.prompt, 'tb02 =', tb02
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb03')
            tb03 = toolbox.input(
                role         = 'BoundaryConditions',
                block        = self.conf.cpl_block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'boundary',
                local        = 'CPLIN+[term:fmthm]',
                source       = self.conf.cpl_model,
                term         = self.conf.cpl_terms,
            )
            print t.prompt, 'tb03 =', tb03
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb04')
            tb04 = toolbox.input(
                role         = 'BoundaryConditions',
                block        = 'pseudotraj',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'CPLIN+START',
            )
            print t.prompt, 'tb04 =', tb04
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb05')
            tb05 = toolbox.input(
                role         = 'GlobalClim',
                format       = 'unknown',
                genv         = self.conf.cycle,
                kind         = 'clim_model',
                local        = 'Const.Clim',
                month        = '[date:ymd]',
            )
            print t.prompt, 'tb05 =', tb05
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb06')
            tb06 = toolbox.input(
                role         = 'LocalClim',
                format       = 'unknown',
                genv         = self.conf.cycle,
                geometry     = self.conf.fp_domains,
                kind         = 'clim_bdap',
                local        = 'const.clim.[geometry::area]',
                month        = '[date:ymd]',
            )
            print t.prompt, 'tb06 =', tb06
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb07')
            tb07 = toolbox.input(
                role         = 'ClimPGD',
                format       = 'fa',
                genv         = self.conf.cycle,
                kind         = 'pgdfa',
                local        = 'Const.Clim.sfx',
            )
            print t.prompt, 'tb07 =', tb07
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb08')
            tb08 = toolbox.input(
                role         = 'CoverParams',
                format       = 'unknown',
                genv         = self.conf.arpege_cycle,
                kind         = 'coverparams',
                local        = 'ecoclimap_covers_param.tgz',
            )
            print t.prompt, 'tb08 =', tb08
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb09')
            tb09 = toolbox.input(
                role         = 'RrtmConst',
                format       = 'unknown',
                genv         = self.conf.arpege_cycle,
                kind         = 'rrtm',
                local        = 'rrtm.const.tgz',
            )
            print t.prompt, 'tb09 =', tb09
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb10')
            tb10 = toolbox.input(
                role         = 'RtCoef',
                format       = 'unknown',
                genv         = self.conf.arpege_cycle,
                kind         = 'rtcoef',
                local        = 'var.sat.misc_rtcoef.01.tgz',
            )
            print t.prompt, 'tb10 =', tb10
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb11 = tbdef')
            tb11 = tbdef = toolbox.input(
                role         = 'FullPosMapping',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'namselectdef',
                local        = 'xxt.def',
            )
            print t.prompt, 'tb11 =', tb11
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb12')
            tb12 = toolbox.input(
                role         = 'FullPosSelection',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                helper       = tbdef[0].contents,
                kind         = 'namselect',
                local        = '[helper::xxtnam]',
                source       = '[helper::xxtsrc]',
                term         = self.conf.fp_terms,
            )
            print t.prompt, 'tb12 =', tb12
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb13')
            tb13 = toolbox.input(
                role         = 'Namelistsurf',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namelist',
                local        = 'EXSEG1.nam',
                source       = 'namel_previ_surfex',
            )
            print t.prompt, 'tb13 =', tb13
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb14')
            tb14 = toolbox.input(
                role         = 'Namelist',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namelist',
                local        = 'fort.4',
                source       = 'namel_[geometry::area]_previ',
            )
            print t.prompt, 'tb14 =', tb14
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox executable tb15 = tbx')
            tb15 = tbx = toolbox.executable(
                role         = 'Binary',
                format       = 'sx',
                genv         = self.conf.cycle,
                kind         = 'mfmodel',
                local        = 'AROME.EX',
                model        = 'arome',
            )
            print t.prompt, 'tb15 =', tb15
            print


        #===================================================================================

        if self.compute in self.steps or self.backup in self.steps:

            self.sh.title('Toolbox algo tb16 = tbalgo')
            tb16 = tbalgo = toolbox.algo(
                engine       = 'parallel',
                fcterm       = self.conf.fc_term,
                kind         = 'lamfc',
                timescheme   = 'sli',
                timestep     = self.conf.timestep,
            )
            print t.prompt, 'tb16 =', tb16
            print

        if self.compute in self.steps:
            for binary in tbx:
                tbalgo.run(binary, mpiopts=self.conf.mpiopts)

        #===================================================================================

        if self.backup in self.steps:

            #-------------------------------------------------------------------------------
            self.sh.subtitle('IO Polling')
            self.io_poll(prefix=tbalgo.flyput_args())

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox output tb17')
            tb17 = toolbox.output(
                role         = 'ModelState',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'historic',
                local        = 'ICMSHFCST+[term:fmth]',
                term         = self.conf.fc_terms,
            )
            print t.prompt, 'tb17 =', tb17
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox output tb18')
            tb18 = toolbox.output(
                role         = 'SurfGuess',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'historic',
                local        = 'ICMSHFCST+[term::fmth].sfx',
                model        = 'surfex',
                term         = '3',
            )
            print t.prompt, 'tb18 =', tb18
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox output tb19')
            tb19 = toolbox.output(
                role         = 'Gridpoint',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                geometry     = self.conf.fp_domains,
                kind         = 'gridpoint',
                local        = 'PFFCST[geometry::area]+[term::fmth]',
                namespace    = 'vortex.cache.fr',
                nativefmt    = '[format]',
                origin       = 'historic',
                term         = self.conf.fp_terms,
            )
            print t.prompt, 'tb19 =', tb19
            print

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox output tb20')
            tb20 = toolbox.output(
                role         = 'Listing',
                binary       = '[model]',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'ascii',
                kind         = 'plisting',
                local        = 'NODE.{glob:a:\d+}_{glob:b:\d+}',
                seta         = '[glob:a]',
                setb         = '[glob:b]',
                task         = self.tag,
            )
            print t.prompt, 'tb20 =', tb20
            print
