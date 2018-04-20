#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
General purpose functions that can be used in conjunction with the
:class:`~vortex.data.stores.FunctionStore`.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from footprints import proxy as fpx

from vortex.data.stores import FunctionStoreCallbackError
from vortex.tools.env import vartrue
from vortex import sessions
from . import helpers

#: No automatic export
__all__ = []


def mergecontents(options):
    """
    Merge the DataContent's of the Section objects designated by the
    *role* option.

    An additional *sort* option may be provided if the resulting merged file
    like object needs to be sorted.

    :param options: The only argument is a dictionary that contains all the options
                    passed to the store plus anything from the query part of the URI.

    :return: Content of the desired local file/container

    :rtype: A file like object
    """
    todo = options.get('role', None)
    sort = vartrue.match(options.get('sort', ['false', ]).pop())
    if todo is not None:
        ctx = sessions.current().context
        sections = list()
        for a_role in todo:
            sections.extend(ctx.sequence.filtered_inputs(role=a_role))
        newcontent = helpers.merge_contents(sections)
        if sort:
            newcontent.sort()
    else:
        raise FunctionStoreCallbackError('At least one *role* option must be provided')
    # Create a Virtual container and dump the new content inside it
    virtualcont = fpx.container(incore=True)
    newcontent.rewrite(virtualcont)
    return virtualcont
