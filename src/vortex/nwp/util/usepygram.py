"""
Usage of EPyGrAM package.

When loaded, this module discards any FootprintBase resource collected as a container
in EPyGrAM package.
"""

import copy

import footprints
from bronx.fancies import loggers
from bronx.stdtypes import date
from bronx.stdtypes.date import Date, Period, Time
from bronx.syntax.externalcode import ExternalCodeImportChecker
from footprints import proxy as fpx
from vortex import sessions
from vortex.data.contents import MetaDataReader
from vortex.data.handlers import Handler

logger = loggers.getLogger(__name__)

epygram_checker = ExternalCodeImportChecker("epygram")
with epygram_checker as ec_register:
    import epygram  # @UnusedImport

    try:
        ec_register.update(version=epygram.__version__)
    except AttributeError:
        raise ImportError("Improper eypgram module.")
    try:
        u_unused = epygram.formats.FA
        hasFA = True
    except AttributeError:
        hasFA = False
    ec_register.update(needFA=hasFA)
    try:
        u_unused = epygram.formats.GRIB
        hasGRIB = True
    except AttributeError:
        hasGRIB = False
    ec_register.update(needGRIB=hasGRIB)
    logger.info(
        "Epygram %s loaded (GRIB support=%s, FA support=%s).",
        epygram.__version__,
        hasGRIB,
        hasFA,
    )

np_checker = ExternalCodeImportChecker("numpy")
with np_checker as npregister:
    import numpy as np

    npregister.update(version=np.__version__)

footprints.proxy.containers.discard_package("epygram", verbose=False)

__all__ = []


def _sources_and_names_fixup(sources, names=None):
    """Fix **sources** and **names** lists."""
    # Prepare sources names
    if not isinstance(sources, (list, tuple, set)):
        sources = [
            sources,
        ]
    sources = [source.upper() for source in sources]
    # Prepare output names
    if names is None:
        names = sources
    else:
        if not isinstance(names, (list, tuple, set)):
            names = [
                names,
            ]
        names = [name.upper().replace(" ", ".") for name in names]
    # Fill the sources list if necessary
    if len(sources) == 1 and len(names) > 1:
        sources *= len(names)
    if len(sources) != len(names):
        raise ValueError(
            "Sizes of sources and names do not fit the requirements."
        )
    return sources, names


@epygram_checker.disabled_if_unavailable
def clone_fields(
    datain,
    dataout,
    sources,
    names=None,
    value=None,
    pack=None,
    overwrite=False,
):
    """Clone any existing fields ending with``source`` to some new field."""
    datain.open()
    sources, names = _sources_and_names_fixup(sources, names)

    tablein = datain.listfields()
    tableout = dataout.listfields()
    addedfields = 0

    # Look for the input fields,
    for source, name in zip(sources, names):
        fx = None
        comprpack = None
        for fieldname in [x for x in sorted(tablein) if x.endswith(source)]:
            newfield = fieldname.replace(source, "") + name
            if not overwrite and newfield in tableout:
                logger.warning("Field <%s> already in output file", newfield)
            else:
                # If the values are to be overwritten : do not read the input
                # field several times...
                if value is None or fx is None or comprpack is None:
                    fx = datain.readfield(fieldname)
                    comprpack = datain.fieldscompression.get(fieldname)
                    if pack is not None:
                        comprpack.update(pack)
                    fy = fx.clone({x: newfield for x in fx.fid.keys()})
                    if value is not None:
                        fy.data.fill(value)
                # If fy is re-used, change the field names
                if value is not None:
                    for fidk in fx.fid.keys():
                        fy.fid[fidk] = newfield
                # On the first append, open the output file
                if addedfields == 0:
                    dataout.close()
                    dataout.open(openmode="a")
                # Actually add the new field
                logger.info("Add field {} pack={}".format(fy.fid, comprpack))
                dataout.writefield(fy, compression=comprpack)
                addedfields += 1

    if addedfields:
        dataout.close()
    datain.close()
    return addedfields


def epy_env_prepare(t):
    localenv = t.sh.env.clone()
    localenv.verbose(True, t.sh)
    if localenv.OMP_NUM_THREADS is None:
        localenv.OMP_NUM_THREADS = 1
    localenv.update(
        LFI_HNDL_SPEC=":1",
        DR_HOOK_SILENT=1,
        DR_HOOK_NOT_MPI=1,
    )
    # Clean trash...
    del localenv.GRIB_SAMPLES_PATH
    del localenv.GRIB_DEFINITION_PATH
    del localenv.ECCODES_SAMPLES_PATH
    del localenv.ECCODES_DEFINITION_PATH
    return localenv


