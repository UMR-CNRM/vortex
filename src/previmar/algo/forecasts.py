#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import re

import footprints

from vortex.algo.components import Parallel

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class SurgesCouplingForecasts(Parallel):
    """"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycomcoupling'],
            ),
            config_name = dict(
                info     = "Name of configuration",
                default  = "",
                optional = True,
                type     = str,
            ),
            numod = dict(
                info     = "model ID",
                optional = True,
                default  = 165,
            ),
            codmod = dict(
                info     = "Data base BDAP Name of modele",
                type     = str,
                optional = True,
                default  = '',
            ),
            fcterm = dict(
                default  = 6,
                optional = True,
            ),
            freq_forcage = dict(
                info     = "Atmospheric grib forcing frequency (minutes)",
                default  = 180,
                optional = True,
            ),
            rstfin = dict(
                info     = "Term max of saving restart files",
                default  = 6,
                optional = True,
            ),
            flyargs = dict(
                default = ('ASUR', 'PSUR',),
            ),
            flypoll = dict(
                default = 'iopoll_marine',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself."""
        super(Parallel, self).prepare(rh, opts)
        if opts.get('mpitool', True):
            self.export('mpitool')

        # Tweak the pseudo hycom namelists New version  !
        for namsec in self.context.sequence.effective_inputs(role = re.compile('FileConfig')):

            r = namsec.rh

            term = str(self.fcterm)
            basedate = r.resource.date
            date = basedate.ymdh
            reseau = basedate.hh

            # Creation Dico des valeurs/cle a changer selon experience
            dico = {}
            if r.resource.param == 'ms':  # tideonly experiment
                dico["heures"] = term
                dico["savfin"] = term
                dico["rstfin"] = str(self.rstfin)
                dico["dateT0"] = date
            else:  # full experiment
                dico["heures"] = term
                dico["savfin"] = term
                dico["h_rese"] = reseau
                dico["modele"] = r.provider.vconf.upper()[-3:]
                xp = r.provider.vconf[-5:-3]
                mode_map = dict(fc= 'PR', an='AA')
                dico["anapre"] = mode_map.get(xp, xp)
                dico["nmatm"]  = str(self.freq_forcage)
                dico["codmod"] = self.codmod
                dico["imodel"] = str(self.numod)
                dico["kmodel"] = self.config_name

            # modification du content
            paramct = r.contents
            paramct.substitute(dico)
            r.save()
            r.container.cat()

        # Promises should be nicely managed by a co-process
        if self.promises:
            self.io_poll_kwargs = dict(model=rh.resource.model)
            self.flyput = True
        else:
            self.flyput = False

    def execute(self, rh, opts):
        """Jump into the correct working directory."""
        tmpwd = 'EXEC_OASIS'
        logger.info('Temporarily change the working dir to ./%s', tmpwd)
        with self.system.cdcontext(tmpwd):
            super(SurgesCouplingForecasts, self).execute(rh, opts)


class SurgesCouplingInterp(SurgesCouplingForecasts):
    """Algo for interpolation case, not documented yet"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycominterp'],
            ),
        )
    )
