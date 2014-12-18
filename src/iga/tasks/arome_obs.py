#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex
from vortex import toolbox
from vortex.layout.nodes import Driver

from iga.tools.op   import register
from iga.tools.apps import OpTask


def setup(t, **kw):
    return Driver(
        tag    = 'obsprep',
        ticket = t,
        nodes  = [
            Batodb(tag='batodb', ticket=t, **kw),
            AvgATMS(tag='avgatms', ticket=t, **kw),
        ]
    )


class Batodb(OpTask):

    def refill(self):
        """Cold start for AROME obsprocessing: get RAW observations files."""

        t = self.ticket

        self.reshape_starter(full=('refdata', 'obs'))

        if 'refdata' in self.starter:

            self.sh.title('Refill Refdata')
            tb01 = toolbox.input(
                role         = 'RefdataGlobal',
                format       = 'ascii',
                kind         = 'refdata',
                local        = 'REFDATA',
                namespace    = '[suite].archive.fr',
                part         = 'all',
                suite        = self.conf.suitebg,
            )
            print t.prompt, 'tb01 =', tb01

            tb01 = toolbox.output(
                role         = 'RefdataGlobal',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'ascii',
                kind         = 'refdata',
                local        = 'REFDATA',
                part         = 'all',
            )
            print t.prompt, 'tb01 =', tb01

        if 'obs' in self.starter:

            self.sh.title('Refill Raw Observations')
            tb02 = tbmap = toolbox.input(
                role         = 'Obsmap',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'obsmap',
                local        = 'batodb_map',
            )
            print t.prompt, 'tb02 =', tb02

            tb03 = toolbox.input(
                role         = 'Observations',
                fatal        = False,
                format       = '[helper:getfmt]',
                helper       = tbmap[0].contents,
                kind         = 'observations',
                local        = '[actualfmt].[part]',
                model        = self.conf.obs_model,
                namespace    = '[suite].archive.fr',
                part         = tbmap[0].contents.dataset(),
                stage        = 'void',
                suite        = self.conf.suitebg,
            )
            print t.prompt, 'tb03 =', tb03

            tb03 = toolbox.output(
                role         = 'Observations',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                fatal        = False,
                format       = '[helper:getfmt]',
                helper       = tbmap[0].contents,
                kind         = 'observations',
                local        = '[actualfmt].[part]',
                model        = self.conf.obs_model,
                part         = tbmap[0].contents.dataset(),
                stage        = 'void',
            )
            print t.prompt, 'tb03 =', tb03

    def process(self):
        """Loop over raw observations for conversion in ODB sets."""

        t = self.ticket

        if self.fetch in self.steps:

            #-------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb01')
            tb01 = toolbox.input(
                role         = 'RefdataGlobal',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'ascii',
                kind         = 'refdata',
                local        = 'REFDATA',
                part         = 'all',
            )
            print t.prompt, 'tb01 =', tb01

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb02 = tbmap')
            tb02 = tbmap = toolbox.input(
                role         = 'Obsmap',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'obsmap',
                local        = 'batodb_map',
            )
            print t.prompt, 'tb02 =', tb02

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb03')
            tb03 = toolbox.input(
                role         = 'Observations',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                fatal        = False,
                format       = '[helper:getfmt]',
                helper       = tbmap[0].contents,
                kind         = 'observations',
                local        = '[actualfmt].[part]',
                model        = self.conf.obs_model,
                part         = tbmap[0].contents.dataset(),
                stage        = 'void',
            )
            print t.prompt, 'tb03 =', tb03

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb04')
            tb04 = toolbox.input(
                role         = 'BatodbConfigurationFile',
                format       = 'ascii',
                genv         = self.conf.arpege_cycle,
                kind         = 'batodbconf',
                local        = 'param.cfg',
                model        = 'arpege',
            )
            print t.prompt, 'tb04 =', tb04

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb05')
            tb05 = toolbox.input(
                role         = 'GPSList',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'gpslist',
                local        = 'list_gpssol',
            )
            print t.prompt, 'tb05 =', tb05

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb06')
            tb06 = toolbox.input(
                role         = 'NamelistBatodb',
                binary       = 'batodb',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namutil',
                local        = 'NAMELIST',
                source       = 'namel_bator',
            )
            print t.prompt, 'tb06 =', tb06

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb07')
            tb07 = toolbox.input(
                role         = 'NamelistLamflag',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namelist',
                local        = 'NAM_lamflag',
                source       = 'namel_lamflag_odb.[geometry:area]',
            )
            print t.prompt, 'tb07 =', tb07

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb08')
            tb08 = toolbox.input(
                role         = 'NamelistSeviri',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namelist',
                local        = 'namelist_rgb',
                source       = 'namel_rgb',
            )
            print t.prompt, 'tb08 =', tb08

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb09 = tbsev')
            tb09 = tbsev = toolbox.input(
                role         = 'RefdataSeviri',
                empty        = True,
                format       = 'ascii',
                kind         = 'refdata',
                local        = 'refdata.sev',
                magic        = 'magic://void',
                part         = 'sev',
            )
            print t.prompt, 'tb09 =', tb09

            #-------------------------------------------------------------------------------

            # Inline shell source
            tbsev[0].contents.append(['sev', 'GRIB', 'sev', self.conf.rundate.ymd, self.conf.rundate.hh])
            tbsev[0].save()
            tbsev[0].container.cat()


            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb11')
            tb11 = toolbox.input(
                role         = 'BlacklistGlobal',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'blacklist',
                local        = 'LISTE_NOIRE_DIAP',
                scope        = 'global',
            )
            print t.prompt, 'tb11 =', tb11

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb12')
            tb12 = toolbox.input(
                role         = 'BlacklistLocal',
                format       = 'ascii',
                genv         = self.conf.cycle,
                kind         = 'blacklist',
                local        = 'LISTE_LOC',
                scope        = 'local',
            )
            print t.prompt, 'tb12 =', tb12

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox executable tb13 = tbio')
            tb13 = tbio = toolbox.executable(
                role         = 'Binary',
                format       = 'bullx',
                genv         = self.conf.arpege_cycle,
                kind         = 'odbioassign',
                local        = 'ioassign.x',
            )
            print t.prompt, 'tb13 =', tb13

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox executable tb14 = tbx')
            tb14 = tbx = toolbox.executable(
                role         = 'Binary',
                format       = 'bullx',
                genv         = self.conf.arpege_cycle,
                kind         = 'batodb',
                local        = 'BATODB.EX',
            )
            print t.prompt, 'tb14 =', tb14

        #===================================================================================

        if self.compute in self.steps:

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox algo tb15 = tbalgo')
            tb15 = tbalgo = toolbox.algo(
                engine       = 'parallel',
                ioassign     = tbio[0].container.localpath(),
                kind         = 'raw2odb',
                lamflag      = True,
                npool        = self.conf.npool,
                slots        = self.conf.slots,
            )
            print t.prompt, 'tb15 =', tb15

            for bin in tbx:
                tbalgo.run(bin, mpiopts=self.conf.mpiopts)

        #===================================================================================

        if self.backup in self.steps:

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb16 = tbmapout')
            tb16 = tbmapout = toolbox.output(
                role         = 'ObsmapUsed',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'ascii',
                kind         = 'obsmap',
                local        = 'batodb_map.out',
                model        = self.conf.obs_model,
                stage        = self.conf.mapstages,
            )
            print t.prompt, 'tb16 =', tb16

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb17')
            tb17 = toolbox.output(
                role         = 'ObservationsODB',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'odb',
                kind         = 'observations',
                local        = 'ECMA.[part]',
                model        = self.conf.obs_model,
                part         = tbmapout[0].contents.odbset(),
                stage        = 'split',
            )
            print t.prompt, 'tb17 =', tb17

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb18')
            tb18 = toolbox.output(
                role         = 'Listing',
                binary       = 'batodb',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'ascii',
                kind         = 'listing',
                local        = 'listing.[part]',
                part         = tbmapout[0].contents.odbset(),
                task         = self.tag,
            )
            print t.prompt, 'tb18 =', tb18


