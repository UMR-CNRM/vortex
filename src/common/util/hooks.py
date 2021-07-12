# -*- coding: utf-8 -*-

"""
Some useful hooks.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import functools

from bronx.fancies import loggers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def update_namelist(t, rh, *completive_rh):
    """Update namelist with resource handler(s) given in **completive_rh**."""
    touched = False
    for crh in completive_rh:
        if not isinstance(crh, (list, tuple)):
            crh = [crh, ]
        for arh in crh:
            logger.info('Merging: {!r} :\n{:s}'.format(arh.container,
                                                       arh.contents.dumps()))
            rh.contents.merge(arh.contents)
            touched = True
    if touched:
        rh.save()


def concatenate(t, rh, *rhlist):
    """Concatenate *rhlist* after *rh*."""
    blocksize = 32 * 1024 * 1024  # 32Mb
    rh.container.close()
    with rh.container.iod_context():
        myfh = rh.container.iodesc(mode='ab')
        for crh in rhlist:
            if not isinstance(crh, (list, tuple)):
                crh = [crh, ]
            for arh in crh:
                logger.info('Appending %s to self.', str(arh.container))
                with arh.container.iod_context():
                    afh = arh.container.iodesc(mode='rb')
                    stuff = afh.read(blocksize)
                    while stuff:
                        myfh.write(stuff)
                        stuff = afh.read(blocksize)


def insert_cutoffs(t, rh, rh_cutoff_source, fuse_per_obstype=False):
    """Read the cutoff from *rh_cutoff_source* and feed them into *rh*.

    If *fuse_per_obstype* is ``True``, the latest cutoff of a given obstype
    will be used for all the occurences of this obstype.
    """
    import vortex.tools.listings
    assert vortex.tools.listings
    if rh_cutoff_source.container.actualfmt == 'bdmbufr_listing':
        c_disp_callback = functools.partial(
            rh_cutoff_source.contents.data.cutoffs_dispenser,
            fuse_per_obstype=fuse_per_obstype
        )
    else:
        raise RuntimeError("Incompatible < {!s} > ressource handler".format(rh_cutoff_source))
    # Fill the gaps in the original request
    rh.contents.add_cutoff_info(c_disp_callback())
    # Actually save the result to file
    rh.save()
