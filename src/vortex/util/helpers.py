"""
Some convenient functions that may simplify scripts
"""

from collections import defaultdict

from bronx.compat import random
from bronx.fancies import loggers
from bronx.stdtypes.date import Date
import footprints as fp

from vortex.data.handlers import Handler
from vortex.layout.dataflow import Section
from vortex import sessions

logger = loggers.getLogger(__name__)


class InputCheckerError(Exception):
    """Exception raised when the Input checking process fails."""

    pass


def generic_input_checker(grouping_keys, min_items, *rhandlers, **kwargs):
    """
    Check which input resources are present.

    First, the resource handlers (*rhandlers* attribute) are split
    into groups based on the values of their properties (only the properties
    specified in the *grouping_keys* attribute are considered).

    Then, for each group, the **check** method is called upon the resource
    handlers. The group description is returned only if the **check** call
    succeed for all the members of the group.

    If the number of groups successfully checked is lower than *min_items*,
    an :class:`InputCheckerError` exception is raised.
    """

    if len(rhandlers) == 0:
        raise ValueError("At least one resource handler have to be provided")
    # Just in case min_items is not an int...
    min_items = int(min_items)

    # Create a flat ResourceHandlers list (rhandlers may consists of lists)
    flat_rhlist = []
    flat_rhmandatory = []
    for inlist, outlist in (
        (rhandlers, flat_rhlist),
        (kwargs.pop("mandatory", []), flat_rhmandatory),
    ):
        for rh in inlist:
            if isinstance(rh, list) or isinstance(rh, tuple):
                outlist.extend(rh)
            else:
                outlist.append(rh)

    # Extract the group informations for each of the resource handlers
    rhgroups = defaultdict(list)
    for rh in flat_rhlist:
        keylist = list()
        for key in grouping_keys:
            value = rh.wide_key_lookup(key, exports=True, fatal=False)
            keylist.append(value)
        rhgroups[tuple(keylist)].append(rh)

    candidateslist = [
        fp.stdtypes.FPDict(
            {k: v for k, v in zip(grouping_keys, group) if v is not None}
        )
        for group in rhgroups.keys()
    ]

    # Activate FTP connections pooling (for enhanced performances)
    t = sessions.current()
    with t.sh.ftppool():
        # Check mandatory stuff
        mychecks = [(rh, rh.check()) for rh in flat_rhmandatory]
        if not all([acheck[1] for acheck in mychecks]):
            for rh in [acheck[0] for acheck in mychecks if not acheck[1]]:
                logger.error("  Missing location: %s", str(rh.locate()))
            raise InputCheckerError(
                "Some of the mandatory resources are missing."
            )

        # Check call for non-mandatory stuff
        outputlist = list()
        # Is the check real or a delusion ?
        fakecheck = kwargs.pop("fakecheck", False)
        #  The keys are sorted so that results remains reproducible
        for grouping_values in sorted(rhgroups.keys()):
            mychecks = [
                (rh, fakecheck or rh.check())
                for rh in rhgroups[grouping_values]
            ]
            groupid = fp.stdtypes.FPDict(
                {
                    k: v
                    for k, v in zip(grouping_keys, grouping_values)
                    if v is not None
                }
            )
            if all([acheck[1] for acheck in mychecks]):
                outputlist.append(groupid)
                logger.info(
                    "Group (%s): All the input files are accounted for.",
                    str(groupid),
                )
            else:
                logger.warning(
                    "Group (%s): Discarded because some of the input files are missing (see below).",
                    str(groupid),
                )
                for rh in [acheck[0] for acheck in mychecks if not acheck[1]]:
                    logger.warning("  Missing location: %s", str(rh.locate()))

    # Enforce min_items
    if len(outputlist) < min_items:
        raise InputCheckerError(
            "The number of input groups is too small "
            + "({:d} < {:d})".format(len(outputlist), min_items)
        )

    return fp.stdtypes.FPList(outputlist), fp.stdtypes.FPList(candidateslist)


def members_input_checker(min_items, *rhandlers, **kwargs):
    """
    This is a shortcut for the generic_input_checher: only the member number is
    considered and the return values corresponds to a list of members.
    """
    mlist = [
        desc["member"]
        for desc in generic_input_checker(
            ("member",), min_items, *rhandlers, **kwargs
        )[0]
    ]
    return fp.stdtypes.FPList(sorted(mlist))


def colorfull_input_checker(min_items, *rhandlers, **kwargs):
    """
    This is a shortcut for the generic_input_checher: it returns a list of
    dictionaries that described the available data.
    """
    return generic_input_checker(
        ("vapp", "vconf", "experiment", "cutoff", "date", "member"),
        min_items,
        *rhandlers,
        **kwargs,
    )


def merge_contents(*kargs):
    """Automatically merge several DataContents.

    Example:
    .. code-block:: python

        mergedcontent = merge_contents(content1, content2, content3)
        # With a list
        mergedcontent = merge_contents([content1, content2, content3])
        # With a list of ResourceHandlers (e.g. as returned by toolbox.input)
        mergedcontent = merge_contents([rh1, rh2, rh3])
        # With a list of Sections (e.g. as returned by effective_inputs)
        mergedcontent = merge_contents([section1, section2, section3])

    """
    # Expand list or tuple elements
    ctlist = list()
    for elt in kargs:
        if isinstance(elt, (list, tuple)):
            ctlist.extend(elt)
        else:
            ctlist.append(elt)
    # kargs may be a list of resource handlers (as returned by the toolbox)
    if all([isinstance(obj, Handler) for obj in ctlist]):
        ctlist = [obj.contents for obj in ctlist]
    # kargs may be a list of sections
    elif all([isinstance(obj, Section) for obj in ctlist]):
        ctlist = [obj.rh.contents for obj in ctlist]
    # Take the first content as a model for the new object
    newcontent = ctlist[0].__class__()
    newcontent.merge(*ctlist)
    return newcontent


def mix_list(list_elements, date=None, member=None):
    """Mix a list using a determined seed, if member and/or date are present."""
    dateinfo = date if date is None else Date(date)
    memberinfo = member if member is None else int(member)
    rgen = random.Random()
    if (dateinfo is not None) or (memberinfo is not None):
        if dateinfo is not None:
            seed = dateinfo.epoch * 100
        else:
            seed = 9999999
        if memberinfo:
            seed = seed // memberinfo
        logger.debug("The random seed is %s.", seed)
        rgen.seed(seed)
    else:
        logger.info("The random seed not initialised")
    logger.debug(
        "The list of elements is %s.",
        " ".join([str(x) for x in list_elements]),
    )
    result_list_elements = list_elements
    result_list_elements.sort()
    rgen.shuffle(result_list_elements)
    logger.debug(
        "The mixed list of elements is %s.",
        " ".join([str(x) for x in result_list_elements]),
    )
    return result_list_elements