class AvgATMS(OpTask):

    def process(self):
        """Loop over raw observations for conversion in ODB sets."""

        t = self.ticket

        if self.fetch in self.steps:

            self.sh.title('Toolbox input tb01')
            tb01 = toolbox.input(
                role         = 'Observations',
                block        = self.conf.block,
                complete     = True,
                experiment   = self.conf.xpid,
                format       = 'odb',
                intent       = 'in',
                kind         = 'observations',
                local        = 'ECMA',
                part         = 'atms',
                stage        = 'split',
            )
            print t.prompt, 'tb01 =', tb01

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb02')
            tb02 = toolbox.input(
                role         = 'AtmsMask',
                format       = 'ascii',
                genv         = self.conf.arpege_cycle,
                kind         = 'atmsmask',
                local        = 'mask.atms',
            )
            print t.prompt, 'tb02 =', tb02

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox executable tb03 = tbio')
            tb03 = tbio = toolbox.executable(
                role         = 'Binary',
                format       = 'bullx',
                genv         = self.conf.arpege_cycle,
                kind         = 'odbioassign',
                local        = 'ioassign.x',
            )
            print t.prompt, 'tb03 =', tb03

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox executable tb04 = tbx')
            tb04 = tbx = toolbox.executable(
                role         = 'Binary',
                format       = 'bullx',
                genv         = self.conf.arpege_cycle,
                kind         = 'odbtools',
                local        = 'shuffle',
            )
            print t.prompt, 'tb04 =', tb04

        #===================================================================================

        if self.compute in self.steps:


            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox algo tb05 = tbalgo')
            tb05 = tbalgo = toolbox.algo(
                engine       = 'parallel',
                ioassign     = tbio[0].container.localpath(),
                kind         = 'average',
                npool        = self.conf.npool,
                slots        = '7',
            )
            print t.prompt, 'tb05 =', tb05

            for bin in tbx:
                tbalgo.run(bin)

        #===================================================================================

        if self.backup in self.steps:

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb06')
            tb06 = toolbox.output(
                role         = 'ObservationsAtms',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                fatal        = False,
                format       = 'odb',
                kind         = 'observations',
                local        = 'ECMA.[part]',
                part         = 'atms',
                stage        = 'average',
            )
            print t.prompt, 'tb06 =', tb06


