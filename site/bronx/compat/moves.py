#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Compatibility for modules or attributes that move or change their name across versions of Python
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import six

# ABCs are moved from "collections" to "collections.abc" in 3.8
six.add_move(six.MovedModule("collections_abc", "collections", "collections.abc"))
collections_abc = six.moves.collections_abc
collections_abc.__doc__ = "Compatibility module for abstract classes that move from 'collections' " \
                          "in Python 2.7 to 'collections.abc' in Python 3.x (will break in 3.8)"
