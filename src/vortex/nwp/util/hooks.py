"""
Some useful hooks.
"""

import collections.abc
import functools

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Period, Time

from ..data.query import StaticCutoffDispenser

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def update_namelist(t, rh, *completive_rh):
    """Update namelist with resource handler(s) given in **completive_rh**."""
    touched = False
    for crh in completive_rh:
        if not isinstance(crh, (list, tuple)):
            crh = [
                crh,
            ]
        for arh in crh:
            logger.info(
                "Merging: {!r} :\n{:s}".format(
                    arh.container, arh.contents.dumps()
                )
            )
            rh.contents.merge(arh.contents)
            touched = True
    if touched:
        rh.save()


def concatenate(t, rh, *rhlist):
    """Concatenate *rhlist* after *rh*."""
    blocksize = 32 * 1024 * 1024  # 32Mb
    rh.container.close()
    with rh.container.iod_context():
        myfh = rh.container.iodesc(mode="ab")
        for crh in rhlist:
            if not isinstance(crh, (list, tuple)):
                crh = [
                    crh,
                ]
            for arh in crh:
                logger.info("Appending %s to self.", str(arh.container))
                with arh.container.iod_context():
                    afh = arh.container.iodesc(mode="rb")
                    stuff = afh.read(blocksize)
                    while stuff:
                        myfh.write(stuff)
                        stuff = afh.read(blocksize)


def insert_cutoffs(t, rh, rh_cutoff_source, fuse_per_obstype=False):
    """Read the cutoff from *rh_cutoff_source* and feed them into *rh*.

    If *fuse_per_obstype* is ``True``, the latest cutoff of a given obstype
    will be used for all the occurences of this obstype.
    """
    # rh_cutoff_source may be a list
    if isinstance(rh_cutoff_source, list):
        if rh_cutoff_source:
            rh_cutoff_source = rh_cutoff_source[0]
        else:
            ValueError("The resource handler's list is empty.")
    # Get the CutoffDispenser
    import vortex.tools.listings

    assert vortex.tools.listings
    if rh_cutoff_source.container.actualfmt == "bdmbufr_listing":
        c_disp_callback = functools.partial(
            rh_cutoff_source.contents.data.cutoffs_dispenser,
            fuse_per_obstype=fuse_per_obstype,
        )
    else:
        raise RuntimeError(
            "Incompatible < {!s} > ressource handler".format(rh_cutoff_source)
        )
    # Fill the gaps in the original request
    rh.contents.add_cutoff_info(c_disp_callback())
    # Actually save the result to file
    rh.save()


def _new_static_cutoff_dispencer(base_date, cutoffs_def):
    def x_period(p):
        try:
            return Period(p)
        except ValueError:
            return Period(Time(p))

    if not isinstance(base_date, Date):
        base_date = Date(base_date)
    if isinstance(cutoffs_def, collections.abc.Mapping):
        cutoffs_def = {
            (k if isinstance(k, Period) else x_period(k)): v
            for k, v in cutoffs_def.items()
        }
        cutoffs = {base_date + k: v for k, v in cutoffs_def.items()}
        c_disp = StaticCutoffDispenser(max(cutoffs.keys()), cutoffs)
    else:
        if not isinstance(cutoffs_def, Period):
            cutoffs_def = x_period(cutoffs_def)
        c_disp = StaticCutoffDispenser(base_date + cutoffs_def)
    return c_disp


def insert_static_cutoffs(t, rh, base_date, cutoffs_def):
    """Compute the cutoff from *cutoffs_def* and feed them into *rh*.

    :param base_date: The current analysis time
    :param cutoffs_def: The cutoff time represented as time offset with respect
                        to *base_date*. *cutoffs_defs* may be a single value or
                        a dictionary. If *cutoffs_def* is a dictionary, it
                        associates a cutoff with a list of `obstypes`.
    """
    # Fill the gaps in the original request
    rh.contents.add_cutoff_info(
        _new_static_cutoff_dispencer(base_date, cutoffs_def)
    )
    # Actually save the result to files
    rh.save()


def arpifs_obs_error_correl_legacy2oops(t, rh):
    """Convert a constant file that contains observation errors correlations."""
    if rh.resource.realkind != "correlations":
        raise ValueError("Incompatible resource: {!s}".format(rh))
    if rh.contents[0].startswith("SIGMAO"):
        logger.warning("Non conversion is needed...")
    else:
        rh.contents[:0] = ["SIGMAO unused\n", "1 1.2\n", "CORRELATIONS\n"]
        rh.save()
