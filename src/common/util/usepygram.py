#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage of EPyGrAM package.

When loaded, this module discards any FootprintBase resource collected as a container
in EPyGrAM package.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

from bronx.stdtypes.date import Date, Time, Period
from bronx.syntax.externalcode import ExternalCodeImportChecker
import footprints
from footprints import proxy as fpx

from vortex import sessions
from vortex.data.contents import MetaDataReader

logger = footprints.loggers.getLogger(__name__)

epygram_checker = ExternalCodeImportChecker('epygram')
with epygram_checker as ec_register:
    import epygram  # @UnusedImport
    ec_register.update(version=epygram.__version__)
    logger.info('Epygram %s loaded.', str(epygram.__version__))


footprints.proxy.containers.discard_package('epygram', verbose=False)

__all__ = []


@epygram_checker.disabled_if_unavailable
def clone_fields(datain, dataout, sources, names=None, value=None, pack=None, overwrite=False):
    """Clone any existing fields ending with``source`` to some new field."""
    # Prepare sources names
    if not isinstance(sources, (list, tuple, set)):
        sources = [sources, ]
    sources = [source.upper() for source in sources]
    # Prepare output names
    if names is None:
        names = sources
    else:
        if not isinstance(names, (list, tuple, set)):
            names = [names, ]
        names = [name.upper().replace(' ', '.') for name in names]
    # Fill the sources list if necessary
    if len(sources) == 1 and len(names) > 1:
        sources *= len(names)
    if len(sources) != len(names):
        raise ValueError('Sizes of sources and names do not fit the requirements.')

    tablein = datain.listfields()
    tableout = dataout.listfields()
    addedfields = 0

    # Look for the input fields,
    for source, name in zip(sources, names):
        fx = None
        comprpack = None
        for fieldname in [ x for x in sorted(tablein) if x.endswith(source) ]:
            newfield = fieldname.replace(source, '') + name
            if not overwrite and newfield in tableout:
                logger.warning('Field <%s> already in output file', newfield)
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
                    dataout.open(openmode='a')
                # Actually add the new field
                logger.info('Add field %s pack=%s' % (fy.fid, comprpack))
                dataout.writefield(fy, compression=comprpack)
                addedfields += 1

    if addedfields:
        dataout.close()
    return addedfields


