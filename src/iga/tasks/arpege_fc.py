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
    return Driver(tag='arpegefc', ticket=t, nodes=[Forecast(tag='forecast', ticket=t, **kw)])

class Forecast(OpTask):

    _tag_topcls = False

    def refill(self):
        """Cold start for AROME forecast: AROME Analysis and ARPEGE boundaries"""

        t = self.ticket

        self.reshape_starter(full=('analysis',))

        if 'analysis' in self.starter:
            self.sh.title('Refill Analysis')
            tb01 = toolbox.input(
                role         = 'Analysis',
                block        = 'canari',
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
                block        = 'canari',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT',
            )
            print t.prompt, 'tb01 =', tb01
            print

    def process(self):
        """Core processing of an arome forecast experiment."""

        t = self.ticket

        if self.fetch in self.steps:

            self.sh.title('Toolbox promise tb01')
            tb01 = toolbox.promise(
                role         = 'ModelState',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'historic',
                local        = 'ICMSHFCST+[term::fmth]',
                term         = self.conf.fc_terms,
            )
            print t.prompt, 'tb01 =', tb01
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox promise tb02')
            tb02 = toolbox.promise(
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
            print t.prompt, 'tb02 =', tb02
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb03')
            tb03 = toolbox.input(
                role         = 'Analysis',
                block        = 'canari',
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'analysis',
                local        = 'ICMSHFCSTINIT',
            )
            print t.prompt, 'tb03 =', tb03
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb04')
            tb04 = toolbox.input(
                role         = 'RrtmConst',
                format       = 'unknown',
                genv         = self.conf.cycle,
                kind         = 'rrtm',
                local        = 'rrtm.const.tgz',
            )
            print t.prompt, 'tb04 =', tb04
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb05')
            tb05 = toolbox.input(
                role         = 'RtCoef',
                format       = 'unknown',
                genv         = self.conf.cycle,
                kind         = 'rtcoef',
                local        = 'var.sat.misc_rtcoef.01.tgz',
            )
            print t.prompt, 'tb05 =', tb05
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb06')
            tb06 = toolbox.input(
                role         = 'GlobalClim',
                format       = 'unknown',
                genv         = self.conf.cycle,
                kind         = 'clim_model',
                local        = 'Const.Clim',
                month        = '[date:ymd]',
            )
            print t.prompt, 'tb06 =', tb06
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb07')
            tb07 = toolbox.input(
                role         = 'LocalClim',
                format       = 'unknown',
                genv         = self.conf.cycle,
                geometry     = self.conf.fp_domains,
                kind         = 'clim_bdap',
                local        = 'const.clim.[geometry::area]',
                month        = '[date:ymd]',
            )
            print t.prompt, 'tb07 =', tb07
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb08')
            tb08 = toolbox.input(
                role         = 'Matfilter',
                format       = 'unknown',
                genv         = self.conf.cycle,
                kind         = 'matfilter',
                local        = 'matrix.fil.[scope::area]',
                scope        = self.conf.fp_domains,
            )
            print t.prompt, 'tb08 =', tb08
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb09')
            tb09 = toolbox.input(
                role         = 'Namelist',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namelist',
                local        = 'fort.4',
                source       = self.conf.fc_nam,
            )
            print t.prompt, 'tb09 =', tb09
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb10 = tbdef')
            tb10 = tbdef = toolbox.input(
                role         = 'FullPosMapping',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'namselectdef',
                local        = 'xxt.def',
            )
            print t.prompt, 'tb10 =', tb10
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb11')
            tb11 = toolbox.input(
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
            print t.prompt, 'tb11 =', tb11
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox executable tb12 = tbx')
            tb12 = tbx = toolbox.executable(
                role         = 'Binary',
                format       = 'bullx',
                genv         = self.conf.cycle,
                kind         = 'mfmodel',
                local        = 'ARPEGE.EX',
            )
            print t.prompt, 'tb12 =', tb12
            print


        #===================================================================================

        if self.compute in self.steps or self.backup in self.steps:

            self.sh.title('Toolbox algo tb13 = tbalgo')
            tb13 = tbalgo = toolbox.algo(
                engine       = 'parallel',
                fcterm       = self.conf.fc_term,
                kind         = 'forecast',
                timescheme   = 'sli',
                timestep     = self.conf.timestep,
            )
            print t.prompt, 'tb13 =', tb13
            print

        if self.compute in self.steps:
            for bin in tbx:
                tbalgo.run(bin, mpiopts=self.conf.mpiopts)

        #===================================================================================

        if self.backup in self.steps:

            #-------------------------------------------------------------------------------
            self.sh.subtitle('IO Polling')
            self.io_poll(prefix=tbalgo.flyput_args())

            self.sh.title('Toolbox output tb14')
            tb14 = toolbox.output(
                role         = 'ModelState',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                kind         = 'historic',
                local        = 'ICMSHFCST+[term::fmth]',
                promise      = True,
                term         = self.conf.fc_terms,
            )
            print t.prompt, 'tb14 =', tb14
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb15')
            tb15 = toolbox.output(
                role         = 'Gridpoint',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'fa',
                geometry     = self.conf.fp_domains,
                kind         = 'gridpoint',
                local        = 'PFFCST[geometry::area]+{glob:h:\d+}',
                namespace    = 'vortex.cache.fr',
                nativefmt    = '[format]',
                origin       = 'historic',
                promise      = True,
                term         = '[glob:h]',
            )
            print t.prompt, 'tb15 =', tb15
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb16')
            tb16 = toolbox.output(
                role         = 'Isp',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'foo',
                kind         = 'isp',
                local        = 'fort.91',
            )
            print t.prompt, 'tb16 =', tb16
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb17')
            tb17 = toolbox.output(
                role         = 'Dhfd',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'lfa',
                kind         = 'ddh',
                local        = 'DHFDLFCST+{glob:h:\d+}',
                scope        = 'dlimited',
                term         = '[glob:h]',
            )
            print t.prompt, 'tb17 =', tb17
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb18')
            tb18 = toolbox.output(
                role         = 'Dhfg',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'lfa',
                kind         = 'ddh',
                local        = 'DHFGLFCST+{glob:h:\d+}',
                scope        = 'global',
                term         = '[glob:h]',
            )
            print t.prompt, 'tb18 =', tb18
            print

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb19')
            tb19 = toolbox.output(
                role         = 'Dhfz',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'lfa',
                kind         = 'ddh',
                local        = 'DHFZOFCST+{glob:h:\d+}',
                scope        = 'zonal',
                term         = '[glob:h]',
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
