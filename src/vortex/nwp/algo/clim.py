"""
AlgoComponents to build model's climatology files.
"""

import copy

from bronx.datagrip import namelist
from bronx.fancies import loggers
import footprints

from vortex.algo.components import BlindRun, AlgoComponent, Parallel, TaylorRun
from vortex.data.geometries import HorizontalGeometry
from vortex.tools.grib import EcGribDecoMixin
from vortex.tools.parallelism import TaylorVortexWorker
from .ifsroot import IFSParallel
from ..tools.drhook import DrHookDecoMixin


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class BuildPGD(BlindRun, DrHookDecoMixin, EcGribDecoMixin):
    """Preparation of physiographic fields for Surfex."""

    _footprint = dict(
        info="Physiographic fields for Surfex.",
        attr=dict(
            kind=dict(
                values=["buildpgd"],
            ),
        ),
    )


class BuildPGD_MPI(Parallel, DrHookDecoMixin, EcGribDecoMixin):
    """Preparation of physiographic fields for Surfex."""

    _footprint = dict(
        info="Physiographic fields for Surfex.",
        attr=dict(
            kind=dict(
                values=["buildpgd"],
            ),
        ),
    )


class C923(IFSParallel):
    """Preparation of climatologic fields."""

    _footprint = dict(
        info="Climatologic fields for Arpege/Arome.",
        attr=dict(
            kind=dict(
                values=["c923"],
            ),
            step=dict(
                info="""Step of conf 923 (NAMCLI::N923).
                          Defines the kind of fields and database processed.""",
                type=int,
                values=footprints.util.rangex(1, 10),
            ),
            orog_in_pgd=dict(
                info="""Whether orography may be read in a PGD file.
                          (NAMCLA::LIPGD=.TRUE.)""",
                type=bool,
                optional=True,
                default=False,
            ),
            input_orog_name=dict(
                info="Filename for input orography file (case LNORO=.T.).",
                optional=True,
                default="Neworog",
            ),
            xpname=dict(
                default="CLIM",
            ),
        ),
    )

    def prepare(self, rh, opts):
        super().prepare(rh, opts)
        # check PGD if needed
        if self.orog_in_pgd:
            pgd = self.context.sequence.effective_inputs(role=("Pgd",))
            if len(pgd) == 0:
                raise ValueError(
                    "As long as 'orog_in_pgd' attribute of this "
                    + "algo component is True, a 'Role: Pgd' "
                    + "resource must be provided."
                )
            pgd = pgd[0].rh
            if pgd.resource.nativefmt == "fa":
                self.algoassert(
                    pgd.container.basename == self.input_orog_name,
                    "Local name for resource Pgd must be '{}'".format(
                        self.input_orog_name
                    ),
                )
            elif pgd.resource.nativefmt == "lfi":
                raise NotImplementedError(
                    "CY43T2 onwards: lfi PGD should not be used."
                )

    def find_namelists(self, opts=None):
        namrh_list = [
            x.rh
            for x in self.context.sequence.effective_inputs(role=("Namelist",))
        ]
        self.algoassert(
            len(namrh_list) == 1,
            "One and only one namelist necessary as input.",
        )
        return namrh_list

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        super().prepare_namelist_delta(rh, namcontents, namlocal)
        namcontents["NAMMCC"]["N923"] = self.step
        namcontents.setmacro("LPGD", self.orog_in_pgd)
        return True


