#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage of EPyGrAM package.

When loaded, this module discards any FootprintBase resource collected as a container
in EPyGrAM package.
"""

import footprints
logger = footprints.loggers.getLogger(__name__)

try:
    import epygram
except ImportError:
    pass
import numpy

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
