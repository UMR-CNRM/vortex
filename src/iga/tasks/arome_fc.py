#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex
from vortex import toolbox

from iga.tools.op  import register
from iga.tools.app import Application


def setup(t, **kw):
    return [ Forecast(t, **kw) ]

class Forecast(Application):

    def setup(self, **kw):
        """Default arome forecast experiment settings."""

        t = self.ticket

        #--------------------------------------------------------------------------------------------------
        self.subtitle('Experiment Setup')

        self.conf.update(kw)
        geomodel = vortex.data.geometries.getbyname(self.conf.fc_geometry)

        logger.info('FC term     = %s', str(self.conf.fc_term))
        logger.info('FC terms    = %s', str(self.conf.fc_terms))
        logger.info('FP terms    = %s', str(self.conf.fp_terms))
        logger.info('FC geometry = %s', str(geomodel))
        logger.info('FC domains  = %s', str(self.conf.fp_domains))

        #--------------------------------------------------------------------------------------------------
        self.subtitle('Toolbox defaults')

        toolbox.defaults(
            model      = t.glove.vapp,
            date       = self.conf.rundate,
            cutoff     = t.env.OP_CUTOFF,
            geometry   = geomodel,
            namespace  = 'vortex.cache.fr',
            gnamespace = 'opgco.cache.fr',
        )

        toolbox.defaults.show()

        #--------------------------------------------------------------------------------------------------
        self.subtitle('GCO cycle ' + self.conf.cycle)
        register(t, self.conf.cycle)

        #--------------------------------------------------------------------------------------------------
        self.subtitle('GCO cycle ' + self.conf.arpege_cycle)
        register(t, self.conf.arpege_cycle)

    def process(self):
        """Core processing of an arome forecast experiment."""

        t = self.ticket

        self.sh.title('Actual ENV')
        self.env.mydump()

        if self.fetch in self.steps:

            #--------------------------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb09')
            tb09 = toolbox.input(
                role         = 'LocalClim',
                format       = 'unknown',
                genv         = self.conf.cycle,
                geometry     = self.conf.fp_domains,
                kind         = 'clim_bdap',
                local        = 'const.clim.[geometry::area].[month]',
                month        = '[date:ymd]',
            )
            print t.prompt, 'tb09 =', tb09
            print

            #--------------------------------------------------------------------------------------------------
            self.sh.title('Toolbox input tb13')
            tb13 = toolbox.input(
                role         = 'Namelist',
                binary       = '[model]',
                format       = 'ascii',
                genv         = self.conf.cycle,
                intent       = 'inout',
                kind         = 'namelist',
                local        = 'fort.4',
                source       = 'namel_[geometry::area]_previ_dyn',
            )
            print t.prompt, 'tb13 =', tb13
            print