class FinalizePGD(AlgoComponent):
    """
    Finalise PGD file: report spectrally optimized orography from Clim to PGD,
    and add E-zone.

    .. deprecated:: since Vortex 1.3.0, use :class:`SetFilteredOrogInPGD` instead.
    """

    _footprint = dict(
        info="Finalisation of PGD.",
        attr=dict(
            kind=dict(
                values=["finalize_pgd"],
            ),
            pgd_out_name=dict(optional=True, default="PGD_final.fa"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..util.usepygram import epygram_checker

        ev = "1.2.14"
        self.algoassert(
            epygram_checker.is_available(version=ev),
            "Epygram >= " + ev + " is needed here",
        )

    def execute(self, rh, opts):  # @UnusedVariable
        """Convert SURFGEOPOTENTIEL from clim to SFX.ZS in pgd."""
        import numpy
        from ..util.usepygram import epygram, epy_env_prepare
        from bronx.meteo.constants import g0

        # Handle resources
        clim = self.context.sequence.effective_inputs(role=("Clim",))
        self.algoassert(
            len(clim) == 1, "One and only one Clim has to be provided"
        )
        pgdin = self.context.sequence.effective_inputs(role=("InputPGD",))
        self.algoassert(
            len(pgdin) == 1, "One and only one InputPGD has to be provided"
        )
        if self.system.path.exists(self.pgd_out_name):
            raise OSError(
                "The output pgd file {!r} already exists.".format(
                    self.pgd_out_name
                )
            )
        # copy fields
        with epy_env_prepare(self.ticket):
            epyclim = clim[0].rh.contents.data
            epypgd = pgdin[0].rh.contents.data
            epyclim.open()
            epypgd.open()
            pgdout = epygram.formats.resource(
                self.pgd_out_name,
                "w",
                fmt="FA",
                headername=epyclim.headername,
                geometry=epyclim.geometry,
                cdiden=epypgd.cdiden,
                validity=epypgd.validity,
                processtype=epypgd.processtype,
            )
            g = epyclim.readfield("SURFGEOPOTENTIEL")
            g.operation("/", g0)
            g.fid["FA"] = "SFX.ZS"
            for f in epypgd.listfields():
                fld = epypgd.readfield(f)
                if f == "SFX.ZS":
                    fld = g
                elif (
                    isinstance(fld, epygram.fields.H2DField)
                    and fld.geometry.grid.get("LAMzone") is not None
                ):
                    ext_data = numpy.ma.masked_equal(
                        numpy.zeros(g.data.shape), 0.0
                    )
                    ext_data[
                        : fld.geometry.dimensions["Y"],
                        : fld.geometry.dimensions["X"],
                    ] = fld.data[:, :]
                    fld = footprints.proxy.fields.almost_clone(
                        fld, geometry=g.geometry
                    )
                    fld.setdata(ext_data)
                pgdout.writefield(
                    fld, compression=epypgd.fieldscompression.get(f, None)
                )


class SetFilteredOrogInPGD(AlgoComponent):
    """
    Report spectrally optimized, filtered orography from Clim to PGD.
    """

    _footprint = dict(
        info="Report spectrally optimized, filtered orography from Clim to PGD.",
        attr=dict(
            kind=dict(
                values=["set_filtered_orog_in_pgd"],
            ),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..util.usepygram import epygram_checker

        ev = "1.3.2"
        self.algoassert(
            epygram_checker.is_available(version=ev),
            "Epygram >= " + ev + " is needed here",
        )

    def execute(self, rh, opts):  # @UnusedVariable
        """Convert SURFGEOPOTENTIEL from clim to SFX.ZS in pgd."""
        from ..util.usepygram import epygram_checker, epy_env_prepare
        from bronx.meteo.constants import g0

        # Handle resources
        clim = self.context.sequence.effective_inputs(role=("Clim",))
        self.algoassert(len(clim) == 1, "One and only one Clim to be provided")
        pgdin = self.context.sequence.effective_inputs(role=("InputPGD",))
        self.algoassert(
            len(pgdin) == 1, "One and only one InputPGD to be provided"
        )
        # copy fields
        with epy_env_prepare(self.ticket):
            epyclim = clim[0].rh.contents.data
            epypgd = pgdin[0].rh.contents.data
            epyclim.open()
            epypgd.open(openmode="a")
            # read spectrally fitted surface geopotential
            g = epyclim.readfield("SURFGEOPOTENTIEL")
            # convert to SURFEX orography
            g.operation("/", g0)
            g.fid["FA"] = "SFX.ZS"
            # write as orography
            if epygram_checker.is_available(version="1.3.6"):
                epypgd.fieldencoding(
                    g.fid["FA"], update_fieldscompression=True
                )
            else:
                # blank read, just to update fieldscompression
                epypgd.readfield(g.fid["FA"], getdata=False)
            epypgd.writefield(
                g, compression=epypgd.fieldscompression.get(g.fid["FA"], None)
            )
            epypgd.close()


class MakeLAMDomain(AlgoComponent):
    """
    Wrapper to call Epygram domain making functions and generate
    namelist deltas for geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["make_domain", "make_lam_domain"],
            ),
            geometry=dict(
                info="The horizontal geometry to be generated.",
                type=HorizontalGeometry,
            ),
            mode=dict(
                info=(
                    "Kind of input for building geometry:"
                    + "'center_dims' to build domain given its centre and"
                    + "dimensions; 'lonlat_included' to build domain given"
                    + "an included lon/lat area."
                ),
                values=["center_dims", "lonlat_included"],
            ),
            geom_params=dict(
                info=(
                    "Set of parameters and/or options to be passed to"
                    + "epygram.geometries.domain_making.build.build_geometry()"
                    + "or"
                    + "epygram.geometries.domain_making.build.build_geometry_fromlonlat()"
                ),
                type=footprints.FPDict,
            ),
            truncation=dict(
                info=(
                    "Type of spectral truncation, among"
                    + "('linear', 'quadratic', 'cubic')."
                ),
                optional=True,
                default="linear",
            ),
            orography_truncation=dict(
                info=(
                    "Type of truncation of orography, among"
                    + "('linear', 'quadratic', 'cubic')."
                ),
                optional=True,
                default="quadratic",
            ),
            e_zone_in_pgd=dict(
                info="Add E-zone sizes in BuildPGD namelist.",
                optional=True,
                type=bool,
                default=False,
            ),
            i_width_in_pgd=dict(
                info="Add I-width size in BuildPGD namelist.",
                optional=True,
                type=bool,
                default=False,
            ),
            # plot
            illustration=dict(
                info="Create the domain illustration image.",
                type=bool,
                optional=True,
                default=True,
            ),
            illustration_fmt=dict(
                info="The format of the domain illustration image.",
                values=["png", "pdf"],
                optional=True,
                default="png",
            ),
            plot_params=dict(
                info="Plot geometry parameters.",
                type=footprints.FPDict,
                optional=True,
                default=footprints.FPDict({"background": True}),
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..util.usepygram import epygram_checker

        ev = "1.2.14"
        if self.e_zone_in_pgd:
            ev = "1.3.2"
        if self.i_width_in_pgd:
            ev = "1.3.3"
        self.algoassert(
            epygram_checker.is_available(version=ev),
            "Epygram >= " + ev + " is needed here",
        )
        self._check_geometry()

    def _check_geometry(self):
        if self.mode == "center_dims":
            params = [
                "center_lon",
                "center_lat",
                "Xpoints_CI",
                "Ypoints_CI",
                "resolution",
            ]
            params_extended = params + [
                "tilting",
                "Iwidth",
                "force_projection",
                "maximize_CI_in_E",
                "reference_lat",
            ]
        elif self.mode == "lonlat_included":
            params = ["lonmin", "lonmax", "latmin", "latmax", "resolution"]
            params_extended = params + [
                "Iwidth",
                "force_projection",
                "maximize_CI_in_E",
            ]
        self.algoassert(
            set(params).issubset(set(self.geom_params.keys())),
            "With mode=={!s}, geom_params must contain at least {!s}".format(
                self.mode, params
            ),
        )
        self.algoassert(
            set(self.geom_params.keys()).issubset(set(params_extended)),
            "With mode=={!s}, geom_params must contain at most {!s}".format(
                self.mode, params
            ),
        )

    def execute(self, rh, opts):  # @UnusedVariable
        from ..util.usepygram import epygram

        dm = epygram.geometries.domain_making
        if self.mode == "center_dims":
            build_func = dm.build.build_geometry
            lonlat_included = None
        elif self.mode == "lonlat_included":
            build_func = dm.build.build_geometry_fromlonlat
            lonlat_included = self.geom_params
        # build geometry
        geometry = build_func(interactive=False, **self.geom_params)
        # summary, plot, namelists:
        with open(self.geometry.tag + "_summary.txt", "w") as o:
            o.write(str(dm.output.summary(geometry)))
        if self.illustration:
            dm.output.plot_geometry(
                geometry,
                lonlat_included=lonlat_included,
                out=".".join([self.geometry.tag, self.illustration_fmt]),
                **self.plot_params,
            )
        dm_extra_params = dict()
        if self.e_zone_in_pgd:
            dm_extra_params["Ezone_in_pgd"] = self.e_zone_in_pgd
        if self.i_width_in_pgd:
            dm_extra_params["Iwidth_in_pgd"] = self.i_width_in_pgd
        namelists = dm.output.lam_geom2namelists(
            geometry,
            truncation=self.truncation,
            orography_subtruncation=self.orography_truncation,
            **dm_extra_params,
        )
        dm.output.write_namelists(namelists, prefix=self.geometry.tag)


class MakeGaussGeometry(Parallel):
    """
    Wrapper to call Gauss geometry making RGRID and generate
    namelist deltas for geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["make_gauss_grid"],
            ),
            geometry=dict(
                info="The vortex horizontal geometry to be generated.",
                type=HorizontalGeometry,
            ),
            truncation=dict(
                info="nominal truncation",
                type=int,
            ),
            grid=dict(
                info="type of grid with regards to truncation, among (linear, quadratic, cubic)",
                optional=True,
                default="linear",
            ),
            orography_grid=dict(
                info="orography subtruncation (linear, quadratic, cubic)",
                optional=True,
                default="quadratic",
            ),
            stretching=dict(
                info="stretching factor",
                type=float,
                optional=True,
                default=1.0,
            ),
            pole=dict(
                info="pole of stretching (lon, lat), angles in degrees",
                type=footprints.FPDict,
                optional=True,
                default={"lon": 0.0, "lat": 90.0},
            ),
            # RGRID commandline options
            latitudes=dict(
                info="number of Gaussian latitudes",
                type=int,
                optional=True,
                default=None,
            ),
            longitudes=dict(
                info="maximum (equatorial) number of longitudes",
                type=int,
                optional=True,
                default=None,
            ),
            orthogonality=dict(
                info="orthogonality precision, as Log10() value",
                type=int,
                optional=True,
                default=None,
            ),
            aliasing=dict(
                info="allowed aliasing, as a Log10() value",
                type=int,
                optional=True,
                default=None,
            ),
            oddity=dict(
                info="odd numbers allowed (1) or not (0)",
                type=int,
                optional=True,
                default=None,
            ),
            verbosity=dict(
                info="verbosity (0 or 1)",
                type=int,
                optional=True,
                default=None,
            ),
            # plot
            illustration=dict(
                info="Create the domain illustration image.",
                type=bool,
                optional=True,
                default=True,
            ),
            illustration_fmt=dict(
                info="The format of the domain illustration image.",
                values=["png", "pdf"],
                optional=True,
                default="png",
            ),
            plot_params=dict(
                info="Plot geometry parameters.",
                type=footprints.FPDict,
                optional=True,
                default=footprints.FPDict({"background": True}),
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..util.usepygram import epygram_checker

        ev = "1.2.14"
        self.algoassert(
            epygram_checker.is_available(version=ev),
            "Epygram >= " + ev + " is needed here",
        )
        self._complete_dimensions()
        self._unit = 4

    def _complete_dimensions(self):
        from ..util.usepygram import epygram_checker

        if epygram_checker.is_available(version="1.4.4"):
            from epygram.geometries.SpectralGeometry import (
                complete_gridpoint_dimensions,
            )

            longitudes, latitudes = complete_gridpoint_dimensions(
                self.longitudes,
                self.latitudes,
                self.truncation,
                self.grid,
                self.stretching,
            )
            self._attributes["longitudes"] = longitudes
            self._attributes["latitudes"] = latitudes
        else:
            self._old_internal_complete_dimensions()

    def _old_internal_complete_dimensions(self):
        from epygram.geometries.SpectralGeometry import (
            gridpoint_dims_from_truncation,
        )

        if self.latitudes is None and self.longitudes is None:
            dims = gridpoint_dims_from_truncation(
                {"max": self.truncation}, grid=self.grid
            )
            self._attributes["latitudes"] = dims["lat_number"]
            self._attributes["longitudes"] = dims["max_lon_number"]
        elif self.longitudes is None:
            self._attributes["longitudes"] = 2 * self.latitudes
        elif self.latitudes is None:
            if self.longitudes % 4 != 0:
                self._attributes["latitudes"] = self.longitudes // 2 + 1
            else:
                self._attributes["latitudes"] = self.longitudes // 2

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        options = {
            "t": str(self.truncation),
            "g": str(self.latitudes),
            "l": str(self.longitudes),
            "f": str(self._unit),
        }
        options_dict = {
            "orthogonality": "o",
            "aliasing": "a",
            "oddity": "n",
            "verbosity": "v",
        }
        for k in options_dict.keys():
            if getattr(self, k) is not None:
                options[options_dict[k]] = str(getattr(self, k))
        return options

    def postfix(self, rh, opts):
        """Complete and write namelists."""
        from ..util.usepygram import epygram_checker

        if epygram_checker.is_available(version="1.4.4"):
            from epygram.geometries.domain_making.output import (
                gauss_rgrid2namelists,
            )

            gauss_rgrid2namelists(
                "fort.{!s}".format(self._unit),
                self.geometry.tag,
                self.latitudes,
                self.longitudes,
                self.truncation,
                self.stretching,
                self.orography_grid,
                self.pole,
            )
        else:
            self._old_internal_postfix(rh, opts)
        super().postfix(rh, opts)

    def _old_internal_postfix(self, rh, opts):
        """Complete and write namelists."""
        import math
        from epygram.geometries.SpectralGeometry import (
            truncation_from_gridpoint_dims,
        )

        # complete scalar parameters
        nam = namelist.NamelistSet()
        nam.add(namelist.NamelistBlock("NAM_PGD_GRID"))
        nam.add(namelist.NamelistBlock("NAMDIM"))
        nam.add(namelist.NamelistBlock("NAMGEM"))
        nam["NAM_PGD_GRID"]["CGRID"] = "GAUSS"
        nam["NAMDIM"]["NDGLG"] = self.latitudes
        nam["NAMDIM"]["NDLON"] = self.longitudes
        nam["NAMDIM"]["NSMAX"] = self.truncation
        nam["NAMGEM"]["NHTYP"] = 2
        nam["NAMGEM"]["NSTTYP"] = (
            2 if self.pole != {"lon": 0.0, "lat": 90.0} else 1
        )
        nam["NAMGEM"]["RMUCEN"] = math.sin(
            math.radians(float(self.pole["lat"]))
        )
        nam["NAMGEM"]["RLOCEN"] = math.radians(float(self.pole["lon"]))
        nam["NAMGEM"]["RSTRET"] = self.stretching
        # numbers of longitudes
        with open("fort.{!s}".format(self._unit)) as n:
            namrgri = namelist.namparse(n)
            nam.merge(namrgri)
        # PGD namelist
        nam_pgd = copy.deepcopy(nam)
        nam_pgd["NAMGEM"].delvar("NHTYP")
        nam_pgd["NAMGEM"].delvar("NSTTYP")
        nam_pgd["NAMDIM"].delvar("NSMAX")
        nam_pgd["NAMDIM"].delvar("NDLON")
        with open(
            ".".join([self.geometry.tag, "namel_buildpgd", "geoblocks"]), "w"
        ) as out:
            out.write(nam_pgd.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        # C923 namelist
        del nam["NAM_PGD_GRID"]
        with open(
            ".".join([self.geometry.tag, "namel_c923", "geoblocks"]), "w"
        ) as out:
            out.write(nam.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        # subtruncated grid for orography
        from ..util.usepygram import epygram_checker

        ev = "1.4.4"
        if epygram_checker.is_available(version=ev):
            trunc_nsmax = truncation_from_gridpoint_dims(
                {
                    "lat_number": self.latitudes,
                    "max_lon_number": self.longitudes,
                },
                grid=self.orography_grid,
                stretching_coef=self.stretching,
            )["max"]
        else:
            trunc_nsmax = truncation_from_gridpoint_dims(
                {
                    "lat_number": self.latitudes,
                    "max_lon_number": self.longitudes,
                },
                grid=self.orography_grid,
            )["max"]
        nam["NAMDIM"]["NSMAX"] = trunc_nsmax
        with open(
            ".".join([self.geometry.tag, "namel_c923_orography", "geoblocks"]),
            "w",
        ) as out:
            out.write(nam.dumps(sorting=namelist.SECOND_ORDER_SORTING))
        # C927 (fullpos) namelist
        nam = namelist.NamelistSet()
        nam.add(namelist.NamelistBlock("NAMFPD"))
        nam.add(namelist.NamelistBlock("NAMFPG"))
        nam["NAMFPD"]["NLAT"] = self.latitudes
        nam["NAMFPD"]["NLON"] = self.longitudes
        nam["NAMFPG"]["NFPMAX"] = self.truncation
        nam["NAMFPG"]["NFPHTYP"] = 2
        nam["NAMFPG"]["NFPTTYP"] = (
            2 if self.pole != {"lon": 0.0, "lat": 90.0} else 1
        )
        nam["NAMFPG"]["FPMUCEN"] = math.sin(
            math.radians(float(self.pole["lat"]))
        )
        nam["NAMFPG"]["FPLOCEN"] = math.radians(float(self.pole["lon"]))
        nam["NAMFPG"]["FPSTRET"] = self.stretching
        nrgri = [v for _, v in sorted(namrgri["NAMRGRI"].items())]
        for i in range(len(nrgri)):
            nam["NAMFPG"]["NFPRGRI({:>4})".format(i + 1)] = nrgri[i]
        with open(
            ".".join([self.geometry.tag, "namel_c927", "geoblocks"]), "w"
        ) as out:
            out.write(nam.dumps(sorting=namelist.SECOND_ORDER_SORTING))


class MakeBDAPDomain(AlgoComponent):
    """
    Wrapper to call Epygram domain making functions and generate
    namelist deltas for BDAP (lonlat) geometry (BuildPGD & C923).
    """

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["make_domain", "make_bdap_domain"],
            ),
            geometry=dict(
                info="The horizontal geometry to be generated.",
                type=HorizontalGeometry,
            ),
            mode=dict(
                info=(
                    "Kind of input for building geometry:"
                    + "'boundaries' to build domain given its lon/lat boundaries"
                    + "(+ resolution); 'inside_model' to build domain given"
                    + "a model geometry to be included in (+ resolution)."
                ),
                values=["boundaries", "inside_model"],
            ),
            resolution=dict(
                info="Resolution in degrees.",
                type=float,
                optional=True,
                default=None,
            ),
            resolution_x=dict(
                info="X resolution in degrees (if different from Y).",
                type=float,
                optional=True,
                default=None,
            ),
            resolution_y=dict(
                info="Y resolution in degrees (if different from X).",
                type=float,
                optional=True,
                default=None,
            ),
            boundaries=dict(
                info="Lonlat boundaries of the domain, case mode='boundaries'.",
                type=footprints.FPDict,
                optional=True,
                default=None,
            ),
            model_clim=dict(
                info="Filename of the model clim, case mode='inside_model'.",
                optional=True,
                default=None,
            ),
            # plot
            illustration=dict(
                info="Create the domain illustration image.",
                type=bool,
                optional=True,
                default=True,
            ),
            illustration_fmt=dict(
                info="The format of the domain illustration image.",
                values=["png", "pdf"],
                optional=True,
                default="png",
            ),
            plot_params=dict(
                info="Plot geometry parameters.",
                type=footprints.FPDict,
                optional=True,
                default=footprints.FPDict({"background": True}),
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..util.usepygram import epygram_checker

        ev = "1.2.14"
        self.algoassert(
            epygram_checker.is_available(version=ev),
            "Epygram >= " + ev + " is needed here",
        )
        if self.mode == "boundaries":
            params = ["lonmin", "lonmax", "latmin", "latmax"]
            self.algoassert(
                set(params) == set(self.boundaries.keys()),
                "With mode=={}, boundaries must contain at least {}".format(
                    self.mode, str(params)
                ),
            )
            if self.model_clim is not None:
                logger.info("attribute *model_clim* ignored")
        elif self.mode == "inside_model":
            self.algoassert(
                self.model_clim is not None,
                "attribute *model_clim* must be provided with "
                + "mode=='inside_model'.",
            )
            self.algoassert(self.sh.path.exists(self.model_clim))
            if self.boundaries is not None:
                logger.info("attribute *boundaries* ignored")
        if self.resolution is None:
            self.algoassert(
                None not in (self.resolution_x, self.resolution_y),
                "Must provide *resolution* OR *resolution_x/resolution_y*",
            )
        else:
            self.algoassert(
                self.resolution_x is None and self.resolution_y is None,
                "Must provide *resolution* OR *resolution_x/resolution_y*",
            )

    def execute(self, rh, opts):  # @UnusedVariable
        from ..util.usepygram import epygram

        dm = epygram.geometries.domain_making
        if self.mode == "inside_model":
            r = epygram.formats.resource(self.model_clim, "r")
            if r.format == "FA":
                g = r.readfield("SURFGEOPOTENTIEL")
            else:
                raise NotImplementedError()
            boundaries = dm.build.compute_lonlat_included(g.geometry)
        else:
            boundaries = self.boundaries
        # build geometry
        if self.resolution is None:
            geometry = dm.build.build_lonlat_geometry(
                boundaries, resolution=(self.resolution_x, self.resolution_y)
            )
        else:
            geometry = dm.build.build_lonlat_geometry(
                boundaries, resolution=self.resolution
            )
        # summary, plot, namelists:
        if self.illustration:
            fig, _ = geometry.plotgeometry(
                color="red", title=self.geometry.tag, **self.plot_params
            )
            fig.savefig(
                ".".join([self.geometry.tag, self.illustration_fmt]),
                bbox_inches="tight",
            )
        namelists = dm.output.regll_geom2namelists(geometry)
        dm.output.write_namelists(namelists, prefix=self.geometry.tag)
        self.system.symlink(
            ".".join([self.geometry.tag, "namel_c923", "geoblocks"]),
            ".".join([self.geometry.tag, "namel_c923_orography", "geoblocks"]),
        )


class AddPolesToGLOB(TaylorRun):
    """
    Add poles to a GLOB* regular FA Lon/Lat file that do not contain them.
    """

    _footprint = dict(
        info="Add poles to a GLOB* regular FA Lon/Lat file that do not contain them.",
        attr=dict(
            kind=dict(
                values=["add_poles"],
            ),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..util.usepygram import epygram_checker

        ev = "1.3.4"
        self.algoassert(
            epygram_checker.is_available(version=ev),
            "Epygram >= " + ev + " is needed here",
        )

    def execute(self, rh, opts):  # @UnusedVariable
        """Add poles to a GLOB* regular FA Lon/Lat file that do not contain them."""
        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instructions(rh, opts)
        clims = self.context.sequence.effective_inputs(role=("Clim",))
        self._add_instructions(
            common_i,
            dict(filename=[s.rh.container.localpath() for s in clims]),
        )
        self._default_post_execute(rh, opts)


class _AddPolesWorker(TaylorVortexWorker):
    _footprint = dict(
        attr=dict(
            kind=dict(values=["add_poles"]),
            filename=dict(info="The file to be processed."),
        )
    )

    def vortex_task(self, **_):
        from ..util.usepygram import (
            add_poles_to_reglonlat_file,
            epy_env_prepare,
        )

        with epy_env_prepare(self.ticket):
            add_poles_to_reglonlat_file(self.filename)


class Festat(Parallel):
    """
    Class to run the festat binary.
    """

    _footprint = dict(
        info="Run festat",
        attr=dict(
            kind=dict(
                values=[
                    "run_festat",
                ],
            ),
            nb_digits=dict(
                info="Number of digits on which the name of the files should be written",
                type=int,
                default=3,
                optional=True,
            ),
            prefix=dict(
                info="Name of the files for the binary",
                optional=True,
                default="CNAME",
            ),
        ),
    )

    _nb_input_files = 0

    def prepare(self, rh, opts):
        # Check the namelist
        input_namelist = self.context.sequence.effective_inputs(
            role="Namelist", kind="namelist"
        )
        if len(input_namelist) != 1:
            logger.error("One and only one namelist must be provided.")
            raise ValueError("One and only one namelist must be provided.")
        else:
            input_namelist = input_namelist[0].rh
        # Create links for the input files
        maxinsec = 10**self.nb_digits
        insec = self.context.sequence.effective_inputs(role="InputFiles")
        nbinsec = len(insec)
        if nbinsec > maxinsec:
            logger.error(
                "The number of input files %s exceed the maximum number of files available %s.",
                nbinsec,
                maxinsec,
            )
            raise ValueError(
                "The number of input files exceed the maximum number of files available."
            )
        else:
            logger.info("%s input files will be treated.", nbinsec)
        i = 0
        for sec in insec:
            i += 1
            self.system.symlink(
                sec.rh.container.actualpath(),
                "{prefix}{number}".format(
                    prefix=self.prefix, number=str(i).zfill(self.nb_digits)
                ),
            )
        # Put the number of sections and the prefix of the input files in the namelist
        namcontents = input_namelist.contents
        logger.info(
            "Setup macro CNAME=%s in %s",
            self.prefix,
            input_namelist.container.actualpath(),
        )
        namcontents.setmacro("CNAME", self.prefix)
        logger.info(
            "Setup macro NCASES=%s in %s",
            i,
            input_namelist.container.actualpath(),
        )
        namcontents.setmacro("NCASES", i)
        namcontents.rewrite(input_namelist.container)
        self._nb_input_files = i
        # Call the super class
        super().prepare(rh, opts)

    def postfix(self, rh, opts):
        # Rename stabal files
        list_stabal = self.system.glob("stab*")
        for stabal in list_stabal:
            self.system.mv(
                stabal,
                "{stabal}.ncases_{ncases}".format(
                    stabal=stabal, ncases=self._nb_input_files
                ),
            )
        # Deal with diag files
        list_diag_stat = self.system.glob("co*y")
        if len(list_diag_stat) > 0:
            diastat_dir_name = "dia.stat.ncases_{ncases}".format(
                ncases=self._nb_input_files
            )
            self.system.mkdir(diastat_dir_name)
            for file in list_diag_stat:
                self.system.mv(file, diastat_dir_name + "/")
            self.system.tar(diastat_dir_name + ".tar", diastat_dir_name)
        list_diag_expl = self.system.glob("expl*y")
        if len(list_diag_expl) > 0:
            diaexpl_dir_name = "dia.expl.ncases_{ncases}".format(
                ncases=self._nb_input_files
            )
            self.system.mkdir(diaexpl_dir_name)
            for file in list_diag_expl:
                self.system.mv(file, diaexpl_dir_name + "/")
            self.system.tar(diaexpl_dir_name + ".tar", diaexpl_dir_name)
        # Call the superclass
        super().postfix(rh, opts)


class Fediacov(Parallel):
    """
    Class to compute diagnostics about covariance.
    """

    _footprint = dict(
        info="Run fediacov",
        attr=dict(
            kind=dict(
                values=[
                    "run_fediacov",
                ],
            ),
        ),
    )

    def postfix(self, rh, opts):
        # Deal with diag files
        list_diag = self.system.glob("*y")
        if len(list_diag) > 0:
            self.system.mkdir("diag")
            for file in list_diag:
                self.system.mv(file, "diag/")
            self.system.tar("diag.tar", "diag")
        # Call the superclass
        super().postfix(rh, opts)
