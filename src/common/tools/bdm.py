# -*- coding: utf-8 -*-

"""
Utility classes and function to work with the BDM database.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

#: No automatic export
__all__ = []


class BDMError(Exception):
    """General BDM error."""
    pass


class BDMRequestConfigurationError(BDMError):
    """Specific Transfer Agent configuration error."""
    pass


class BDMGetError(BDMError):
    """Generic BDM get error."""
    pass
