:mod:`vortex.layout.dataflow` --- Sequences of data
===================================================

.. automodule:: vortex.layout.dataflow
   :synopsis: Base components of the internal data flow inside a context

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.4.0


Global descriptors
------------------

.. autodata:: IntentTuple

.. data:: intent

  Predefined INTENT values IN, OUT and INOUT.

.. autodata:: IXOTuple

.. data:: ixo

  Predefined IXO sequence values INPUT, OUTPUT and EXEC.


Interface
---------

.. autofunction:: stripargs_section


Exceptions
----------

.. autoclass:: SectionFatalError
   :show-inheritance:


Classes
-------

.. autoclass:: Section
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Sequence
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: SequenceInputsReport
   :show-inheritance:
   :members:
   :member-order: alphabetical
 
.. autoclass:: LocalTracker
   :show-inheritance:
   :members:
   :member-order: alphabetical
 
.. autoclass:: LocalTrackerEntry
   :show-inheritance:
   :members:
   :member-order: alphabetical
