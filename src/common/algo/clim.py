#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

#: No automatic export
__all__ = []

import decimal

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import BlindRun, AlgoComponent
from vortex.data.geometries import HorizontalGeometry
from common.algo.ifsroot import IFSParallel


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
        assert len(nam) == 1, "One and only one namelist necessary as input."
        nam = nam[0].rh
        nam.contents['NAMMCC']['N923'] = self.step
        nam.contents.setmacro('LIPGD', self.orog_in_pgd)
        nam.save()
        # get geometry for lfi->fa923
        geom_delta = self.context.sequence.effective_inputs(role=('GeometryDefinition',))
        assert len(geom_delta) == 1, "One and only one namelist necessary as input."
        geom_delta = geom_delta[0].rh
        nam923blocks = geom_delta.contents.data
        # Note: conversion to float because may be Decimal
        for b in nam923blocks.values():
            print(b)
            for k in b.keys():
                print(k)
                if isinstance(b[k], decimal.Decimal):
                    b[k] = float(b[k])
        # convert pgd
        pgd = self.context.sequence.effective_inputs(role=('Pgd',))
        if len(pgd) == 0:
            assert not self.orog_in_pgd, \
                """As long as 'orog_in_pgd' attribute of this algo component is
                True, a 'Role: Pgd' resource must be provided."""
        else:
            pgd = pgd[0].rh
            if pgd.resource.nativefmt == 'lfi':
                assert pgd.container.basename != self.input_orog_name, \
                    "Local name for resource Pgd mustn't be '{}' if format is lfi.".format(self.input_orog_name)
                print("Convert PGD from LFI to FA923")
                self._convert_pgdlfi2pgdfa923(pgd,
                                              nam923blocks,
                                              outname=self.input_orog_name)


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
                        "'center_dims' to build domain given its center and" +
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
            plot_params = dict(
                info = "Plot geometry parameters.",
                type = footprints.FPDict,
                optional = True,
                default = footprints.FPDict({'gisquality':'i',
                                             'bluemarble':0.,
                                             'background':True})
            ),
            geometry = dict(
                info = "The horizontal geometry to be generated.",
                type = HorizontalGeometry,
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
        assert is_epygram_available('1.2.10')
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
        assert set(params).issubset(set(self.geom_params.keys())), \
            "With mode=={}, geom_params must contain at least {}".format(self.mode, str(params))
        assert set(self.geom_params.keys()).issubset(set(params_extended)), \
            "With mode=={}, geom_params must contain at most {}".format(self.mode, str(params))

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
        domain_making.plot_geometry(geometry,
                                    lonlat_included=lonlat_included,
                                    out='.'.join([self.geometry.tag,
                                                  self.illustration_fmt]),
                                    **self.plot_params)
        namblocks = domain_making.geom2namblocks(geometry)
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
