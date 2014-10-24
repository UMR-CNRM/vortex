#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.resources import Resource
from mercator.syntax.stdattrs import grids, experiences, bogus, model, atmofields, atmoForcingOrigin
from vortex.syntax.stdattrs import term
from vortex.tools.date import Date


class Namelist(Resource):
    _footprint = dict(
        info = 'Ocean and assim Namelists',
        attr = dict(
            nmtype = dict(
                optional = True,
                values = [ 'main', 'ice', 'io' ],
                default = 'main',
            ),
            cexper = dict(
                values = experiences,
            ),
            kind = dict(
                values = [ 'namelist' ]
            ),
            grid = dict(
                values = grids,
            ),
        ),
    )

    def mercator_basename(self):
        if self.cexper in experiences:
            if self.nmtype == 'main':
                return 'namelist'
            if self.nmtype == 'ice':
                return 'namelist_ice'
            if self.nmtype == 'io':
                return 'namelistio'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'paraminput/ocean/ana/',
        )


class NamelistAssimilation(Namelist):
    _footprint = dict(
        info = 'namelist for assimilation',
        attr = dict(
            assim = dict(
                optional = False,
                type = bool,
                values = [ True, False ],
            ),
            nmtype = dict(
                optional = False,
                values = [ 'kernel', 'palm' ],
            ),
            grid = dict(
                values = grids,
            ),
        ),
    )

    def mercator_basename(self):
        if self.assim:
            if self.nmtype == 'kernel':
                return 'kernel.prm'
            elif self.nmtype == 'palm':
                return 'palm.prm'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'paraminput/assim/ana/',
        )


class NamelistBogus(NamelistAssimilation):
    _footprint = dict(
        info = 'bogus namelist',
        attr = dict(
            nmtype = dict(
                optional = False,
                values = [ 'hbr', 'hbrst', 'gradhbr', 'hunderice', 'runoff', 'tsuvontrop', 'tsuvunderice' ],
            ),
            grid = dict(
                values = grids,
            ),
        ),
    )

    def mercator_basename(self):
        if self.nmtype == 'hbr':
            return 'DS_BOGUS_HBR.list'
        elif self.nmtype == 'hbrst':
            return 'DS_BOGUS_HBRST.list'
        elif self.nmtype == 'gradhbr':
            return 'DS_BOGUS_gradHBR.list'
        elif self.nmtype == 'hunderice':
            return 'IS_BOGUS_HunderICE.list'
        elif self.nmtype == 'runoff':
            return 'VP_BOGUS_RUNOFF.list'
        elif self.nmtype == 'tsuvontrop':
            return 'VP_BOGUS_TSUVonTROP.list'
        elif self.nmtype == 'tsuvunderice':
            return 'VP_BOGUS_TSUVunderICE.list'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'paraminput/assim/ana/',
        )


class Bogus(Resource):
    _footprint = dict(
        info = 'bogus files',
        attr = dict(
            bogustype = dict(
                values = bogus
            ),
        ),
    )


class Bathymetry(Resource):
    _footprint = dict(
        info = 'bathymetry',
        attr = dict(
            grid = dict(
                values = grids,
            ),
            cexper = dict(
                values = experiences,
            ),
            assim = dict(
                type = bool,
                optional = True,
                default = False,
            ),
            kind = dict(
                values = [ 'bathymetry' ]
            )
        ),
    )

    def mercator_basename(self):
        if self.assim:
            return 'bathy3D.cmz'
        else:
            # guess this one:
            if self.grid == 'orca025':
                return self.grid.upper()+'_bathy_etopo1_gebco1_smoothed_coast_corrected_sept09.nc'

    def mercator_pathinfo(self):
        assim_ocean = 'ocean'
        if self.assim:
            assim_ocean = 'assim'

        return dict(
            grid = self.grid,
            path = 'staticinput/'+assim_ocean+'/',
        )


class Runoff(Resource):
    _footprint = dict(
        info = 'climatology runoff',
        attr = dict(
            grid = dict(
                values = grids,
            ),
            cexper = dict(
                values = experiences,
            ),
            kind = dict(
              values = [ 'runoff' ]
            )
        ),
    )

    def mercator_basename(self):
        if self.grid == 'orca025':
            return 'runoff_obtaz_rhone_antar_1m_bathy_sept09_'+self.grid.upper()+'_10112009.nc'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'staticinput/ocean',
        )


