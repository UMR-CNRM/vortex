"""
TODO: Module documentation
"""

from vortex.syntax.stdattrs import month_deco
from common.data.consts import GenvModelResource
from common.data.climfiles import GenericClim
from vortex.data.geometries import LonlatGeometry
from gco.syntax.stdattrs import gdomain


#: No automatic export
__all__ = []


class ChemicalBackup(GenvModelResource):
    """Pseudo-climatological file for chemical boundary conditions.

    Backup values for missing values.
    """
    _footprint = dict(
        info = 'Climatological backup for chemical boundary conditions',
        attr = dict(
            kind = dict(
                values   = ['chemical_bkup'],
            ),
            gvar = dict(
                default  = 'cams_bc_backup'
            ),
            nativefmt = dict(
                optional = True,
                default  = 'netcdf',
            )
        )
    )

    @property
    def realkind(self):
        return 'chemical_bkup'


class MonthClimMisc(GenericClim):
    """Monthly miscellaneous climatological files."""

    _footprint = [
        month_deco,
        dict(
            info = 'Monthly climatological files',
            attr = dict(
                kind = dict(
                    values  = ['clim_misc'],
                ),
                gvar = dict(
                    default = 'clim_[model]_[source]'
                ),
                source = dict(
                ),
                model = dict(
                    values  = ['mocage'],
                    default = 'mocage',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clim_misc'


class DomainMonthClimMisc(GenericClim):
    """Monthly miscellaneous climatological files by domain."""

    _footprint = [
        month_deco,
        gdomain,
        dict(
            info = 'Monthly climatological files, domain indexed',
            attr = dict(
                kind = dict(
                    values  = ['generic_clim_misc'],
                ),
                geometry = dict(
                    type = LonlatGeometry,
                ),
                gvar = dict(
                    default = 'clim_[model]_[source]_[gdomain]'
                ),
                source = dict(
                ),
                model = dict(
                    values  = ['mocage'],
                    default = 'mocage',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'generic_clim_misc'


class ElmtEmissions(GenericClim):
    """Class for a chemical element climatology (domain dependant).

    A LonlatGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object
    and a specific chemical element emission.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Elmt climatology',
            attr = dict(
                kind = dict(
                    values = ['emiss_elmt', 'emiss_ch4'],
                    remap = dict(emiss_ch4 = 'emiss_elmt'),
                ),
                elmt = dict(
                    values = ['surf_ch4', 'volc'],
                    default = 'surf_ch4',
                    optional = True,
                ),
                geometry = dict(
                    type = LonlatGeometry,
                ),
                gvar = dict(
                    default = 'emis_[elmt]_[gdomain]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'emiss_elmt'


class SurfaceSpeciesConfig(GenericClim):
    """Class for a surface species configuration file (domain dependant).

    A LonlatGeometry object is needed. A Genvkey can be given
    with a default name retrieved thanks to a GenvDomain object.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Surface species configuration',
            attr = dict(
                kind = dict(
                    values = ['surf_species_cfg']
                ),
                geometry = dict(
                    type = LonlatGeometry,
                ),
                gvar = dict(
                    default = 'cfgfile_surface_[gdomain]'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'surf_species_cfg'
