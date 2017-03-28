#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints

from resources import Resource
from vortex.syntax.stdattrs import a_model
from vortex.util.config import JacketConfigParser


class Jacket(object):
    """The class definition of in and out resources from a given executable."""
    def __init__(self, afile=None):
        if afile:
            self.config = JacketConfigParser(afile)
            self.virtual = False
        else:
            self.virtual = True
        self._initfile = afile

    def as_dump(self):
        return "file={!r}".format(self._initfile)

    def export_dict(self):
        return self._initfile


class Executable(Resource):
    """Abstract class for resources that could be executed."""

    _abstract = True
    _footprint = dict(
        info = 'Miscellaneaous executable resource',
        attr = dict(
            cycle = dict(
                info     = "Any kind of cycle name",
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            kind = dict(
                info        = "The resource's kind.",
                doc_zorder  = 90,
            ),
            nativefmt = dict(
                doc_visibility = footprints.doc.visibility.GURU,
            ),
            clscontents = dict(
                doc_visibility = footprints.doc.visibility.GURU,
            )
        )
    )


class Script(Executable):
    """Basic interpreted executable associated to a specific language."""

    _footprint = dict(
        attr = dict(
            rawopts = dict(
                info     = "Options that will be passed directly to the script",
                optional = True,
                default  = '',
            ),
            language = dict(
                info     = "The programming language",
                values   = ['perl', 'python', 'ksh', 'bash', 'sh'],
            ),
            kind = dict(
                optional = True,
                default  = 'script',
                values   = ['script'],
            )
        )
    )

    @property
    def realkind(self):
        return 'script'

    def command_line(self, **opts):
        """Returns optional attribute :attr:`rawopts`."""
        if self.rawopts is None:
            return ''
        else:
            return self.rawopts


class Binary(Executable):
    """Basic compiled executable."""
    _abstract = True
    _footprint = dict(
        attr = dict(
            compiler = dict(
                info     = "The compiler label.",
                optional = True,
            ),
            static = dict(
                info     = "Statically linked binary.",
                type     = bool,
                optional = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            jacket = dict(
                type            = Jacket,
                optional        = True,
                default         = Jacket(),
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            )
        )
    )

    @property
    def realkind(self):
        return 'binary'


class BlackBox(Binary):
    """Binary resource with explicit command line options."""

    _footprint = dict(
        attr = dict(
            binopts = dict(
                info     = "Options that will be passed directly to the binary",
                optional = True,
                default  = '',
            ),
            kind = dict(
                values   = ['binbox', 'blackbox'],
                remap    = dict(binbox = 'blackbox'),
            ),
        )
    )

    def command_line(self, **opts):
        """Returns current attribute :attr:`binopts`."""
        return self.binopts


class NWPModel(Binary):
    """Base class for any Numerical Weather Prediction Model."""

    _abstract = True
    _footprint = dict(
        info = 'NWP Model',
        attr = dict(
            model = a_model,
            kind = dict(
                values = ['nwpmodel']
            )
        )
    )

    @property
    def realkind(self):
        return 'nwpmodel'

    def command_line(self, **opts):
        """Abstract method."""
        return ''


class OceanographicModel(Binary):
    """Base class for any Oceanographic Model."""

    _abstract = True
    _footprint = dict(
        info = 'Oceanographic Model',
        attr = dict(
            model = a_model,
            kind = dict(
                values = ['oceanmodel']
            )
        )
    )

    @property
    def realkind(self):
        return 'oceanmodel'

    def command_line(self, **opts):
        """Abstract method."""
        return ''


class SurfaceModel(Binary):

    _abstract  = True
    _footprint = dict(
        info = 'Model used for the Safran-Surfex-Mepra chain.',
        attr = dict(
            model = a_model,
            kind  = dict(
                values = ['snowmodel']
            ),
        ),
    )
