# -*- coding: utf-8 -*-

"""
AlgoComponents for MOCAGE post-processing.
"""

from __future__ import absolute_import, print_function, division, unicode_literals

from collections import defaultdict
import re

from bronx.datagrip.namelist import NamelistBlock
from bronx.fancies import loggers
from bronx.syntax.externalcode import ExternalCodeImportChecker
import footprints

from vortex.algo.components import BlindRun, Expresso, AlgoComponentError
from vortex.syntax.stdattrs import model

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class PPCamsBDAP(BlindRun):
    """
    Post-processing of mocage/cams fc for BDAP.
    """

    _footprint = [
        model,
        dict(
            info = 'Post-processing of mocage/cams fc for BDAP',
            attr = dict(
                kind = dict(
                    values   = ['ppcamsbdap'],
                ),
                model = dict(
                    values   = ['mocage']
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'namelistgrib2.nam',
                ),
                daily_values = dict(
                    info      = "Create daily statistics files.",
                    type     = bool,
                    optional = True,
                    default  = False,
                ),
                daily_species = dict(
                    info     = "The list of species to process in daily statistics files.",
                    type     = footprints.FPList,
                    optional = True,
                    default  = footprints.FPList(['O_x', 'NO_2', 'NO', 'CO', 'SO_2', 'PM10', 'PM2.5']),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ppcamsbdap'

    def compute_daily_values(self, rh):
        """Compute daily statistics on forecast outputs."""
        numpy_checker = ExternalCodeImportChecker('numpy')
        with numpy_checker:
            import numpy as np
        netcdf_checker = ExternalCodeImportChecker('netCDF4')
        with netcdf_checker:
            from netCDF4 import Dataset, MFDataset
        if not (numpy_checker.is_available() and netcdf_checker.is_available()):
            raise AlgoComponentError('The numpy and netCDF4 packages need to be installed ' +
                                     'when "daily_stats" is True.')
        if rh.resource.geometry.area not in self.stats_files:
            self.stats_files[rh.resource.geometry.area] = list()
            if rh.resource.term.hour % 24 == 0:
                return
        self.stats_files[rh.resource.geometry.area].append(rh.container.localpath())
        if rh.resource.term.hour % 24 != 0:
            return
        else:
            # Open all the files simultaneously for the day considered
            all_files = MFDataset(self.stats_files[rh.resource.geometry.area])
            # Read a single example file
            example_file = Dataset(self.stats_files[rh.resource.geometry.area][0])
            # Open the output files
            output_file = Dataset('ppstats.mocage-daily.{}+{:04d}.netcdf'.format(
                rh.resource.geometry.area,
                rh.resource.term.hour), 'w')
            # Copy global attributes
            output_file.setncatts({k: example_file.getncattr(k) for k in example_file.ncattrs()})
            # Copy the dimensions
            for dim_name, dim_values in example_file.dimensions.items():
                output_file.createDimension(dim_name,
                                            len(dim_values) if not dim_values.isunlimited()
                                            else None)
            # Process each variable
            for var_name, var_values in example_file.variables.items():
                var_dim = len(var_values.dimensions)
                # 1D and 2D variables are just copied in the output files
                if var_dim < 3:
                    output_var = output_file.createVariable(var_name,
                                                            var_values.datatype,
                                                            var_values.dimensions)
                    output_var.setncatts({k: var_values.getncattr(k) for k in var_values.ncattrs()})
                    output_var[:] = var_values[:]
                # Other variables are processed
                elif var_name in self.daily_species:
                    # Read the whole data
                    data = np.array(all_files.variables[var_name][:])
                    # Daily mean in each grid-point
                    output_var = output_file.createVariable(var_name + '_mean', var_values.datatype,
                                                            var_values.dimensions)
                    output_var.setncatts({k: var_values.getncattr(k) for k in var_values.ncattrs()})
                    output_var[:] = np.mean(data, axis=0, keepdims=True)
                    # Daily maximum in each grid-point
                    output_var = output_file.createVariable(var_name + '_max', var_values.datatype,
                                                            var_values.dimensions)
                    output_var.setncatts({k: var_values.getncattr(k) for k in var_values.ncattrs()})
                    output_var[:] = np.max(data, axis=0, keepdims=True)
            # Close the files
            all_files.close()
            example_file.close()
            output_file.close()
            self.stats_files[rh.resource.geometry.area] = list()

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system
        if self.daily_values:
            self.stats_files = dict()
        # Namelist
        namelists = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        template_multi = r'namelistgrib2_(\w+)\.nam'
        if len(namelists) == 0:
            message = 'there must be at least one namelist'
            logger.critical(message)
            raise ValueError(message)
        elif len(namelists) == 1:
            namrh = namelists[0].rh
            if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
                logger.critical('The namelist cannot be named "%s".', self.namelist_name)
                raise ValueError()
            geometries = (None, )
        else:
            geometries = list(map(lambda n: re.match(template_multi, n.rh.container.localpath()), namelists))
            if not all(geometries):
                message = 'If there is more than 1 Namelist, they must be named "namelistgrib2_DOM.nam" .  STOP'
                logger.critical(message)
                raise ValueError(message)
            else:
                geometries = [m.group(1) for m in geometries]
        # loop on domains to construct the reference Namelists
        if None in geometries:
            maccraq_blocks = defaultdict(lambda: maccraq_blocks[None])
            contents = defaultdict(lambda: contents[None])
        else:
            maccraq_blocks = dict()
            contents = dict()
        for namelist, geometry in zip(namelists, geometries):
            logger.info('geometry : %s, namelist : %s',
                        str(geometry), namelist.rh.container.localpath())
            contents[geometry] = namelist.rh.contents
            maccraq_blocks[geometry] = NamelistBlock(name='MACCRAQ_IN')
            maccraq_blocks[geometry].update(namelist.rh.contents['MACCRAQ_IN'])
        # HM files from forecast
        hmrh = self.context.sequence.effective_inputs(role='HMFiles',
                                                      kind='gridpoint')
        # overwrite hmrh by the ascending sort of the hmrh list
        hmrh.sort(key=lambda s: s.rh.resource.term)
        for i in hmrh:
            r = i.rh
            # wait for the next HM netcdf file to be translated in grib2 format
            self.grab(i, comment='forecast outputs moved to grib2 format')
            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                  r.resource.term.fmthm))
            actualdate = r.resource.date + r.resource.term
            # optionally compute daily statistics
            if self.daily_values:
                self.compute_daily_values(r)
            # Get a temporary namelist container
            newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')
            # Substitute macros in namelist
            myblock = contents[r.resource.geometry.area]['MACCRAQ_IN']
            myblock.clear()
            myblock.update(maccraq_blocks[r.resource.geometry.area])
            myblock.addmacro('YYYY', actualdate.year)
            myblock.addmacro('MM', actualdate.month)
            myblock.addmacro('DD', actualdate.day)
            myblock.addmacro('HH', actualdate.hour)
            myblock.addmacro('YYYYMMJJBASE', int(r.resource.date.ymd))
            myblock.addmacro('ST', int(r.resource.term.hour))
            contents[r.resource.geometry.area].rewrite(newcontainer)
            newcontainer.cat()
            # Link in the forecast file
            self.system.softlink(r.container.localpath(), 'HMFILE.nc')
            # Execute
            super(PPCamsBDAP, self).execute(rh, opts)
            newcontainer.clear()
            actualname = 'MFM_' + actualdate.ymdh + '.grib2'
            if self.system.path.exists('MFM_V5-.grib2'):
                sh.mv('MFM_V5-.grib2', actualname)
            if self.system.path.exists('MFM_V5+.grib2'):
                sh.mv('MFM_V5+.grib2', actualname)
            sh.rmall('HMFILE.nc', 'HM_HYBRID.nc', 'HM.nc')
            # The grib2 output may be promised for BDAP transferts : put method applied to these outputs
            # put these outputs in the cache ; IGA will perform the following actions.
            expected = [x for x in self.promises
                        if (re.match(actualname, x.rh.container.localpath()))]
            for thispromise in expected:
                thispromise.put(incache=True)


class MkStatsCams(Expresso):

    _footprint = dict(
        info = 'Produce some statistics after a mocage forecast',
        attr = dict(
            interpreter = dict(
                optional = True,
                default  = 'python',
                values = ['python', 'current'],
            ),
            engine = dict(
                values = ['mkstcams']
            )
        )
    )

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        hmfiles = self.context.sequence.effective_inputs(
            role='HMBroadcastFiles',
            kind='gridpoint'
        )

        # We take any input file to guess prefix and mask
        example = hmfiles[0].rh

        # Let's assume that prefix and mask are separated by a '+' and split filename
        actualprefix, actualmask = example.container.localpath().split('+', 1)

        # Replacing any leading digit with a wildcard '?'
        x = re.match(r'(\d+)', actualmask)
        if x:
            digits = len(x.group(0))
            actualmask = '?' * digits + actualmask[digits:]

        return dict(
            prefix='"' + actualprefix + '+"',
            mask='"' + actualmask + '"',
            verbose='',
        )
