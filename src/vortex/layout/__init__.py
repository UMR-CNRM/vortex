"""
Package dealing with various aspects of the VORTEX session organisation/layout.

It provides modules to keep track of all the input/output data handled during
a VORTEX session:

    * the :mod:`dataflow` module defines the :class:`~dataflow.Section` class
      and all the necessary class to gather and manipulate :class:`~dataflow.Section`
      objects ;
    * the :mod:`contexts` module is dedicated to the :class:`~contexts.Context`
      class that provide a logical separation within VORTEX sessions. It mantains
      the list of sections and environment variables ;
    * the :mod:`monitor` module defines utility classes to monitor the state of an
      ensemble of :class:`~dataflow.Section` objects.
"""

#: No automatic export
__all__ = []

__tocinfoline__ = "Package that helps organising a VORTEX session."
