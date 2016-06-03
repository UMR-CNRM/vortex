#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Some convenient functions that may simplify scripts
"""

from collections import defaultdict

import footprints as fp

logger = fp.loggers.getLogger(__name__)


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
        raise ValueError('At least one resource handler have to be provided')
    # Just in case min_items is not an int...
    min_items = int(min_items)

    # Create a flat ResourceHandlers list (rhandlers may consists of lists)
    flat_rhlist = []
    flat_rhmandatory = []
    for inlist, outlist in ((rhandlers, flat_rhlist),
                            (kwargs.pop('mandatory', []), flat_rhmandatory),):
        for rh in inlist:
            if isinstance(rh, list) or isinstance(rh, tuple):
                outlist.extend(rh)
            else:
                outlist.append(rh)

    # Check mandatory
    if not all([rh.check() for rh in flat_rhmandatory]):
        raise InputCheckerError("Some of the mandatory resources are missing.")

    # Extract the group informations for each of the resource handlers
    rhgroups = defaultdict(list)
    for rh in flat_rhlist:
        keylist = list()
        for key in grouping_keys:
            value = rh.wide_key_lookup(key, exports=True)
            keylist.append(value)
        rhgroups[tuple(keylist)].append(rh)

    # Check call
    outputlist = list()
    #  The keys are sorted so that results remains reproducible
    for grouping_values in sorted(rhgroups.iterkeys()):
        if all([rh.check() for rh in rhgroups[grouping_values]]):
            outputlist.append(fp.stdtypes.FPDict({k: v for k, v in zip(grouping_keys, grouping_values)}))
            logger.info("Group (%s): All the input files are accounted for.", str(outputlist[-1]))

    # Enforce min_items
    if len(outputlist) < min_items:
        raise InputCheckerError("The number of input groups is too small " +
                                "({:d} < {:d})".format(len(outputlist), min_items))

    return fp.stdtypes.FPList(outputlist)


def members_input_checker(min_items, *rhandlers, **kwargs):
    """
    This is a shortcut for the generic_input_checher: only the member number is
    considered and the return values corresponds to a list of members.
    """
    mlist = [desc['member'] for desc in generic_input_checker(('member', ), min_items,
                                                              *rhandlers, **kwargs)]
    return fp.stdtypes.FPList(sorted(mlist))


def colorfull_input_checker(min_items, *rhandlers, **kwargs):
    """
    This is a shortcut for the generic_input_checher: it returns a list of
    dictionaries that described the available data.
    """
    return generic_input_checker(('vapp', 'vconf', 'cutoff', 'date', 'member'),
                                 min_items, *rhandlers, **kwargs)
