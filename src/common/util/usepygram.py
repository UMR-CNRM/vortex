#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage of EPyGrAM package.

When loaded, this module discards any FootprintBase resource collected as a container
in EPyGrAM package.
"""

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.contents import MetaDataReader
from vortex.tools.date import Date, Time

try:
    import epygram
except ImportError:
    pass

footprints.proxy.containers.discard_package('epygram')

__all__ = []


def clone_fields(data, source, name='NEWFIELD', value=0., pack=None):
    """Clone any existing fields ending with``source`` to some new constant field."""
    name = name.upper().replace(' ', '.')
    source = source.upper()
    table = data.listfields()
    addfields = list()

    for fieldname in [ x for x in sorted(table) if x.endswith(source) ]:
        newfield = fieldname.replace(source, '') + name
        if newfield in table:
            logger.warning('Field <%s> already in file', newfield)
        else:
            fx = data.readfield(fieldname)
            fy = fx.clone({ x:newfield for x in fx.fid.keys() })
            fy.data.fill(value)
            comprpack = data.fieldscompression.get(fieldname)
            if pack is not None:
                comprpack.update(pack)
            addfields.append((fy, comprpack))

    if addfields:
        data.close()
        data.open(openmode='a')
        for newfield, pack in addfields:
            logger.info('Add field %s pack=%s' % (newfield.fid, pack))
            data.writefield(newfield, compression=pack)

    data.close()

    return len(addfields)


def addfield(t, rh, fieldsource, fieldtarget, constvalue):
    """Provider hook for adding a field through cloning."""
    if rh.container.exists():
        rh.container.updfill(True)
        t.sh.chmod(rh.container.localpath(), 0644)
        localenv = t.sh.env.clone()
        localenv.active(True)
        localenv.verbose(True, t.sh)
        localenv.update(
            LFI_HNDL_SPEC   = ':1',
            DR_HOOK_SILENT  = 1,
            DR_HOOK_NOT_MPI = 1,
        )
        clone_fields(rh.contents.data, fieldsource, name=fieldtarget, value=constvalue)
        localenv.active(False)
    else:
        logger.warning('Try to add field on a missing resource <%s>', rh.container.localpath())


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
        for epyfld in epyf.iter_field(getdata=False):
            bundle.add((epyfld.validity.getbasis(), epyfld.validity.term()))
        if len(bundle) > 1:
            logger.error("The GRIB file contains fileds with different date and terms.")
        if len(bundle) == 0:
            logger.warning("The GRIB file doesn't contains any fields")
            return None, 0
        else:
            return bundle[0]
