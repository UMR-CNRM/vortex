:mod:`vortex.layout.dataflow` --- Sequences of data
===================================================

.. automodule:: vortex.layout.dataflow
   :synopsis: Base components of the internal data flow inside a context

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.4.0


Global descriptors
------------------

.. data:: intent

  Predefined INTENT values IN, OUT and INOUT.
  
.. data:: ixo

  Predefined IXO sequence values INPUT, OUTPUT and EXEC.

Interface
---------

.. autofunction:: stripargs_section

Classes
-------

.. autoclass:: Section
   :show-inheritance:
   :members:
   :member-order: bysource

.. autoclass:: Sequence
   :show-inheritance:
   :members:
   :member-order: bysource

