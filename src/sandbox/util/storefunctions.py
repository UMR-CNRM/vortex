#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six

#: No automatic export
__all__ = []


def echofunction(options):
    """Simple example of a function designed to be called by the FunctionStore.

    :param options: The only argument is a dictionary that contains all the options
                    passed to the store plus anything from the query part of the URI.

    :return: Content of the desired local file

    :rtype: A file like object
    """
    outstr = ''
    # Try to find out the name of the local file: more generally, one can
    # access every attributes from the resource handler.
    rhdict = options.get('rhandler', None)
    if rhdict:
        outstr += "localfile: {}\n".format(rhdict.get('container', {}).get('filename', ''))
    else:
        outstr += "no ressource handler her :-(\n"
    # Messages may be added to the query part of the URI
    msgs = options.get('msg', ('Missing :-(',))
    for i, msg in enumerate(msgs):
        outstr += "\nMessage #{:d} is: {:s}\n".format(i, msg)
    # NB: The result have to be a file like object !
    return six.BytesIO(outstr.encode(encoding='utf_8'))
