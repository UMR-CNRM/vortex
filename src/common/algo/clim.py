#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common AlgoComponnent to build model's climatology files.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import copy
import io
import six

import footprints

from vortex.algo.components import BlindRun, AlgoComponent, Parallel
from vortex.data.geometries import HorizontalGeometry
from common.algo.ifsroot import IFSParallel
from bronx.datagrip import namelist

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class BuildPGD(BlindRun):
    """Preparation of physiographic fields for Surfex."""

    _footprint = dict(
        info = "Physiographic fields for Surfex.",
        attr = dict(
            kind = dict(
                values   = ['buildpgd'],
            ),
        )
    )

    def prepare(self, rh, opts):
        """DrHook stuff."""
        super(BuildPGD, self).prepare(rh, opts)
        # Basic exports
        for optpack in ['drhook', 'drhook_not_mpi']:
            self.export(optpack)


class C923(IFSParallel):
    """Preparation of climatologic fields."""

    _footprint = dict(
        info = "Climatologic fields for Arpege/Arome.",
        attr = dict(
            kind = dict(
                values   = ['c923'],
            ),
            step = dict(
                info = """Step of conf 923 (NAMCLI::N923).
                          Defines the kind of fields and database processed.""",
                type = int,
                values = footprints.util.rangex(1, 10)
            ),
            orog_in_pgd = dict(
                info = """Whether orography may be read in a PGD file.
                          (NAMCLA::LIPGD=.TRUE.)""",
                type = bool,
                optional = True,
                default = False,
            ),
            input_orog_name = dict(
                info = "Filename for input orography file (case LNORO=.T.).",
                optional = True,
                default = 'Neworog',
            ),
            xpname = dict(
                default = 'CLIM',
            ),
        )
    )

    def prepare(self, rh, opts):
        super(C923, self).prepare(rh, opts)
        # Namelist
        nam = self.context.sequence.effective_inputs(role=('Namelist',))
        self.algoassert(len(nam) == 1,
                        "One and only one namelist necessary as input.")
        nam = nam[0].rh
        nam.contents['NAMMCC']['N923'] = self.step
        nam.contents.setmacro('LPGD', self.orog_in_pgd)
        nam.save()
        # check PGD if needed
        if self.orog_in_pgd:
            pgd = self.context.sequence.effective_inputs(role=('Pgd',))
            if len(pgd) == 0:
                raise ValueError("As long as 'orog_in_pgd' attribute of this " +
                                 "algo component is True, a 'Role: Pgd' " +
                                 "resource must be provided.")
            pgd = pgd[0].rh
            if pgd.resource.nativefmt == 'fa':
                self.algoassert(
                    pgd.container.basename == self.input_orog_name,
                    "Local name for resource Pgd must be '{}'".
                    format(self.input_orog_name))
            elif pgd.resource.nativefmt == 'lfi':
                raise NotImplementedError('CY43T2 onwards: lfi PGD should not be used.')


