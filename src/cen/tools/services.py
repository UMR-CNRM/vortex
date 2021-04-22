#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module contains the services specifically needed by Olive.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.services import AbstractRdTemplatedMailService

#: Export nothing
__all__ = []


class CenMailService(AbstractRdTemplatedMailService):
    """Class responsible for sending predefined mails.

    This class should not be called directly.
    """

    _footprint = dict(
        info = 'CEN predefined mail services class',
        attr = dict(
            kind = dict(
                values   = ['cenmail'],
            ),
        )
    )

    _TEMPLATES_SUBDIR = 'cenmails'
