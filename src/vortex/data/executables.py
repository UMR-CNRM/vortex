#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from resources import Resource
from vortex.syntax.stdattrs import a_model
from vortex.util.config import JacketConfigParser


class Jacket(object):

    def __init__(self, afile=None):
        if afile:
            self.config = JacketConfigParser(afile)
            self.virtual = False
        else:
            self.virtual = True
        self._initfile = afile

    def as_dump(self):
        return "{0:s}.{1:s}(file={2:s})".format(
            self.__module__,
            self.__class__.__name__,
            repr(self._initfile)
        )


class Executable(Resource):
    """Abstract class for resources that could be executed."""

    _abstract = True
    _footprint = dict(
        info = 'Miscellaneaous executable resource',
        attr = dict(
            cycle = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            )
        )
    )


class Script(Executable):
    """Basic interpreted executable associated to a specific language."""

    _footprint = dict(
        attr = dict(
            rawopts = dict(
                optional = True,
                default  = '',
            ),
            language = dict(
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
                optional = True,
            ),
            static = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
            jacket = dict(
                type = Jacket,
                optional = True,
                default  = Jacket()
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