class MergeVarBC(OpTask):

    def refill(self):
        """Cold start for AROME forecast: AROME Analysis and ARPEGE boundaries"""

        t = self.ticket

        self.reshape_starter(full=('varbc',))

        if 'varbc' in self.starter:
            self.sh.title('Refill ARPEGE VarBC')
            tb01 = toolbox.input(
                role         = 'VarbcOP',
                format       = 'ascii',
                intent       = 'in',
                kind         = 'varbc',
                local        = 'VARBC.cycle',
                mixmodel     = 'arpege',
                namespace    = '[suite].archive.fr',
                suite        = self.conf.suitebg,
            )
            print t.prompt, 'tb01 =', tb01

            tb01 = toolbox.output(
                role         = 'VarbcOP',
                block        = '4dupd2',
                format       = 'ascii',
                intent       = 'in',
                kind         = 'varbc',
                local        = 'VARBC.cycle',
                model        = 'arpege',
                vapp         = '[model]',
                vconf        = 'france',
                experiment   = self.conf.suitebg,
            )
            print t.prompt, 'tb01 =', tb01

    def process(self):
        """Merge VarBC files."""

        t = self.ticket

        if self.fetch in self.steps:

            self.sh.title('Toolbox input tb01')
            tb01 = toolbox.input(
                role         = 'VarbcOP',
                block        = '4dupd2',
                format       = 'ascii',
                intent       = 'in',
                kind         = 'varbc',
                local        = 'VARBC.cycle',
                model        = 'arpege',
                vapp         = '[model]',
                vconf        = 'france',
                experiment   = self.conf.suitebg,
            )
            print t.prompt, 'tb01 =', tb01

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox input tb02')
            tb02 = toolbox.input(
                role         = 'VarbcPT3H',
                block        = 'minim',
                date         = '{0:s}/-PT{1:s}H'.format(self.conf.date.ymdh, self.conf.assim_step),
                experiment   = self.conf.xpid,
                format       = 'ascii',
                intent       = 'in',
                kind         = 'varbc',
                local        = 'VARBC.cycle2',
            )
            print t.prompt, 'tb02 =', tb02

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox executable tb03 = tbx')
            tb03 = tbx = toolbox.executable(
                role         = 'Binary',
                format       = 'bullx',
                genv         = self.conf.arpege_cycle,
                kind         = 'varbctool',
                local        = 'MERGE_VARBC.EX',
            )
            print t.prompt, 'tb03 =', tb03
            print

        #===================================================================================

        if self.compute in self.steps:


            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox algo tb04 = tbalgo')
            tb04 = tbalgo = toolbox.algo(
                engine       = 'parallel',
                kind         = 'mergevarbc',
            )
            print t.prompt, 'tb04 =', tb04

            for bin in tbx:
                tbalgo.run(bin)

        #===================================================================================

        if self.backup in self.steps:

            #-------------------------------------------------------------------------------

            self.sh.title('Toolbox output tb05')
            tb05 = toolbox.output(
                role         = 'VarbcMerged',
                block        = self.conf.block,
                experiment   = self.conf.xpid,
                format       = 'ascii',
                kind         = 'varbc',
                local        = 'VARBC.cycle_out',
                stage        = 'merge',
            )
            print t.prompt, 'tb05 =', tb05
