# -*- coding: utf-8 -*-

"""
All kinds of AlgoComponents used to prepare Mocage runs (deals with external forcings).
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import six
from collections import defaultdict
from functools import partial
import io

from bronx.datagrip.namelist import NamelistBlock
from bronx.fancies import loggers
from bronx.stdtypes import date
from bronx.syntax.iterators import pcn

import footprints

from vortex.algo.components import Parallel, BlindRun, AlgoComponentError
from vortex.syntax.stdattrs import a_date, model

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class CorrOmegaSurf(Parallel):
    """Correction of vertical velocity at surface level."""

    _footprint = [
        model,
        dict(
            info = 'Correction of vertical velocity at surface level',
            attr = dict(
                kind = dict(
                    values = ['corromegasurf'],
                ),
                model = dict(
                    values = ['mocage']
                ),
                mpiconflabel = dict(
                    default  = 'mocage'
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'corromegasurf'

    def prepare(self, rh, opts):

        # Let ancestors handling most of the env setting
        super(CorrOmegaSurf, self).prepare(rh, opts)

        sh = self.system

        gridrh = self.context.sequence.effective_inputs(
            role='AltitudeFields',
            kind='gridpoint'
        )
        gridrh.sort(key=lambda s: s.rh.resource.term)

        sh.remove('fort.2')
        list_file = [six.text_type(filerh.rh.container.localpath()) for filerh in gridrh]
        list_file = "\n".join([six.text_type(len(list_file)), ] + list_file)

        with io.open('fort.2', 'w') as fnam:
            fnam.write(list_file)
        sh.cat('fort.2', output=False)


class AbstractSumoForcing(Parallel):
    """Abstract AlgoComponnent for any forcing execution based on Sumo."""

    _abstract = True
    _footprint = [
        model,
        dict(
            info = 'Any kind of forcing task based on the Sumo executable',
            attr = dict(
                kind = dict(
                ),
                cfgfile = dict(
                    info     = 'Radical of the name of the configuration file',
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'SUMO_IN',
                ),
                model = dict(
                    values   = ['mocage']
                ),
                mpiconflabel = dict(
                    default  = 'mocage'
                )
            )
        )
    ]

    def _crit_error(self, errmsg):
        """Log an error message (**errmsg**) and raise an exception."""
        logger.critical(errmsg)
        raise AlgoComponentError(errmsg)

    @property
    def _sumo_nam_refblock(self):
        """Find the Sumo namelist in the inputs list and return the Sume namelist block."""
        namsec = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namsec) != 1:
            self._crit_error('There must be exactly one namelist for sumo execution.')
        # Read the namelist block
        namrh = namsec[0].rh
        if (not namrh.container.is_virtual() and
                self.system.path.basename(namrh.container.localpath()) == self.namelist_name):
            self._crit_error('The namelist cannot be named "{:s}".'.format(self.namelist_name))
        namcontent = namrh.contents
        refblock = NamelistBlock(self.namelist_name)
        refblock.update(namcontent[self.namelist_name])
        # This way the initial namelist will never be modified
        namrh.reset_contents()
        return namcontent, refblock

    def _sumo_nam_setcontent(self, namblock, actualdate, domain):
        """Update the Sumo namelist block."""
        namblock.addmacro('YYYY', actualdate.year)
        namblock.addmacro('MM', actualdate.month)
        namblock.addmacro('DD', actualdate.day)
        namblock.addmacro('DOMAIN', domain)
        namblock.addmacro('CFGFILE', self.cfgfile + '.' + domain + '.cfg')

    def _sumo_nam_rewrite(self, namcontent, refblock, actualdate, domain):
        """Update the Sumo namelist and write it to the appropriate location."""
        # Update the sumo namelist block
        myblock = namcontent[self.namelist_name]
        myblock.clear()
        myblock.update(refblock)
        self._sumo_nam_setcontent(myblock, actualdate, domain)
        # Get a temporary namelist container to host the domain specific namelist
        newcontainer = footprints.proxy.container(filename=self.namelist_name,
                                                  mode='w', format='txt')
        namcontent.rewrite(newcontainer)
        self.system.subtitle('Rewritten namelist ({:s})'.format(self.namelist_name))
        newcontainer.cat(mode='r')
        return newcontainer

    def _sumo_exec(self, namcontent, refblock, actualdate, domain, rh, opts):
        """Update the Sumo namelist and execute the Sumo binary."""
        namcontainer = self._sumo_nam_rewrite(namcontent, refblock,
                                              actualdate, domain)
        try:
            super(AbstractSumoForcing, self).execute(rh, opts)
        finally:
            namcontainer.clear()


class AbstractSumoForcingWithMeteo(AbstractSumoForcing):
    """Abstract AlgoComponnent for any forcing execution based on Sumo.

    With a cplmto attribute.
    """

    _abstract = True
    _footprint = dict(
        attr = dict(
            cplmto = dict(
                info     = 'Type of the meteo coupling',
                optional = True,
                default  = 'ECMWF',
            ),
        )
    )

    @property
    def _surface_fields_rh(self):
        """The list of ResourceHandlers matching the SurfaceFields role."""
        gribsec = self.context.sequence.effective_inputs(
            role='SurfaceFields',
            kind='gridpoint')
        return [s.rh for s in gribsec]

    def _sumo_nam_setcontent(self, namblock, actualdate, domain):
        """Update the Sumo namelist block."""
        super(AbstractSumoForcingWithMeteo, self)._sumo_nam_setcontent(namblock, actualdate, domain)
        namblock.addmacro('CPLMETEO', self.cplmto)


class Surface(AbstractSumoForcingWithMeteo):
    """AlgoComponent for Sumo."""

    _footprint = dict(
        info = 'Surface',
        attr = dict(
            kind = dict(
                values   = ['surface'],
            ),
            cfgfile = dict(
                optional = True,
                default  = 'RACMOBUS_MACCOPER2016',
            ),
        )
    )

    @property
    def realkind(self):
        return 'surface'

    def execute(self, rh, opts):
        """Standard execution."""
        namcontent, refblock = self._sumo_nam_refblock

        # Grib files from IFS MET*
        gribrh = self._surface_fields_rh
        # Sm files
        smsec = self.context.sequence.effective_inputs(
            role='SMFiles',
            kind='boundary')

        if smsec:
            for r in gribrh:
                self.system.title('Loop on domain {0.geometry.area:s} and term {0.term.fmthm:s}'
                                  .format(r.resource))
                actualdate = r.resource.date + r.resource.term
                self._sumo_exec(namcontent, refblock, actualdate, r.resource.geometry.area,
                                rh, opts)
        else:
            logger.warning('No SM files')


class SurfaceArp(AbstractSumoForcingWithMeteo):
    """AlgoComponent for Sumo (Arpege variant)"""

    _footprint = dict(
        info = 'SurfaceArp',
        attr = dict(
            kind = dict(
                values   = ['surfacearp'],
            ),
            cfgfile = dict(
                optional = True,
                default  = 'RACMOBUS_PREVAIR2016',
            ),
        )
    )

    _INPUTFILES_FMT = 'AMECH{:d}'

    @property
    def realkind(self):
        return 'surfacearp'

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system
        namcontent, refblock = self._sumo_nam_refblock

        # Grib files from Arpege AMECH*:
        # retrieve the domains, put the associated ressource handlers in lists
        domains = defaultdict(partial(defaultdict, list))
        for rhi in self._surface_fields_rh:
            vdate = rhi.resource.date + rhi.resource.term
            vday = date.Date(vdate.year, vdate.month, vdate.day, 0, 0)
            domains[rhi.resource.geometry.area][vday].append(rhi)
        # Sort things up...
        for domainrhs in domains.values():
            for daysrhs in domainrhs.values():
                daysrhs.sort(key=lambda rh: rh.resource.date + rh.resource.term)

        # loop on domains
        for currentdom, domainrhs in sorted(domains.items()):
            sh.title('Loop on domain {0:s}'.format(currentdom))

            for _, currentday, nextday in pcn(sorted(domainrhs)):
                if nextday is None:
                    continue
                sh.title("{:s}: Looping on actualdate={!s}".format(currentdom, currentday))

                dayrhs = domainrhs[currentday] + [domainrhs[nextday][0], ]
                for num, rhi in enumerate(dayrhs, start=1):
                    logger.info('%s: Link on term %s (as %s).', currentdom,
                                rhi.resource.term.fmthm, self._INPUTFILES_FMT.format(num))
                    self.system.softlink(rhi.container.localpath(), self._INPUTFILES_FMT.format(num))

                # Let's run sumo...
                self._sumo_exec(namcontent, refblock, currentday, currentdom, rh, opts)

                # Some cleaning for this domain
                for i in range(len(dayrhs)):
                    sh.rm(self._INPUTFILES_FMT.format(i + 1))


class Fire(AbstractSumoForcing):
    """Algo component for sumo (fire task)"""

    _footprint = dict(
        info = 'Fire',
        attr = dict(
            kind = dict(
                values = ['fire'],
            ),
            cfgfile = dict(
                optional = True,
                default  = 'RACMOBUS_MACCOPER2016_BB',
            ),
        )
    )

    @property
    def realkind(self):
        return 'fire'

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system
        namcontent, refblock = self._sumo_nam_refblock

        # Loop on domains
        obssec = self.context.sequence.effective_inputs(
            role='ObservationsFire',
            kind='obsfire')

        for r_obs in obssec:
            r = r_obs.rh

            sh.title('Loop on domain {0:s}'.format(r.resource.geometry.area))

            # Create symlinks for fire obsfiles
            obsfiles = sh.ls(r.container.localpath())
            for i in obsfiles:
                path = r.container.localpath() + '/' + i
                sh.symlink(path, i)
            # Launch Sumo
            self._sumo_exec(namcontent, refblock,
                            r.resource.date, r.resource.geometry.area,
                            rh, opts)
            # Remove symlinks
            for i in obsfiles:
                sh.remove(i)


class Mktopbd(BlindRun):
    """Algo component for Mktopbd"""

    _footprint = [
        model,
        dict(
            info = 'Mktopbd algo component',
            attr = dict(
                kind = dict(
                    values = ['mktopbd'],
                ),
                basedate = a_date,
                fcterm = dict(
                    info = 'Forecast term',
                    type = date.Time,
                ),
                model = dict(
                    values = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'mktopbd'

    def spawn_stdin_options(self):
        """Build the dictionnary to provide arguments to the binary."""
        return dict(
            fcterm=self.fcterm,
            basedate=self.basedate,
        )
