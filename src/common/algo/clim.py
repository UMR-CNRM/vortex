#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

import json

from vortex.algo.components import BlindRun, AlgoComponent
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
            ),
            input_orog_name = dict(
                info = "Filename for input orography file (case LNORO=.T.).",
                type = str,
                optional = True,
                default = 'Neworo',
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
        mk_pgdfa923_from_pgdlfi(self.session, *args, **kwargs)

    def prepare(self, rh, opts):
        """DrHook stuff."""
        super(BuildPGD, self).prepare(rh, opts)
        nam = self.context.sequence.effective_inputs(role=('Namelist',))[0]
        nam.contents.merge({'NAMMCC':{'N923':self.step}})
        nam.contents.setmacro('__LIPGD__', self.orography_in_pgd)

        geom_delta = self.context.sequence.effective_inputs(role=('Geometry Definition',))[0]
        nam923blocks = geom_delta.contents.data
        print(nam923blocks)

        pgd = self.context.sequence.effective_inputs(role=('Pgd',))
        if len(pgd) == 0:
            assert not self.orog_in_pgd, \
                """As long as 'orog_in_pgd' attribute of this algo component is
                True, a 'Role: Pgd' resource must be provided."""
        else:
            if pgd[0].format == 'lfi':
                assert pgd[0].container.basename != self.input_orog_name, \
                    "Local name for resource Pgd mustn't be 'Neworo' if format is lfi."
                self._convert_pgdlfi2pgdfa923(pgd[0],
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
                info = """Kind of input for building geometry:
                       'center_dims' to build domain given its center and
                       dimensions; 'lonlat_included' to build domain given
                       an included lon/lat area.""",
                values = ['center_dims', 'lonlat_included']
            ),
            #input_params = dict(
            #    info = """Set of parameters and/or options to be passed to
            #           epygram.geometries.domain_making.build_geometry()
            #           or
            #           epygram.geometries.domain_making.build_geometry_fromlonlat()""",
            #    type = str,  # FIXME: JSON workaround
            #    # type = footprints.FPDict,
            #),
        )
    )

    def _get_geometry(self):
        if self.mode == 'center_dims':
            params = ['center_lon', 'center_lat', 'Xpoints_CI', 'Ypoints_CI',
                      'resolution']
        elif self.mode == 'lonlat_included':
            params = ['lonmin', 'lonmax', 'latmin', 'latmax',
                      'resolution']
        # assert set(params).issubset(set(self.input_params.keys())), \
        # FIXME: JSON workaround
        #input_params = json.loads(self.input_params)
        #assert set(params).issubset(set(input_params.keys())), \
        #    "With mode=={}, input_params must contain at least {}".format(self.mode, str(params))
        self.input_params = {k:float(self.env.get(k.upper())) for k in params}
        self.geometryname = self.env.GEOMETRY

    def _get_plot_kwargs(self):
        """Get plot options through environment variables."""
        plot_kwargs = {}
        dm = 'DOMAIN_MAKER_'
        for k in ('gisquality', 'bluemarble', 'background'):
            if self.env.get(dm + k.upper()):
                plot_kwargs[k] = self.env.get(dm + k.upper())
        return plot_kwargs

    def execute(self, rh, opts):
        from common.util.usepygram import (epygram, is_epygram_available)
        domain_making = epygram.geometries.domain_making
        assert is_epygram_available('1.2.10')
        self._get_geometry()
        params = self.input_params.copy()
        params['interactive'] = False  # force it because an algo cannot be interactive
        if self.mode == 'center_dims':
            build_func = domain_making.build_geometry
            lonlat_included = None
        elif self.mode == 'lonlat_included':
            build_func = domain_making.build_geometry_fromlonlat
            lonlat_included = self.input_params
        # build geometry
        geometry = build_func(**params)
        # summary, plot, namelists:
        with open(self.geometryname + '_summary.txt', 'w') as o:
            o.write(domain_making.show_geometry(geometry))
        domain_making.plot_geometry(geometry,
                                    lonlat_included=lonlat_included,
                                    out='.'.join([self.geometryname, 'png']),
                                    **self._get_plot_kwargs())
        namblocks = domain_making.geom2namblocks(geometry)
        domain_making.format_namelists(namblocks, prefix=self.geometryname)


class MakeGaussGeometry(AlgoComponent):
    """
    Wrapper to call Epygram Gauss geometry making functions and generate
    namelist deltas for geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'make_gauss_grid' ],
            ),
        )
    )
