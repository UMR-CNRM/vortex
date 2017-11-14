:mod:`vortex.layout.dataflow` --- Sequences of data
===================================================

.. automodule:: vortex.layout.dataflow
   :synopsis: Base components of the internal data flow inside a context

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.4.0


Global descriptors
------------------

.. autoclass:: IntentTuple
   :show-inheritance:
   :members:
   :member-order: alphabetical


.. data:: intent

  Predefined INTENT values IN, OUT and INOUT.

.. autoclass:: IXOTuple
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. data:: ixo

  Predefined IXO sequence values INPUT, OUTPUT and EXEC.

.. autoclass:: InputsReportStatusTupple
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. data:: InputsReportStatus

  Predefined Statuses for input's reports.

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
