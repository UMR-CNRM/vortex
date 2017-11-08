#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common AlgoComponnent to build model's climatology files.
"""

from __future__ import print_function, absolute_import, division

import decimal

import footprints

from vortex.algo.components import BlindRun, AlgoComponent
from vortex.data.geometries import HorizontalGeometry
from common.algo.ifsroot import IFSParallel

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
                type = str,
                optional = True,
                default = 'Neworog',
            ),
            xpname = dict(
                default = 'CLIM',
            ),
        )
    )

    def _convert_pgdlfi2pgdfa923(self, *args, **kwargs):
        """
        Convert fields from a PGD.lfi to ad-hoc-well-formatted-for-clim923 FA
        format.

        Refer to :function:`common.util.usepygram.mk_pgdfa923_from_pgdlfi`
        for args and kwargs, ticket session excepted.
        """
        from common.util.usepygram import mk_pgdfa923_from_pgdlfi
        mk_pgdfa923_from_pgdlfi(self.ticket, *args, **kwargs)

    def prepare(self, rh, opts):
        """Prepare PGD to be readable."""
        super(C923, self).prepare(rh, opts)
        # Namelist
        nam = self.context.sequence.effective_inputs(role=('Namelist',))
        self.algoassert(len(nam) == 1,
                        "One and only one namelist necessary as input.")
        nam = nam[0].rh
        nam.contents['NAMMCC']['N923'] = self.step
        nam.contents.setmacro('LIPGD', self.orog_in_pgd)
        nam.save()
        # get geometry for lfi->fa923
        geom_delta = self.context.sequence.effective_inputs(role=('GeometryDefinition',))
        self.algoassert(len(geom_delta) == 1,
                        "One and only one namelist necessary as input.")
        geom_delta = geom_delta[0].rh
        nam923blocks = geom_delta.contents.data
        # Note: conversion to float because may be Decimal
        for b in nam923blocks.values():
            for k in b.keys():
                if isinstance(b[k], decimal.Decimal):
                    b[k] = float(b[k])
        # convert pgd
        pgd = self.context.sequence.effective_inputs(role=('Pgd',))
        if len(pgd) == 0:
            self.algoassert(
                not self.orog_in_pgd,
                "As long as 'orog_in_pgd' attribute of this algo component is " +
                "True, a 'Role: Pgd' resource must be provided.")
        else:
            pgd = pgd[0].rh
            if pgd.resource.nativefmt == 'lfi':
                self.algoassert(
                    pgd.container.basename != self.input_orog_name,
                    "Local name for resource Pgd mustn't be '{}' if format is lfi.".
                    format(self.input_orog_name))
                logger.info("Convert PGD from LFI to FA923")
                self._convert_pgdlfi2pgdfa923(pgd,
                                              nam923blocks,
                                              outname=self.input_orog_name)


class FinalizePGD(AlgoComponent):
    """
    Finalise PGD file: report spectrally filtered orography from Clim to PGD,
    and convert it to FA if necessary.
    """

    _footprint = dict(
        info = "Finalisation of PGD.",
        attr = dict(
            kind = dict(
                values   = ['finalize_pgd'],
            ),
            pgd_out_name = dict(
                type = str,
                optional = True,
                default = 'PGD_final.fa'
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(FinalizePGD, self).__init__(*kargs, **kwargs)
        self._addon_checked = None

    def _check_addons(self):
        if self._addon_checked is None:
            self._addon_checked = 'sfx' in self.system.loaded_addons()
        if not self._addon_checked:
            raise RuntimeError("The sfx addon is needed... please load it.")

    def prepare(self, rh, opts):
        """Default pre-link for namelist file and domain change."""
        super(FinalizePGD, self).prepare(rh, opts)
        from common.util.usepygram import empty_fa
        # Handle resources
        clim = self.context.sequence.effective_inputs(role=('Clim',))
        self.algoassert(len(clim) == 1, "One and only one Clim has to be provided")
        pgdin = self.context.sequence.effective_inputs(role=('InputPGD',))
        self.algoassert(len(pgdin) == 1, "One and only one InputPGD has to be provided")
        if self.system.path.exists(self.pgd_out_name):
            raise IOError("The output pgd file %s already exists.",
                          self.pgd_out_name)
        # prepare PGDin if necessary
        if pgdin[0].rh.resource.nativefmt == 'lfi':
            # PGD need conversion
            logger.info("Create empty target fa file: %s.",
                        self.pgd_out_name)
            # Create empty FA...
            self._pgd_fa = empty_fa(self.ticket, clim[0].rh, self.pgd_out_name)
            # Convert PGD.lfi to PGD.fa...
            logger.info("Calling sfxtools' lfi2fa from %s to %s.",
                        pgdin[0].rh.container.localpath(),
                        self.pgd_out_name)
            self.system.sfx_lfi2fa(pgdin[0].rh.container.localpath(), self.pgd_out_name)
        elif pgdin[0].rh.resource.nativefmt == 'fa':
            # Format Adapter: epygram
            self._pgd_fa = pgdin[0].rh.contents.data
        else:
            raise IOError("File %s nativefmt must be 'fa' or 'lfi'.")

    def execute(self, rh, opts):
        """Convert SURFGEOPOTENTIEL from clim to SFX.ZS in pgd."""
        from common.util.usepygram import epy_env_prepare
        clim = self.context.sequence.effective_inputs(role=('Clim',))
        with epy_env_prepare(self.ticket):
            self._pgd_fa.open(openmode='a')
            zs_name = 'SFX.ZS'
            self._pgd_fa.readfield(zs_name, getdata=False)  # to know how it is encoded
            zs = clim[0].rh.contents.data.readfield('SURFGEOPOTENTIEL')
            zs.operation('/', 9.80665)
            zs.fid['FA'] = zs_name
            self._pgd_fa.writefield(zs, compression=self._pgd_fa.fieldscompression[zs.fid['FA']])
            self._pgd_fa.close()


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
            mode = dict(
                info = ("Kind of input for building geometry:" +
                        "'center_dims' to build domain given its centre and" +
                        "dimensions; 'lonlat_included' to build domain given" +
                        "an included lon/lat area."),
                values = ['center_dims', 'lonlat_included']
            ),
            geom_params = dict(
                info = ("Set of parameters and/or options to be passed to" +
                        "epygram.geometries.domain_making.build_geometry()" +
                        "or" +
                        "epygram.geometries.domain_making.build_geometry_fromlonlat()"),
                type = footprints.FPDict,
            ),
            orography_truncation = dict(
                info = ("Type of truncation of orography, among" +
                        "('linear', 'quadratic', 'cubic')."),
                type = str,
                optional = True,
                default = 'quadratic',
            ),
            plot_params = dict(
                info = "Plot geometry parameters.",
                type = footprints.FPDict,
                optional = True,
                default = footprints.FPDict({'gisquality': 'i',
                                             'bluemarble': 0.,
                                             'background': True})
            ),
            geometry = dict(
                info = "The horizontal geometry to be generated.",
                type = HorizontalGeometry,
            ),
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
        )
    )

    def __init__(self, *args, **kwargs):
        super(MakeLAMDomain, self).__init__(*args, **kwargs)
        from common.util.usepygram import is_epygram_available
        self.algoassert(is_epygram_available('1.2.10'), "Epygram >= 1.2.10 is needed here")
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
                        "With mode=={}, geom_params must contain at least {}".
                        format(self.mode, str(params)))
        self.algoassert(set(self.geom_params.keys()).issubset(set(params_extended)),
                        "With mode=={}, geom_params must contain at most {}".
                        format(self.mode, str(params)))

    def execute(self, rh, opts):
        from common.util.usepygram import epygram
        domain_making = epygram.geometries.domain_making
        if self.mode == 'center_dims':
            build_func = domain_making.build_geometry
            lonlat_included = None
        elif self.mode == 'lonlat_included':
            build_func = domain_making.build_geometry_fromlonlat
            lonlat_included = self.geom_params
        # build geometry
        geometry = build_func(interactive=False, **self.geom_params)
        # summary, plot, namelists:
        with open(self.geometry.tag + '_summary.txt', 'w') as o:
            o.write(domain_making.show_geometry(geometry))
        if self.illustration:
            domain_making.plot_geometry(geometry,
                                        lonlat_included=lonlat_included,
                                        out='.'.join([self.geometry.tag,
                                                      self.illustration_fmt]),
                                        **self.plot_params)
        namblocks = domain_making.geom2namblocks(geometry,
                                                 truncated=self.orography_truncation)
        domain_making.format_namelists(namblocks, prefix=self.geometry.tag)


class MakeGaussGeometry(AlgoComponent):
    """
    Wrapper to call Epygram Gauss geometry making functions and generate
    namelist deltas for geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['make_gauss_grid'],
            ),
        )
    )
