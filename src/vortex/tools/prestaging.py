#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Advanced tools that deal with resources pre-staging.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from collections import namedtuple

import footprints
from footprints import proxy as fpx
from footprints.dump import lightdump
from footprints.util import Catalog, GetByTag

from vortex.tools.systems import OSExtended

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

#: Definition of a named tuple PrestagingPriorityTuple
PrestagingPriorityTuple = namedtuple('PrestagingPriorityTuple', ['urgent', 'normal', 'low'], verbose=False)

#: Predefined PrestagingPriorities values for urgent, normal and low
prestaging_p = PrestagingPriorityTuple(urgent=99, normal=50, low=0)


# Module Interface
def get_hub(**kw):
    """Return the actual PrestagingHub object matching the *tag* (or create one)."""
    return PrestagingHub(**kw)


class PrestagingTool(footprints.FootprintBase, Catalog):
    """Abstract class that deal with pre-staging for a given storage target."""

    _abstract = True
    _collector = ('prestagingtool',)
    _footprint = dict(
        info = "Abstract class that deal with pre-staging for a given storage target.",
        attr = dict(
            system = dict(
                info = "The current system object",
                type = OSExtended
            ),
            issuerkind = dict(
                info = 'The kind of store issuing the prestaging request'
            ),
            priority = dict(
                info = 'The prestaging request priority',
                type = int,
                values = list(prestaging_p)
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        """Abstract PrestagingTools init."""
        # Call both inits
        Catalog.__init__(self)
        footprints.FootprintBase.__init__(self, *kargs, **kwargs)

    def __str__(self):
        return self.describe(fulldump=False)

    def describe(self, fulldump=False):
        """Print the object's characteristics and content."""
        res = 'PrestagingTool object of class: {:s}\n'.format(self.__class__)
        for k, v in self.footprint_as_shallow_dict().items():
            res += '  * {:s}: {!s}\n'.format(k, v)
        if fulldump:
            res += '\n  * Todo list:\n'
            res += '\n'.join(['    - {:s}'.format(item) for item in self.items()])
        return res

    def flush(self, email=None):
        """Send the prestaging request to the appropriate location."""
        raise NotImplementedError()


class PrivatePrestagingHub(object):
    """
    Manages pre-staging request by forwarding them to the appropriate
    :class:`PrestagingTool` object.

    If no, :class:`PrestagingTool` class is able to handle the pre-staging
    request, just do nothing.

    :note: When calling the :meth:`record` method, the pre-staging request is
        just stored away. To actually request the pre-statging, one must call the
        :meth:`flush` method.
    """

    def __init__(self, sh, email=None):
        self._email = email
        self._sh = sh
        self._prestagingtools = set()

    def record(self, location, priority=prestaging_p.normal, **kwargs):
        """Take into consideration a pre-staging request.

        :param str location: The location of the requested data
        :param int priority: The prestaging request priority
        :param dict kwargs: Any argument that will be used to create the :class:`PrestagingTool` object
        """
        # Prestaging tool descriptions
        myptool_desc = dict(priority=priority, system=self._sh)
        myptool_desc.update(kwargs)
        myptool = None
        # Scan pre-existing prestaging tools to find a suitable one
        for ptool in self._prestagingtools:
            if ptool.footprint_reusable() and ptool.footprint_compatible(myptool_desc):
                logger.debug("Re-usable prestaging tool found: %s", lightdump(myptool_desc))
                myptool = ptool
                break
        # If necessary, create a new one
        if myptool is None:
            myptool = fpx.prestagingtool(_emptywarning=False, **myptool_desc)
            if myptool is not None:
                logger.debug("Fresh prestaging tool created: %s", lightdump(myptool_desc))
                self._prestagingtools.add(myptool)
        # Let's role
        if myptool is None:
            logger.debug("Unable to perform prestaging with: %s", lightdump(myptool_desc))
        else:
            myptool.add(location)

    def _get_ptools(self, priority_threshold=prestaging_p.low):
        todo = set()
        for ptool in self._prestagingtools:
            if ptool.priority >= priority_threshold:
                todo.add(ptool)
        return todo

    def __repr__(self, *args, **kwargs):
        return ('{0:s} | n_prestagingtools={1:d}>'
                .format(super(PrivatePrestagingHub, self).__repr__().rstrip('>'),
                        len(self._prestagingtools)))

    def __str__(self):
        return (repr(self) + "\n\n" +
                "\n\n".join([ptool.describe(fulldump=True) for ptool in self._prestagingtools]))

    def flush(self, priority_threshold=prestaging_p.low):
        """Actually send the pre-staging request to the appropriate location.

        :param int priority: Only requests with a priority >= *priority_threshold*
            will be sent.
        """
        for ptool in self._get_ptools(priority_threshold):
            rc = ptool.flush(email=self._email)
            if rc:
                self._prestagingtools.discard(ptool)
            else:
                logger.error("Something went wrong when flushing the %s prestaging tool", ptool)

    def clear(self, priority_threshold=prestaging_p.low):
        """Erase the pre-staging requests list.

        :param int priority: Only requests with a priority >= *priority_threshold*
            will be deleted.
        """
        for ptool in self._get_ptools(priority_threshold):
            self._prestagingtools.discard(ptool)


class PrestagingHub(PrivatePrestagingHub, GetByTag):
    """
    A subclass of :class:`PrivatePrestagingHub` that using :class:`GetByTag`
    to remain persistent in memory.

    Therefore, a *tag* attribute needs to be specified when building/retrieving
    an object of this class.
    """
    pass