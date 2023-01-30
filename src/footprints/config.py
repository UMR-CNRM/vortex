"""
Footprint dynamic configuration.
"""

from bronx.fancies import loggers
from bronx.patterns import getbytag
from bronx.stdtypes import dictionaries

from . import reporting

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# Module interface

def get(**kw):
    """Return actual setup object matching description."""
    return FootprintSetup(**kw)


def keys():
    """Return the list of current setup names."""
    return FootprintSetup.tag_keys()


def values():
    """Return the list of current setup values."""
    return FootprintSetup.tag_values()


def items():
    """Return the items for all the setups available."""
    return FootprintSetup.tag_items()


def add2proxies(c, **kw):
    """
    Add to default or specified setup object (according to ``kw`` and its ``tag`` value)
    the current collector ``c`` as a reference to existing proxies.
    """
    setup = FootprintSetup(**kw)
    for p in setup.proxies:
        setattr(p, c.tag, c.load)
        setattr(p, c.tag + 's', c)


# Constants

NO_REPORTING = 0
ONERROR_REPORTING = 1
LIGHT_REPORTING = 2
FULL_REPORTING = 3

RAW_REPORTINGSTYLE = 0
FLAT_REPORTINGSTYLE = 1
FACTORIZED1_REPORTINGSTYLE = 2
FACTORIZED2_REPORTINGSTYLE = 3

DFLT_MAXLEN_LIGHT_REPORTING = 100


# Base class

class FootprintSetup(getbytag.GetByTag):
    """Defines some defaults and external tools."""

    def __init__(self, docstrings=1, extended=True, fastmode=False,
                 fatal=True, shortnames=False, fastkeys=('kind',),
                 callback=None, defaults=None, proxies=None,
                 report=ONERROR_REPORTING, lreport_len=DFLT_MAXLEN_LIGHT_REPORTING,
                 report_style=RAW_REPORTINGSTYLE, nullreport=reporting.NullReport()):
        """Initialisation of a simple footprint setup driver."""
        self._extended = bool(extended)
        self.docstrings = docstrings
        self.shortnames = bool(shortnames)
        self.fatal = bool(fatal)
        self.report = report
        self.lreport_len = lreport_len
        self.report_style = report_style
        self.nullreport = nullreport
        self.fastmode = bool(fastmode)
        self.fastkeys = tuple(fastkeys)
        self.callback = callback

        if proxies is None:
            self.proxies = set()
        else:
            self.proxies = set(proxies)

        self._defaults = dictionaries.LowerCaseDict()
        if defaults is not None:
            self._defaults.update(defaults)
            logger.warning('New FootprintSetup')

    def __call__(self, **kw):
        if kw:
            initvalues = self.as_dict()
            initvalues.update(kw)
            thesetup = self.__class__(**initvalues)
        else:
            thesetup = self
        thesetup.info()
        return thesetup

    def as_dict(self):
        """Return a standalone dictionary or current setup attributes."""
        return {k.lstrip('_'): v for k, v in self.__dict__.items()}

    def info(self):
        """Summary of actual settings."""
        for k, v in sorted(self.as_dict().items()):
            print(k.ljust(12), ':', v)

    def add_proxy(self, obj, clear=False):
        """
        Populate an ``obj`` with references to active collectors and load methods
        so that it could behave like a static proxy.
        """
        if isinstance(obj, object):
            from . import collectors
            self.proxies.add(obj)
            for k, v in collectors.items():
                if clear or not hasattr(obj, k):
                    setattr(obj, k, v.load)
                if clear or not hasattr(obj, k + 's'):
                    setattr(obj, k + 's', v)
        else:
            logger.error('Could not populate a non-module or non-instance object: %s', obj)
            raise ValueError('Not a module nor an object instance: {!s}'.format(obj))

    def _get_defaults(self):
        """Property getter for footprints defaults."""
        return self._defaults

    def _set_defaults(self, *args, **kw):
        """Property setter for current defaults environment of the footprint resolution."""
        self._defaults = dictionaries.LowerCaseDict()
        self._defaults.update(*args, **kw)

    defaults = property(_get_defaults, _set_defaults)

    def _get_extended(self):
        """Property getter to ``extended`` switch."""
        return self._extended

    def _set_extended(self, switch):
        """Property setter to ``extended`` mode for footprint defaults."""
        if switch is not None:
            self._extended = bool(switch)

    extended = property(_get_extended, _set_extended)

    def extras(self):
        """
        Return a dictionary of extra key-value pairs
        according to a callback function given as an attribute.
        """
        if self.callback:
            cb = self.callback
            return cb()
        else:
            return dict()
