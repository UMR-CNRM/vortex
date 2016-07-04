#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage of EPyGrAM package.

When loaded, this module discards any FootprintBase resource collected as a container
in EPyGrAM package.
"""

import sys
from distutils.version import LooseVersion

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.contents import MetaDataReader
from vortex.tools.date import Date, Time

try:
    import epygram  # @UnusedImport
except ImportError:
    pass

footprints.proxy.containers.discard_package('epygram')

__all__ = []


def is_epygram_available(minimal_version='0.0.0'):
    """Is epygram available ?

    :param str minimal_version: The minimal version we are looking for.
    """
    return (('epygram' in sys.modules) and
            (LooseVersion(epygram.__version__) >= LooseVersion(minimal_version)))


class EpygramUnavailableError(Exception):
    pass


def disabled_if_no_epygram(minimal_version_or_name):
    """This decorator disables the provided object if epygram is not available.

    :param str minimal_version_or_name: The minimal version we are looking for.
    """
    minimal_version = ('0.0.0'
                       if callable(minimal_version_or_name)
                       else minimal_version_or_name)

    def actual_disabled_if_no_epygram(func_or_cls):
        def error_func(*args, **kw):
            raise EpygramUnavailableError()
        return (func_or_cls
                if is_epygram_available(minimal_version)
                else error_func)

    if callable(minimal_version_or_name):
        return actual_disabled_if_no_epygram(minimal_version_or_name)
    return actual_disabled_if_no_epygram


@disabled_if_no_epygram
def clone_fields(datain, dataout, sources, names=None, value=None, pack=None):
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
    # aliases
    tablein = datain.listfields()
    tableout = dataout.listfields()
    addfields = list()

    # Look for the input fields,
    for source, name in zip(sources, names):
        for fieldname in [ x for x in sorted(tablein) if x.endswith(source) ]:
            newfield = fieldname.replace(source, '') + name
            if newfield in tableout:
                logger.warning('Field <%s> already in output file', newfield)
            else:
                fx = datain.readfield(fieldname)
                fy = fx.clone({x: newfield for x in fx.fid.keys()})
                if value is not None:
                    fy.data.fill(value)
                comprpack = datain.fieldscompression.get(fieldname)
                if pack is not None:
                    comprpack.update(pack)
                addfields.append((fy, comprpack))

    # Write output fields
    if addfields:
        dataout.close()
        dataout.open(openmode='a')
        for newfield, pack in addfields:
            logger.info('Add field %s pack=%s' % (newfield.fid, pack))
            dataout.writefield(newfield, compression=pack)

    dataout.close()

    return len(addfields)


def _env_prepare(t):
    localenv = t.sh.env.clone()
    localenv.active(True)
    localenv.verbose(True, t.sh)
    if localenv.OMP_NUM_THREADS is None:
        localenv.OMP_NUM_THREADS = 1
    localenv.update(
        DR_HOOK_SILENT  = 1,
        DR_HOOK_NOT_MPI = 1,
    )
    return localenv


@disabled_if_no_epygram
def addfield(t, rh, fieldsource, fieldtarget, constvalue):
    """Provider hook for adding a field through cloning."""
    if rh.container.exists():
        localenv = _env_prepare(t)
        clone_fields(rh.contents.data, rh.contents.data,
                     fieldsource, names=fieldtarget, value=constvalue)
        localenv.active(False)
    else:
        logger.warning('Try to add field on a missing resource <%s>',
                       rh.container.localpath())


@disabled_if_no_epygram
def copyfield(t, rh, rhsource, fieldsource, fieldtarget):
    """Provider hook for copying fields between FA files."""
    if rh.container.exists():
        localenv = _env_prepare(t)
        clone_fields(rhsource.contents.data, rh.contents.data, fieldsource, fieldtarget)
        localenv.active(False)
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


@disabled_if_no_epygram
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
        return epyf.validity.getbasis(), epyf.validity.term()


@disabled_if_no_epygram('1.0.0')
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
