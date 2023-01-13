# -*- coding: utf-8 -*-

"""
TNT stands for "The Namelist Tool".

The main objectives of this package is to provide command line tools useful to
work with namelists or pack of namelists (update them, compare them, ...).

The Sphinx documentation of this package is few. However, for end users, the
entry points to this package are the ``tnt.py``, ``tntdiff.py`` and
``tntstack.py`` command line utilities provided in the ``tools`` subdirectory
(or in your ``$PATH`` when ``pip`` is used).
These command line utility are provided with an embedded documentation accessible
with the `-h` option (e.g. ``tnt.py -h``).

The ``tnt.py`` and ``tntstack.py`` command line utilities heavily rely on
directive files. A template of such directive files can be generated using the
``-D`` option (``tnt.py -D`` or ``tntstack.py -D``). The template directives
files are thoroughly documented and should be regarded as documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from . import config
from . import namadapter
from . import util