class FinalizePGD(AlgoComponent):
    """
    Finalise PGD file: report spectrally optimized orography from Clim to PGD,
    and add E-zone.
    """

    _footprint = dict(
        info = "Finalisation of PGD.",
        attr = dict(
            kind = dict(
                values   = ['finalize_pgd'],
            ),
            pgd_out_name = dict(
                optional = True,
                default = 'PGD_final.fa'
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super(FinalizePGD, self).__init__(*args, **kwargs)
        from common.util.usepygram import is_epygram_available
        ev = '1.2.14'
        self.algoassert(is_epygram_available(ev), "Epygram >= " + ev +
                        " is needed here")

    def execute(self, rh, opts):  # @UnusedVariable
        """Convert SURFGEOPOTENTIEL from clim to SFX.ZS in pgd."""
        import numpy
        from common.util.usepygram import epygram, epy_env_prepare
        from bronx.meteo.constants import g0
        # Handle resources
        clim = self.context.sequence.effective_inputs(role=('Clim',))
        self.algoassert(len(clim) == 1, "One and only one Clim has to be provided")
        pgdin = self.context.sequence.effective_inputs(role=('InputPGD',))
        self.algoassert(len(pgdin) == 1, "One and only one InputPGD has to be provided")
        if self.system.path.exists(self.pgd_out_name):
            raise IOError("The output pgd file %s already exists.",
                          self.pgd_out_name)
        # copy fields
        with epy_env_prepare(self.ticket):
            epyclim = clim[0].rh.contents.data
            epypgd = pgdin[0].rh.contents.data
            epyclim.open()
            epypgd.open()
            pgdout = epygram.formats.resource(self.pgd_out_name, 'w', fmt='FA',
                                              headername=epyclim.headername,
                                              geometry=epyclim.geometry,
                                              cdiden=epypgd.cdiden,
                                              validity=epypgd.validity,
                                              processtype=epypgd.processtype)
            g = epyclim.readfield('SURFGEOPOTENTIEL')
            g.operation('/', g0)
            g.fid['FA'] = 'SFX.ZS'
            for f in epypgd.listfields():
                fld = epypgd.readfield(f)
                if f == 'SFX.ZS':
                    fld = g
                elif (isinstance(fld, epygram.fields.H2DField) and
                      fld.geometry.grid.get('LAMzone') is not None):
                    ext_data = numpy.ma.masked_equal(numpy.zeros(g.data.shape), 0.)
                    ext_data[:fld.geometry.dimensions['Y'],
                             :fld.geometry.dimensions['X']] = fld.data[:, :]
                    fld = footprints.proxy.fields.almost_clone(fld, geometry=g.geometry)
                    fld.setdata(ext_data)
                pgdout.writefield(fld, compression=epypgd.fieldscompression.get(f, None))


class MakeLAMDomain(AlgoComponent):
    """
    Wrapper to call Epygram domain making functions and generate
    namelist deltas for geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['make_domain', 'make_lam_domain'],
            ),
            geometry = dict(
                info = "The horizontal geometry to be generated.",
                type = HorizontalGeometry,
            ),
            mode = dict(
                info = ("Kind of input for building geometry:" +
                        "'center_dims' to build domain given its centre and" +
                        "dimensions; 'lonlat_included' to build domain given" +
                        "an included lon/lat area."),
                values = ['center_dims', 'lonlat_included']
            ),
            geom_params = dict(
                info = ("Set of parameters and/or options to be passed to" +
                        "epygram.geometries.domain_making.build.build_geometry()" +
                        "or" +
                        "epygram.geometries.domain_making.build.build_geometry_fromlonlat()"),
                type = footprints.FPDict,
            ),
            truncation = dict(
                info = ("Type of spectral truncation, among" +
                        "('linear', 'quadratic', 'cubic')."),
                optional = True,
                default = 'linear',
            ),
            orography_truncation = dict(
                info = ("Type of truncation of orography, among" +
                        "('linear', 'quadratic', 'cubic')."),
                optional = True,
                default = 'quadratic',
            ),
            # plot
            illustration = dict(
                info = "Create the domain illustration image.",
                type = bool,
                optional = True,
                default = True
            ),
            illustration_fmt = dict(
                info = "The format of the domain illustration image.",
                values = ['png', 'pdf'],
                optional = True,
                default = 'png'
            ),
            plot_params = dict(
                info = "Plot geometry parameters.",
                type = footprints.FPDict,
                optional = True,
                default = footprints.FPDict({'gisquality': 'i',
                                             'bluemarble': 0.,
                                             'background': True})
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super(MakeLAMDomain, self).__init__(*args, **kwargs)
        from common.util.usepygram import is_epygram_available
        ev = '1.2.14'
        self.algoassert(is_epygram_available(ev), "Epygram >= " + ev +
                        " is needed here")
        self._check_geometry()
        self.plot_params['bluemarble'] = 0.  # FIXME:? JPEG decoder not available on beaufix

    def _check_geometry(self):
        if self.mode == 'center_dims':
            params = ['center_lon', 'center_lat', 'Xpoints_CI', 'Ypoints_CI',
                      'resolution']
            params_extended = params + ['tilting', 'Iwidth', 'force_projection', 'maximize_CI_in_E']
        elif self.mode == 'lonlat_included':
            params = ['lonmin', 'lonmax', 'latmin', 'latmax',
                      'resolution']
            params_extended = params + ['Iwidth', 'force_projection', 'maximize_CI_in_E']
        self.algoassert(set(params).issubset(set(self.geom_params.keys())),
                        "With mode=={!s}, geom_params must contain at least {!s}".
                        format(self.mode, params))
        self.algoassert(set(self.geom_params.keys()).issubset(set(params_extended)),
                        "With mode=={!s}, geom_params must contain at most {!s}".
                        format(self.mode, params))

    def execute(self, rh, opts):  # @UnusedVariable
        from common.util.usepygram import epygram
        dm = epygram.geometries.domain_making
        if self.mode == 'center_dims':
            build_func = dm.build.build_geometry
            lonlat_included = None
        elif self.mode == 'lonlat_included':
            build_func = dm.build.build_geometry_fromlonlat
            lonlat_included = self.geom_params
        # build geometry
        geometry = build_func(interactive=False, **self.geom_params)
        # summary, plot, namelists:
        with open(self.geometry.tag + '_summary.txt', 'w') as o:
            o.write(dm.output.summary(geometry))
        if self.illustration:
            dm.output.plot_geometry(geometry,
                                    lonlat_included=lonlat_included,
                                    out='.'.join([self.geometry.tag,
                                                  self.illustration_fmt]),
                                    **self.plot_params)
        namelists = dm.output.lam_geom2namelists(geometry,
                                                 truncation=self.truncation,
                                                 orography_subtruncation=self.orography_truncation)
        dm.output.write_namelists(namelists, prefix=self.geometry.tag)


class MakeGaussGeometry(Parallel):
    """
    Wrapper to call Gauss geometry making RGRID and generate
    namelist deltas for geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['make_gauss_grid'],
            ),
            geometry = dict(
                info = "The vortex horizontal geometry to be generated.",
                type = HorizontalGeometry,
            ),
            truncation = dict(
                info = 'nominal truncation',
                type = int,
            ),
            grid = dict(
                info = 'type of grid with regards to truncation, among (linear, quadratic, cubic)',
                optional = True,
                default = 'linear'
            ),
            orography_grid = dict(
                info = 'orography subtruncation (linear, quadratic, cubic)',
                optional = True,
                default = 'quadratic'
            ),
            stretching = dict(
                info = 'stretching factor',
                type = float,
                optional = True,
                default = 1.,
            ),
            pole = dict(
                info = 'pole of stretching (lon, lat), angles in degrees',
                type = footprints.FPDict,
                optional = True,
                default = {'lon': 0., 'lat': 90.}
            ),
            # RGRID commandline options
            latitudes = dict(
                info = 'number of Gaussian latitudes',
                type = int,
                optional = True,
                default = None
            ),
            longitudes = dict(
                info = 'maximum (equatorial) number of longitudes',
                type = int,
                optional = True,
                default = None
            ),
            orthogonality = dict(
                info = 'orthogonality precision, as Log10() value',
                type = int,
                optional = True,
                default = None
            ),
            aliasing = dict(
                info = 'allowed aliasing, as a Log10() value',
                type = int,
                optional = True,
                default = None
            ),
            oddity = dict(
                info = 'odd numbers allowed (1) or not (0)',
                type = int,
                optional = True,
                default = None
            ),
            verbosity = dict(
                info = 'verbosity (0 or 1)',
                type = int,
                optional = True,
                default = None
            ),
            # plot
            illustration = dict(
                info = "Create the domain illustration image.",
                type = bool,
                optional = True,
                default = True
            ),
            illustration_fmt = dict(
                info = "The format of the domain illustration image.",
                values = ['png', 'pdf'],
                optional = True,
                default = 'png'
            ),
            plot_params = dict(
                info = "Plot geometry parameters.",
                type = footprints.FPDict,
                optional = True,
                default = footprints.FPDict({'gisquality': 'i',
                                             'bluemarble': 0.,
                                             'background': True})
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super(MakeGaussGeometry, self).__init__(*args, **kwargs)
        from common.util.usepygram import is_epygram_available
        ev = '1.2.14'
        self.algoassert(is_epygram_available(ev), "Epygram >= " + ev +
                        " is needed here")
        self._complete_dimensions()
        self._unit = 4
        self.plot_params['bluemarble'] = 0.  # FIXME:? JPEG decoder not available on beaufix

    def _complete_dimensions(self):
        # from common.util.usepygram import epygram
        from epygram.geometries.SpectralGeometry import gridpoint_dims_from_truncation
        if self.latitudes is None and self.longitudes is None:
            dims = gridpoint_dims_from_truncation({'max': self.truncation},
                                                  grid=self.grid)
            self._attributes['latitudes'] = dims['lat_number']
            self._attributes['longitudes'] = dims['max_lon_number']
        elif self.longitudes is None:
            self._attributes['longitudes'] = 2 * self.latitudes
        elif self.latitudes is None:
            if self.longitudes % 4 != 0:
                self._attributes['latitudes'] = self.longitudes // 2 + 1
            else:
                self._attributes['latitudes'] = self.longitudes // 2

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        options = {'t': six.text_type(self.truncation),
                   'g': six.text_type(self.latitudes),
                   'l': six.text_type(self.longitudes),
                   'f': six.text_type(self._unit)}
        options_dict = {'orthogonality': 'o',
                        'aliasing': 'a',
                        'oddity': 'n',
                        'verbosity': 'v'}
        for k in options_dict.keys():
            if getattr(self, k) is not None:
                options[options_dict[k]] = six.text_type(getattr(self, k))
        return options

    def postfix(self, rh, opts):
        """Complete and write namelists."""
        import math
        from epygram.geometries.SpectralGeometry import truncation_from_gridpoint_dims
        # complete scalar parameters
        nam = namelist.NamelistSet()
        nam.add(namelist.NamelistBlock('NAM_PGD_GRID'))
        nam.add(namelist.NamelistBlock('NAMDIM'))
        nam.add(namelist.NamelistBlock('NAMGEM'))
        nam['NAM_PGD_GRID']['CGRID'] = 'GAUSS'
        nam['NAMDIM']['NDGLG'] = self.latitudes
        nam['NAMDIM']['NDLON'] = self.longitudes
        nam['NAMDIM']['NSMAX'] = self.truncation
        nam['NAMGEM']['NHTYP'] = 2
        nam['NAMGEM']['NSTTYP'] = 2 if self.pole != {'lon': 0., 'lat': 90.} else 1
        nam['NAMGEM']['RMUCEN'] = math.sin(math.radians(float(self.pole['lat'])))
        nam['NAMGEM']['RLOCEN'] = math.radians(float(self.pole['lon']))
        nam['NAMGEM']['RSTRET'] = self.stretching
        # numbers of longitudes
        with io.open('fort.{!s}'.format(self._unit), 'r') as n:
            namrgri = namelist.namparse(n)
            nam.merge(namrgri)
        # PGD namelist
        nam_pgd = copy.deepcopy(nam)
        nam_pgd['NAMGEM'].delvar('NHTYP')
        nam_pgd['NAMGEM'].delvar('NSTTYP')
        nam_pgd['NAMDIM'].delvar('NSMAX')
        nam_pgd['NAMDIM'].delvar('NDLON')
        with open('.'.join([self.geometry.tag,
                            'namel_buildpgd',
                            'geoblocks']),
                  'w') as out:
            out.write(nam_pgd.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        # C923 namelist
        del nam['NAM_PGD_GRID']
        with open('.'.join([self.geometry.tag,
                            'namel_c923',
                            'geoblocks']),
                  'w') as out:
            out.write(nam.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        # subtruncated grid for orography
        trunc_nsmax = truncation_from_gridpoint_dims({'lat_number': self.latitudes,
                                                      'max_lon_number': self.longitudes},
                                                     grid=self.orography_grid)['max']
        nam['NAMDIM']['NSMAX'] = trunc_nsmax
        with open('.'.join([self.geometry.tag,
                            'namel_c923_orography',
                            'geoblocks']),
                  'w') as out:
            out.write(nam.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        # C927 (fullpos) namelist
        nam = namelist.NamelistSet()
        nam.add(namelist.NamelistBlock('NAMFPD'))
        nam.add(namelist.NamelistBlock('NAMFPG'))
        nam['NAMFPD']['NLAT'] = self.latitudes
        nam['NAMFPD']['NLON'] = self.longitudes
        nam['NAMFPG']['NFPMAX'] = self.truncation
        nam['NAMFPG']['NFPHTYP'] = 2
        nam['NAMFPG']['NFPTTYP'] = 2 if self.pole != {'lon': 0., 'lat': 90.} else 1
        nam['NAMFPG']['FPMUCEN'] = math.sin(math.radians(float(self.pole['lat'])))
        nam['NAMFPG']['FPLOCEN'] = math.radians(float(self.pole['lon']))
        nam['NAMFPG']['FPSTRET'] = self.stretching
        nrgri = [v for _, v in sorted(namrgri['NAMRGRI'].items())]
        for i in range(len(nrgri)):
            nam['NAMFPG']['NFPRGRI({:>4})'.format(i + 1)] = nrgri[i]
        with open('.'.join([self.geometry.tag,
                            'namel_c927',
                            'geoblocks']),
                  'w') as out:
            out.write(nam.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        super(MakeGaussGeometry, self).postfix(rh, opts)


class MakeBDAPDomain(AlgoComponent):
    """
    Wrapper to call Epygram domain making functions and generate
    namelist deltas for BDAP (lonlat) geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['make_domain', 'make_bdap_domain'],
            ),
            geometry = dict(
                info = "The horizontal geometry to be generated.",
                type = HorizontalGeometry,
            ),
            mode = dict(
                info = ("Kind of input for building geometry:" +
                        "'boundaries' to build domain given its lon/lat boundaries" +
                        "(+ resolution); 'inside_model' to build domain given" +
                        "a model geometry to be included in (+ resolution)."),
                values = ['boundaries', 'inside_model']
            ),
            resolution = dict(
                info = "Resolution in degrees.",
                type = float,
            ),
            boundaries = dict(
                info = "Lonlat boundaries of the domain, case mode='boundaries'.",
                type = footprints.FPDict,
                optional = True,
                default = None,
            ),
            model_clim = dict(
                info = "Filename of the model clim, case mode='inside_model'.",
                optional = True,
                default = None,
            ),
            # plot
            illustration = dict(
                info = "Create the domain illustration image.",
                type = bool,
                optional = True,
                default = True
            ),
            illustration_fmt = dict(
                info = "The format of the domain illustration image.",
                values = ['png', 'pdf'],
                optional = True,
                default = 'png'
            ),
            plot_params = dict(
                info = "Plot geometry parameters.",
                type = footprints.FPDict,
                optional = True,
                default = footprints.FPDict({'gisquality': 'i',
                                             'bluemarble': 0.,
                                             'background': True})
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super(MakeBDAPDomain, self).__init__(*args, **kwargs)
        from common.util.usepygram import is_epygram_available
        ev = '1.2.14'
        self.algoassert(is_epygram_available(ev), "Epygram >= " + ev +
                        " is needed here")
        if self.mode == 'boundaries':
            params = ['lonmin', 'lonmax', 'latmin', 'latmax']
            self.algoassert(set(params) == set(self.boundaries.keys()),
                            "With mode=={}, boundaries must contain at least {}".
                            format(self.mode, str(params)))
            if self.model_clim is not None:
                logger.info('attribute *model_clim* ignored')
        elif self.mode == 'inside_model':
            self.algoassert(self.model_clim is not None,
                            "attribute *model_clim* must be provided with " +
                            "mode=='inside_model'.")
            self.algoassert(self.sh.path.exists(self.model_clim))
            if self.boundaries is not None:
                logger.info('attribute *boundaries* ignored')
        self.plot_params['bluemarble'] = 0.  # FIXME:? JPEG decoder not available on beaufix

    def execute(self, rh, opts):  # @UnusedVariable
        from common.util.usepygram import epygram
        dm = epygram.geometries.domain_making
        if self.mode == 'inside_model':
            r = epygram.formats.resource(self.model_clim, 'r')
            if r.format == 'FA':
                g = r.readfield('SURFGEOPOTENTIEL')
            else:
                raise NotImplementedError()
            boundaries = dm.build.compute_lonlat_included(g.geometry)
        else:
            boundaries = self.boundaries
        # build geometry
        geometry = dm.build.build_lonlat_geometry(boundaries,
                                                  resolution=self.resolution)
        # summary, plot, namelists:
        if self.illustration:
            fig, _ = geometry.plotgeometry(color='red',
                                           title=self.geometry.tag,
                                           **self.plot_params)
            fig.savefig('.'.join([self.geometry.tag,
                                  self.illustration_fmt]),
                        bbox_inches='tight')
        namelists = dm.output.regll_geom2namelists(geometry)
        dm.output.write_namelists(namelists, prefix=self.geometry.tag)
        self.system.symlink('.'.join([self.geometry.tag,
                                      'namel_c923',
                                      'geoblocks']),
                            '.'.join([self.geometry.tag,
                                      'namel_c923_orography',
                                      'geoblocks']))
