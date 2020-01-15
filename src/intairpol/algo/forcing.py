#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

"""
All kinds of AlgoComponents used to prepare Mocage runs (deals with external forcings).
"""

import six
import io
import re

from bronx.datagrip.namelist import NamelistBlock
from bronx.fancies import loggers
from bronx.stdtypes import date

import footprints

from vortex.algo.components import Parallel, BlindRun, Expresso
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


class Surface(Parallel):
    """Algo component for Sumo"""

    _footprint = [
        model,
        dict(
            info = 'Surface',
            attr = dict(
                kind = dict(
                    values   = ['surface'],
                ),
                cfgfile = dict(
                    info     = 'Radical of the name of the configuration file',
                    optional = True,
                    default  = 'RACMOBUS_MACCOPER2016',
                ),
                cplmto = dict(
                    info     = 'Type of the meteo coupling',
                    optional = True,
                    default  = 'ECMWF',
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'SUMO_IN',
                ),
                model = dict(
                    values   = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'surface'

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system

        # Sumo namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for sumo execution. Stop.')
            raise ValueError('There must be exactly one namelist for sumo execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()
        refblock = NamelistBlock(name=self.namelist_name)
        refblock.update(namrh.contents[self.namelist_name])

        # Grib files from IFS MET*
        gribrh = self.context.sequence.effective_inputs(
            role='SurfaceFields',
            kind='gridpoint')
        # Sm files
        smrh = self.context.sequence.effective_inputs(
            role='SMFiles',
            kind='boundary')

        if smrh:
            for i in gribrh:
                r = i.rh
                sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                      r.resource.term.fmthm))
                actualdate = r.resource.date + r.resource.term

                # Get a temporary namelist container
                newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')

                # Substitute macros in namelist
                myblock = namrh.contents[self.namelist_name]
                myblock.clear()
                myblock.update(refblock)
                myblock.addmacro('YYYY', actualdate.year)
                myblock.addmacro('MM', actualdate.month)
                myblock.addmacro('DD', actualdate.day)
                myblock.addmacro('DOMAIN', r.resource.geometry.area)
                myblock.addmacro('CFGFILE', self.cfgfile + '.' + r.resource.geometry.area + '.cfg')
                myblock.addmacro('CPLMETEO', self.cplmto )

                namrh.contents.rewrite(newcontainer)
                newcontainer.cat()

                super(Surface, self).execute(rh, opts)

                newcontainer.clear()
        else:
            logger.warning('No SM files')


class Fire(Parallel):
    """Algo component for sumo (fire task)"""

    _footprint = dict(
        info = 'Fire',
        attr = dict(
            kind = dict(
                values = ['fire'],
            ),
            cfgfile = dict(
                info     = 'Radical of the name of the configuration file',
                optional = True,
                default  = 'RACMOBUS_MACCOPER2016_BB',
            ),
            namelist_name = dict(
                info     = 'Namelist name for the binary',
                optional = True,
                default  = 'SUMO_IN',
            ),
        )
    )

    @property
    def realkind(self):
        return 'fire'

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def execute(self, rh, opts):
        """Standard execution."""

        sh = self.system

        # Sumo namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for sumo execution. Stop.')
            raise ValueError('There must be exactly one namelist for sumo execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()
        refblock = NamelistBlock(name=self.namelist_name)
        refblock.update(namrh.contents[self.namelist_name])

        # Loop on domains
        obsrh = self.context.sequence.effective_inputs(
            role='ObservationsFire',
            kind='obsfire')

        for r_obs in obsrh:
            r = r_obs.rh

            sh.title('Loop on domain {0:s}'.format(r.resource.geometry.area))

            # Create symlinks for fire obsfiles
            obsfiles = sh.ls(r.container.localpath())
            for i in obsfiles:
                path = r.container.localpath() + '/' + i
                sh.symlink(path, i)

            # Get a temporary namelist container
            newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')

            # Substitute macros in namelist
            myblock = namrh.contents[self.namelist_name]
            myblock.clear()
            myblock.update(refblock)
            myblock.addmacro('YYYY', r.resource.date.year)
            myblock.addmacro('MM', r.resource.date.month)
            myblock.addmacro('DD', r.resource.date.day)
            myblock.addmacro('DOMAIN', r.resource.geometry.area)
            myblock.addmacro('CFGFILE', self.cfgfile + '.' + r.resource.geometry.area + '.cfg')

            namrh.contents.rewrite(newcontainer)
            newcontainer.cat()

            super(Fire, self).execute(rh, opts)

            newcontainer.clear()

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
            fcterm   = self.fcterm,
            basedate = self.basedate,
        )

class SurfaceArp(Parallel):
    """Algo component for Sumo"""

    _footprint = [
        model,
        dict(
            info = 'SurfaceArp',
            attr = dict(
                kind = dict(
                    values   = ['surfacearp'],
                ),
                cfgfile = dict(
                    info     = 'Radical of the name of the configuration file',
                    optional = True,
                    default  = 'RACMOBUS_PREVAIR2016',
                ),
                cplmto = dict(
                    info     = 'Type of the meteo coupling',
                    optional = True,
                    default  = 'ARPEGE',
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'SUMO_IN',
                ),
                model = dict(
                    values   = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'surfacearp'

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system

        # Sumo namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for sumo execution. Stop.')
            raise ValueError('There must be exactly one namelist for sumo execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()
        refblock = NamelistBlock(name=self.namelist_name)
        refblock.update(namrh.contents[self.namelist_name])

        # Grib files from Arpege AMECH*
        gribrh = self.context.sequence.effective_inputs(
            role='SurfaceFields',
            kind='gridpoint')
        # Retrieve the domains
        domains = []
        ldom = []

        for i in gribrh:
            r = i.rh
            domains.append(r.resource.geometry.area)
        for i in set(domains):
            ldom.append(i)

        # loop on domains
        for id in set(domains):
            currentdom = id
            sh.title('Loop on domain {0:s} '.format(currentdom))
            sh.rmall('AMECH[1-9][0-9]','AMECH[1-9]')
            num=0
            # loop on terms in the current domain
            #gribrh = self.context.sequence.effective_inputs(
            #                                        role='SurfaceFields',
            #                                        kind='gridpoint',
            #                                        geometry=str(currentdom),)
            logger.info('*avant liens**********' )
            for i in gribrh:
                r = i.rh
                #logger.info('number or files %d ' , len(r))
                if r.resource.geometry.area == str(currentdom):
                     sh.title('Link on term {0:s}'.format(r.resource.term.fmthm))
                     num = num + 1
                     # Link in the Fullpos output file
                     logger.info(' lien**********' )
                     self.system.softlink(r.container.localpath(), 'AMECH' + str(num))
                if num == 1:
                     logger.info('*stocke r0 date **********' )
                     r0 = gribrh[0].rh
                     actualdate = r0.resource.date + r.resource.term

    
            # Get a temporary namelist container
            newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')
    
            # Substitute macros in namelist
            myblock = namrh.contents[self.namelist_name]
            myblock.clear()
            myblock.update(refblock)
            myblock.addmacro('YYYY', actualdate.year)
            myblock.addmacro('MM', actualdate.month)
            myblock.addmacro('DD', actualdate.day)
            #myblock.addmacro('DOMAIN', r.resource.geometry.area)
            #myblock.addmacro('CFGFILE', self.cfgfile + '.' + r.resource.geometry.area + '.cfg')
            myblock.addmacro('DOMAIN', currentdom )
            myblock.addmacro('CFGFILE', self.cfgfile + '.' + currentdom + '.cfg')
            myblock.addmacro('CPLMETEO', self.cplmto )
    
            namrh.contents.rewrite(newcontainer)
            newcontainer.cat()


            ## super(SurfaceArp, self).execute(rh, opts)

            ## newcontainer.clear()
    #else:
    #    logger.warning('No SM files')

            logger.info('*avant sumo**********' )
            super(SurfaceArp, self).execute(rh, opts)