def epy_env_prepare(t):
    localenv = t.sh.env.clone()
    localenv.verbose(True, t.sh)
    if localenv.OMP_NUM_THREADS is None:
        localenv.OMP_NUM_THREADS = 1
    localenv.update(
        LFI_HNDL_SPEC = ':1',
        DR_HOOK_SILENT  = 1,
        DR_HOOK_NOT_MPI = 1,
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
            clone_fields(rh.contents.data, rh.contents.data,
                         fieldsource, names=fieldtarget, value=constvalue,
                         pack=pack)
    else:
        logger.warning('Try to add field on a missing resource <%s>',
                       rh.container.localpath())


@epygram_checker.disabled_if_unavailable
def copyfield(t, rh, rhsource, fieldsource, fieldtarget, pack=None):
    """Provider hook for copying fields between FA files (but do not overwrite existing fields)."""
    if rh.container.exists():
        with epy_env_prepare(t):
            clone_fields(rhsource.contents.data, rh.contents.data,
                         fieldsource, fieldtarget, pack=pack)
    else:
        logger.warning('Try to copy field on a missing resource <%s>',
                       rh.container.localpath())


@epygram_checker.disabled_if_unavailable
def overwritefield(t, rh, rhsource, fieldsource, fieldtarget, pack=None):
    """Provider hook for copying fields between FA files (overwrite existing fields)."""
    if rh.container.exists():
        with epy_env_prepare(t):
            clone_fields(rhsource.contents.data, rh.contents.data,
                         fieldsource, fieldtarget, overwrite=True, pack=pack)
    else:
        logger.warning('Try to copy field on a missing resource <%s>',
                       rh.container.localpath())


class EpygramMetadataReader(MetaDataReader):

    _abstract = True
    _footprint = dict(
        info = 'Abstract MetaDataReader for formats handled by epygram',
    )

    def _do_delayed_init(self):
        epyf = self._content_in
        if not epyf.isopen:
            epyf.open()
        date_epy, term_epy = self._process_epy(epyf)
        self._datahide = {
            'date': Date(date_epy) if date_epy else date_epy,
            'term': Time(hour=int(term_epy.total_seconds() / 3600),
                         minute=int((term_epy.total_seconds() / 60)) % 60)
        }

    def _process_epy(self, epyf):
        """Abstract method that does the actual processing using epygram."""
        raise NotImplementedError("Abstract method")


@epygram_checker.disabled_if_unavailable
class FaMetadataReader(EpygramMetadataReader):

    _footprint = dict(
        info = 'MetaDataReader for the FA file format',
        attr = dict(
            format = dict(
                values = ('FA',)
            )
        )
    )

    def _process_epy(self, epyf):
        # Just call the epygram function !
        with epy_env_prepare(sessions.current()):
            return epyf.validity.getbasis(), epyf.validity.term()


@epygram_checker.disabled_if_unavailable(version='1.0.0')
class GribMetadataReader(EpygramMetadataReader):

    _footprint = dict(
        info = 'MetaDataReader for the GRIB file format',
        attr = dict(
            format = dict(
                values = ('GRIB',)
            )
        )
    )

    def _process_epy(self, epyf):
        # Loop over the fields and check the unicity of date/term
        bundle = set()
        with epy_env_prepare(sessions.current()):
            epyfld = epyf.iter_fields(getdata=False)
            while epyfld:
                bundle.add((epyfld.validity.getbasis(), epyfld.validity.term()))
                epyfld = epyf.iter_fields(getdata=False)
        if len(bundle) > 1:
            logger.error("The GRIB file contains fileds with different date and terms.")
        if len(bundle) == 0:
            logger.warning("The GRIB file doesn't contains any fields")
            return None, 0
        else:
            return bundle.pop()


@epygram_checker.disabled_if_unavailable(version='1.2.11')
def mk_pgdfa923_from_pgdlfi(t, rh_pgdlfi, nam923blocks,
                            outname=None,
                            fieldslist=None,
                            field_prefix='S1D_',
                            pack=None):
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
        fldout = fpx.fields.almost_clone(fld,
                                         geometry=geom,
                                         fid={'FA': field_prefix + fld.fid['LFI']})
        fldout.setdata(fld.data[1:-1, 1:-1])
        return fldout

    if fieldslist is None:
        fieldslist = ['ZS', 'COVER001', 'COVER002']
    if pack is None:
        pack = {'KNGRIB': -1}
    if outname is None:
        outname = rh_pgdlfi.container.abspath + '.fa923'
    if not t.sh.path.exists(outname):
        with epy_env_prepare(t):
            pgdin = fpx.dataformats.almost_clone(rh_pgdlfi.contents.data,
                                                 true3d=True)
            geom, spgeom = dm.build.build_geom_from_e923nam(nam923blocks)  # TODO: Arpege case
            validity = epygram.base.FieldValidity(date_time=Date(1994, 5, 31, 0),  # Date of birth of ALADIN
                                                  term=Period(0))
            pgdout = epygram.formats.resource(filename=outname,
                                              openmode='w',
                                              fmt='FA',
                                              processtype='initialization',
                                              validity=validity,
                                              geometry=geom,
                                              spectral_geometry=spgeom)
            for f in fieldslist:
                fldout = sfxlfi2fa_field(pgdin.readfield(f), geom)
                pgdout.writefield(fldout, compression=pack)
    else:
        logger.warning('Try to create an already existing resource <%s>',
                       outname)


@epygram_checker.disabled_if_unavailable(version='1.0.0')
def empty_fa(t, rh, empty_name):
    """
    Create an empty FA file with fieldname **empty_name**,
    creating header from given existing FA resource handler **rh**.

    :return: the empty epygram resource, closed
    """
    if rh.container.exists():
        with epy_env_prepare(t):
            rh.contents.data.open()
            assert not t.sh.path.exists(empty_name), \
                'Empty target filename already exist: {}'.format(empty_name)
            e = epygram.formats.resource(empty_name, 'w', fmt='FA',
                                         headername=rh.contents.data.headername,
                                         validity=rh.contents.data.validity,
                                         processtype=rh.contents.data.processtype,
                                         cdiden=rh.contents.cdiden)
            e.close()
            rh.contents.data.close()
            return e
    else:
        raise IOError('Try to copy header from a missing resource <%s>',
                      rh.container.localpath())


@epygram_checker.disabled_if_unavailable(version='1.0.0')
def geopotentiel2zs(t, rh, rhsource, pack=None):
    """Copy surface geopotential from clim to zs in PGD."""
    from bronx.meteo.constants import g0
    if rh.container.exists():
        with epy_env_prepare(t):
            orog = rhsource.contents.data.readfield('SURFGEOPOTENTIEL')
            orog.operation('/', g0)
            orog.fid['FA'] = 'SFX.ZS'
            rh.contents.data.close()
            rh.contents.data.open(openmode='a')
            rh.contents.data.writefield(orog, compression=pack)
    else:
        logger.warning('Try to copy field on a missing resource <%s>',
                       rh.container.localpath())
