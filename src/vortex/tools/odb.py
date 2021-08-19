# -*- coding: utf-8 -*-

"""
Backward compatibility module.

Please use :mod:`vortex.tools.folder` and :mod:`common.tools.odb` instead.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

# Backward compatibility...
from . import folder

OdbShell = folder.OdbShell