@epygram_checker.disabled_if_unavailable
def addfield(t, rh, fieldsource, fieldtarget, constvalue, pack=None):
    """Provider hook for adding a field through cloning."""
    if rh.container.exists():
        with epy_env_prepare(t):
            clone_fields(
                rh.contents.data,
                rh.contents.data,
                fieldsource,
                names=fieldtarget,
                value=constvalue,
                pack=pack,
            )
    else:
        logger.warning(
            "Try to add field on a missing resource <%s>",
            rh.container.localpath(),
        )


@epygram_checker.disabled_if_unavailable
def copyfield(t, rh, rhsource, fieldsource, fieldtarget, pack=None):
    """Provider hook for copying fields between FA files (but do not overwrite existing fields)."""
    if rh.container.exists():
        with epy_env_prepare(t):
            clone_fields(
                rhsource.contents.data,
                rh.contents.data,
                fieldsource,
                fieldtarget,
                pack=pack,
            )
    else:
        logger.warning(
            "Try to copy field on a missing resource <%s>",
            rh.container.localpath(),
        )


@epygram_checker.disabled_if_unavailable
def overwritefield(t, rh, rhsource, fieldsource, fieldtarget, pack=None):
    """Provider hook for copying fields between FA files (overwrite existing fields)."""
    if rh.container.exists():
        with epy_env_prepare(t):
            clone_fields(
                rhsource.contents.data,
                rh.contents.data,
                fieldsource,
                fieldtarget,
                overwrite=True,
                pack=pack,
            )
    else:
        logger.warning(
            "Try to copy field on a missing resource <%s>",
            rh.container.localpath(),
        )


@np_checker.disabled_if_unavailable
@epygram_checker.disabled_if_unavailable
def updatefield(t, rh, rhsource, fieldsource, fieldtarget, masktype, *kargs):
    """
    Provider hook for updating fields in the **rh** FA files.

    The content (not the field itself) of **fieldsource** will be copied to
    **fieldtarget**. Some kind of masking is performed. Depending on
    **masktype**, only a subset of the field content might be updated.
    **masktype** can take the following values:

        * ``none``: no mask, the whole content is copied;
        * ``np.ma.masked``: masked values are ignored during the copy.

    """
    if rh.container.exists():
        with epy_env_prepare(t):
            # Various initialisations
            fieldsource, fieldtarget = _sources_and_names_fixup(
                fieldsource, fieldtarget
            )
            datain = rhsource.contents.data
            datain.open()
            dataout = rh.contents.data
            dataout.close()
            dataout.open(openmode="a")
            tablein = datain.listfields()
            tableout = dataout.listfields()
            updatedfields = 0

            # Function that creates the subset of elements to update
            if masktype == "none":

                def subsetfunc(epyobj):
                    return Ellipsis

            elif masktype == "np.ma.masked":

                def subsetfunc(epyobj):
                    if np.ma.is_masked(epyobj.data):
                        return np.logical_not(epyobj.data.mask)
                    else:
                        return Ellipsis

            else:
                raise ValueError(
                    "Unsupported masktype in the updatefield hook."
                )

            # Look for the input fields and update them
            for source, target in zip(fieldsource, fieldtarget):
                for fieldname in [
                    x for x in sorted(tablein) if x.endswith(source)
                ]:
                    targetfield = fieldname.replace(source, "") + target
                    if targetfield in tableout:
                        fx = datain.readfield(fieldname)
                        fy = dataout.readfield(targetfield)
                        subset = subsetfunc(fx)
                        fy.data[subset] = fx.data[subset]
                        dataout.writefield(fy)
                        updatedfields += 1
                    else:
                        logger.warning(
                            "Field <%s> is missing in the output file",
                            targetfield,
                        )

            dataout.close()
            datain.close()
            return updatedfields
    else:
        logger.warning(
            "Try to copy field on a missing resource <%s>",
            rh.container.localpath(),
        )


class EpygramMetadataReader(MetaDataReader):
    _abstract = True
    _footprint = dict(
        info="Abstract MetaDataReader for formats handled by epygram",
    )

    def _do_delayed_init(self):
        epyf = self._content_in
        if not epyf.isopen:
            epyf.open()
        date_epy, term_epy = self._process_epy(epyf)
        self._datahide = {
            "date": Date(date_epy) if date_epy else date_epy,
            "term": Time(
                hour=int(term_epy.total_seconds() / 3600),
                minute=int(term_epy.total_seconds() / 60) % 60,
            ),
        }

    def _process_epy(self, epyf):
        """Abstract method that does the actual processing using epygram."""
        raise NotImplementedError("Abstract method")


@epygram_checker.disabled_if_unavailable
class FaMetadataReader(EpygramMetadataReader):
    _footprint = dict(
        info="MetaDataReader for the FA file format",
        attr=dict(format=dict(values=("FA",))),
    )

    def _process_epy(self, epyf):
        # Just call the epygram function !
        with epy_env_prepare(sessions.current()):
            return epyf.validity.getbasis(), epyf.validity.term()


@epygram_checker.disabled_if_unavailable(version="1.0.0")
class GribMetadataReader(EpygramMetadataReader):
    _footprint = dict(
        info="MetaDataReader for the GRIB file format",
        attr=dict(format=dict(values=("GRIB",))),
    )

    def _process_epy(self, epyf):
        # Loop over the fields and check the unicity of date/term
        bundle = set()
        with epy_env_prepare(sessions.current()):
            epyfld = epyf.iter_fields(getdata=False)
            while epyfld:
                bundle.add(
                    (epyfld.validity.getbasis(), epyfld.validity.term())
                )
                epyfld = epyf.iter_fields(getdata=False)
        if len(bundle) > 1:
            logger.error(
                "The GRIB file contains fileds with different date and terms."
            )
        if len(bundle) == 0:
            logger.warning("The GRIB file doesn't contains any fields")
            return None, 0
        else:
            return bundle.pop()


@epygram_checker.disabled_if_unavailable(version="1.2.11")
def mk_pgdfa923_from_pgdlfi(
    t,
    rh_pgdlfi,
    nam923blocks,
    outname=None,
    fieldslist=None,
    field_prefix="S1D_",
    pack=None,
):
    """
    Hook to convert fields from a PGD.lfi to well-formatted for clim923 FA format.

    :param t: session ticket
    :param rh_pgdlfi: resource handler of source PGD.lfi to process
    :param nam923blocks: namelist blocks of geometry for clim923
    :param outname: output filename
    :param fieldslist: list of fields to convert
    :param field_prefix: prefix to add to field name in FA
    :param pack: packing for fields to write
    """
    dm = epygram.geometries.domain_making

    def sfxlfi2fa_field(fld, geom):
        fldout = fpx.fields.almost_clone(
            fld, geometry=geom, fid={"FA": field_prefix + fld.fid["LFI"]}
        )
        fldout.setdata(fld.data[1:-1, 1:-1])
        return fldout

    if fieldslist is None:
        fieldslist = ["ZS", "COVER001", "COVER002"]
    if pack is None:
        pack = {"KNGRIB": -1}
    if outname is None:
        outname = rh_pgdlfi.container.abspath + ".fa923"
    if not t.sh.path.exists(outname):
        with epy_env_prepare(t):
            pgdin = fpx.dataformats.almost_clone(
                rh_pgdlfi.contents.data, true3d=True
            )
            geom, spgeom = dm.build.build_geom_from_e923nam(
                nam923blocks
            )  # TODO: Arpege case
            validity = epygram.base.FieldValidity(
                date_time=Date(1994, 5, 31, 0),  # Date of birth of ALADIN
                term=Period(0),
            )
            pgdout = epygram.formats.resource(
                filename=outname,
                openmode="w",
                fmt="FA",
                processtype="initialization",
                validity=validity,
                geometry=geom,
                spectral_geometry=spgeom,
            )
            for f in fieldslist:
                fldout = sfxlfi2fa_field(pgdin.readfield(f), geom)
                pgdout.writefield(fldout, compression=pack)
    else:
        logger.warning(
            "Try to create an already existing resource <%s>", outname
        )


@epygram_checker.disabled_if_unavailable(version="1.0.0")
def empty_fa(t, rh, empty_name):
    """
    Create an empty FA file with fieldname **empty_name**,
    creating header from given existing FA resource handler **rh**.

    :return: the empty epygram resource, closed
    """
    if rh.container.exists():
        with epy_env_prepare(t):
            rh.contents.data.open()
            assert not t.sh.path.exists(empty_name), (
                "Empty target filename already exist: {}".format(empty_name)
            )
            e = epygram.formats.resource(
                empty_name,
                "w",
                fmt="FA",
                headername=rh.contents.data.headername,
                validity=rh.contents.data.validity,
                processtype=rh.contents.data.processtype,
                cdiden=rh.contents.cdiden,
            )
            e.close()
            rh.contents.data.close()
            return e
    else:
        raise OSError(
            "Try to copy header from a missing resource <{!s}>".format(
                rh.container.localpath()
            )
        )


@epygram_checker.disabled_if_unavailable(version="1.0.0")
def geopotentiel2zs(t, rh, rhsource, pack=None):
    """Copy surface geopotential from clim to zs in PGD."""
    from bronx.meteo.constants import g0

    if rh.container.exists():
        with epy_env_prepare(t):
            orog = rhsource.contents.data.readfield("SURFGEOPOTENTIEL")
            orog.operation("/", g0)
            orog.fid["FA"] = "SFX.ZS"
            rh.contents.data.close()
            rh.contents.data.open(openmode="a")
            rh.contents.data.writefield(orog, compression=pack)
    else:
        logger.warning(
            "Try to copy field on a missing resource <%s>",
            rh.container.localpath(),
        )


@epygram_checker.disabled_if_unavailable(version="1.3.4")
def add_poles_to_GLOB_file(filename):
    """
    DEPRECATED: please use add_poles_to_reglonlat_file instead
    Add poles to a GLOB* regular FA Lon/Lat file that do not contain them.
    """
    import numpy

    rin = epygram.formats.resource(filename, "r")
    filename_out = filename + "+poles"
    rout = epygram.formats.resource(
        filename_out,
        "w",
        fmt=rin.format,
        validity=epygram.base.FieldValidity(
            date_time=date.today(), term=date.Period(0, 0, 0)
        ),
        processtype=rin.processtype,
        cdiden=rin.cdiden,
    )
    assert rin.geometry.gimme_corners_ll()["ul"][1] < 90.0, (
        "This file already contains poles."
    )
    for f in rin.listfields():
        if f == "SPECSURFGEOPOTEN":
            continue
        fld = rin.readfield(f)
        write_args = {}
        if isinstance(fld, epygram.fields.H2DField):
            # create new geometry
            newdims = copy.deepcopy(fld.geometry.dimensions)
            newdims["Y"] += 2
            newgrid = copy.deepcopy(fld.geometry.grid)
            newgrid["input_position"] = (
                newgrid["input_position"][0],
                newgrid["input_position"][1] + 1,
            )
            newgeom = fpx.geometrys.almost_clone(
                fld.geometry, dimensions=newdims, grid=newgrid
            )
            # compute poles data value as mean of last latitude circle
            newdata = numpy.zeros((newdims["Y"], newdims["X"]))
            newdata[1:-1, :] = fld.data[...]
            newdata[0, :] = newdata[1, :].mean()
            newdata[-1, :] = newdata[-2, :].mean()
            # clone field with new geometry
            fld = fpx.fields.almost_clone(fld, geometry=newgeom)
            fld.data = newdata
            # get initial compression
            write_args = dict(compression=rin.fieldscompression[fld.fid["FA"]])
        rout.writefield(fld, **write_args)


@epygram_checker.disabled_if_unavailable(version="1.3.4")
def add_poles_to_reglonlat_file(filename):
    """
    Add pole(s) to a regular FA Lon/Lat file that do not contain them.
    """
    import numpy

    rin = epygram.formats.resource(filename, "r")
    filename_out = filename + "+poles"
    rout = epygram.formats.resource(
        filename_out,
        "w",
        fmt=rin.format,
        validity=epygram.base.FieldValidity(
            date_time=rin.validity.get(), term=date.Period(0, 0, 0)
        ),
        processtype=rin.processtype,
        cdiden=rin.cdiden,
    )
    assert rin.geometry.name == "regular_lonlat", (
        "This file's geometry is not regular lon/lat, cannot add pole(s)."
    )
    # determine what is to be done
    resolution = rin.geometry.grid["Y_resolution"].get("degrees")
    latmin = rin.geometry.gimme_corners_ll()["ll"][1]
    latmax = rin.geometry.gimme_corners_ll()["ul"][1]
    # south
    south = False
    if abs(-90.0 - latmin) <= epygram.config.epsilon:
        logger.info("This file already contains south pole")
    elif abs((-90.0 + resolution) - latmin) <= epygram.config.epsilon:
        south = True
    else:
        logger.info(
            "This file south border is too far from south pole to add it."
        )
    # north
    north = False
    if abs(90.0 - latmax) <= epygram.config.epsilon:
        logger.info("This file already contains north pole")
    elif abs((90.0 - resolution) - latmax) <= epygram.config.epsilon:
        north = True
    else:
        logger.info(
            "This file north border is too far from north pole to add it."
        )
    if not north and not south:
        raise epygram.epygramError("Nothing to do")
    # prepare new geom
    geom = rin.readfield("SURFGEOPOTENTIEL").geometry
    newdims = copy.deepcopy(geom.dimensions)
    newgrid = copy.deepcopy(geom.grid)
    if north and south:
        newdims["Y"] += 2
    else:
        newdims["Y"] += 1
    if south:
        newgrid["input_lon"] = epygram.util.Angle(
            geom.gimme_corners_ll()["ll"][0], "degrees"
        )
        newgrid["input_lat"] = epygram.util.Angle(
            geom.gimme_corners_ll()["ll"][1] - resolution, "degrees"
        )
        newgrid["input_position"] = (0, 0)
    else:  # north only: 0,0 has not changed
        newgrid["input_lon"] = epygram.util.Angle(
            geom.gimme_corners_ll()["ll"][0], "degrees"
        )
        newgrid["input_lat"] = epygram.util.Angle(
            geom.gimme_corners_ll()["ll"][1], "degrees"
        )
        newgrid["input_position"] = (0, 0)
    newgeom = fpx.geometrys.almost_clone(
        geom, dimensions=newdims, grid=newgrid
    )
    # loop on fields
    for f in rin.listfields():
        if f == "SPECSURFGEOPOTEN":
            continue  # meaningless in lonlat clims
        fld = rin.readfield(f)
        write_args = {}
        if isinstance(fld, epygram.fields.H2DField):
            # compute poles data value as mean of last latitude circle
            newdata = numpy.zeros((newdims["Y"], newdims["X"]))
            if south and north:
                newdata[1:-1, :] = fld.data[...]
                newdata[0, :] = newdata[1, :].mean()
                newdata[-1, :] = newdata[-2, :].mean()
            elif south:
                newdata[1:, :] = fld.data[...]
                newdata[0, :] = newdata[1, :].mean()
            elif north:
                newdata[:-1, :] = fld.data[...]
                newdata[-1, :] = newdata[-2, :].mean()
            # clone field with new geometry
            fld = fpx.fields.almost_clone(fld, geometry=newgeom)
            fld.data = newdata
            # get initial compression
            write_args = dict(compression=rin.fieldscompression[fld.fid["FA"]])
        rout.writefield(fld, **write_args)


@epygram_checker.disabled_if_unavailable()
def split_errgrib_on_shortname(t, rh):
    """Split a Background Error GRIB file into pieces (based on the GRIB shortName)."""
    # Sanity checks
    if (
        rh.resource.realkind != "bgstderr"
        or getattr(rh.resource, "variable", None) is not None
    ):
        raise ValueError("Incompatible resource: {!s}".format(rh))

    def create_section(sn):
        """Create a new section object for a given shortName (**sn**)."""
        sn_r = fpx.resource(
            variable=sn, **rh.resource.footprint_as_shallow_dict()
        )
        sn_p = fpx.provider(magic="magic:///")
        sn_c = fpx.container(
            filename=rh.container.localpath() + sn, format="grib", mode="ab+"
        )
        secs = t.context.sequence.input(
            rh=Handler(dict(resource=sn_r, provider=sn_p, container=sn_c)),
            role="BackgroundStdError",
        )
        secs[0].get()
        return secs[0]

    # Iterate over the GRIB messages
    gribs = rh.contents.data
    sections = dict()
    try:
        grb = gribs.iter_messages(headers_only=False)
        while grb is not None:
            # Find the ShortName
            fid = grb.genfid()
            for k in sorted(fid.keys()):
                sn = fid[k].get("shortName", None)
                if sn is not None:
                    break
            if sn is None:
                raise OSError("No ShortName was found")
            # Set up the appropriate section
            if sn not in sections:
                sections[sn] = create_section(sn)
            # Write the field
            grb.write_to_file(sections[sn].rh.container.iodesc())
            # Next field (if any)
            grb = gribs.iter_messages(headers_only=False)
    finally:
        for sec in sections.values():
            sec.rh.container.close()

    # Summary
    if sections:
        logger.info(
            "%d new sections created. See details below:", len(sections)
        )
        for i, sec in enumerate(
            sorted(sections.values(), key=lambda s: s.rh.resource.variable)
        ):
            sec.rh.quickview(nb=i)