class Moorings(Resource):
    _footprint = [
        model,
        dict(
            info = 'moorings',
            attr = dict(
                kind = dict(
                    values = [ 'moorings', ]
                ),
                grid = dict(
                    values = grids,
                ),
                type = dict(
                    values = [ 'moor', 'sect' ],
                    optional = False,
                ),
            ),
        )
    ]

    def mercator_basename(self):
        return 'position.'+self.type+'.'+self.model

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'staticinput/ocean',
        )


class MooringsPosition(Resource):
    _footprint = [
        term,
        dict(
            info = 'moorings',
            attr = dict(
                kind = dict(
                    values = [ 'moorings', ]
                ),
                grid = dict(
                    values = grids,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'moorings'

    def mercator_basename(self):
        if self.grid == 'orca025':
            return 'position_ijproc.moor_bin_' + self.term.fmthour

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'staticinput/ocean',
        )


class Coordinates(Resource):
    _footprint = dict(
        info = 'coordinates',
        attr = dict(
            grid = dict(
                values = grids,
            ),
            kind = dict(
                values = [ 'coordinates' ]
            )
        ),
    )

    def mercator_basename(self):
        return 'coordinates_'+self.grid.upper()+'_LIM.nc'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'staticinput/ocean',
        )


class ModelBinaries(Resource):
    _footprint = [
        term,
        dict(
            info = 'model binaries',
            attr = dict(
                grid = dict(
                    optional = True,
                    values = grids,
                ),
                assim = dict(
                    optional = False,
                    type = bool,
                ),
                type = dict(
                    optional = False,
                    values = [ 'main', 'block', 'pil', 'build_nc', 'anolist' ]
                ),
                kind = dict(
                    values = [ 'binary' ]
                )
            ),
        )
    ]

    @property
    def realkind(self):
        return 'binary'

    def mercator_basename(self):
        if self.type == 'main':
            if self.assim:
                return 'palm_main'
            else:
                return 'opa'
        elif self.type == 'block':
            return 'main_block_' + self.term.fmthour
        elif self.type == 'pil':
            return 'SAMIAU_PALM_MULTIMP.pil'
        elif self.type == 'build_nc':
            return self.type+'_mpp'
        elif self.type == 'anolist':
            return 'createlisttxtbylib.x'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'config/exe/',
        )


class ClimatologyLevitus(Resource):
    _footprint = dict(
        info = 'Levitus Climatology',
        attr = dict(
            kind = dict(
                values = [ 'climatology', ]
            ),
            field = dict(
                optional = False,
                values = [ 'Tem', 'Sal' ],
            ),
            year = dict(
                optional = True,
                values = [ '98', '05' ],
                default = '05',
            ),
            month = dict(
                optional = True,
                values = [ '{0:02d}'.format(x) for x in range(1, 13) ],
                default = None,
            ),
            grid = dict(
                optional = True,
                values = grids,
                default = 'orca025'
            ),
        ),
    )

    @property
    def realkind(self):
        return 'climatology'

    def mercator_basename(self):
        return 'Levitus'+self.year+'_'+self.field+'_'+self.grid.upper()+'m'+self.month+'.nc'

    def mercator_pathinfo(self):
        return dict(
            grid = self.grid,
            path = 'staticinput/monthly_climato'
        )


class AtmosphericForcing(Resource):
    _footprint = dict(
        info = 'Atmospheric forcings',
        attr = dict(
            kind = dict(
                values = 'atmforcing'
            ),
            grid = dict(
                optional = False,
                values = grids,
            ),
            field = dict(
                optional = False,
                values = atmofields,
            ),
            origin = dict(
                optional = True,
                values = atmoForcingOrigin,
                default = 'ECMWF',
            ),
            timecoverage = dict(
                optional = True,
                values = [ 'daily', 'weekly' ],
                default = 'daily',
            ),
            start_date = dict(
                optional = False,
                type = Date,
            ),
            end_date = dict(
                optional = False,
                type = Date,
            )
        )
    )

    def mercator_basename(self):
        return '_'.join( [
            self.origin,
            self.field,
            self.grid.upper(),
            str(self.start_date.to_cnesjulian()),
            str(self.end_date.to_cnesjulian()),
        ])

# vim: set ts=4 sw=4 expandtab et:
