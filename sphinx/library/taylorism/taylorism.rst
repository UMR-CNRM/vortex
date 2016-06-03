:mod:`taylorism` --- Framework for parallelisation of tasks
===========================================================

:Release: |version_taylorism|
:Date: |today|

.. automodule:: taylorism
   :synopsis: Framework for parallelisation of tasks

Functions
---------

.. autofunction:: run_as_server
.. autofunction:: batch_main

Actors
------

.. autoclass:: Boss
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Worker
   :show-inheritance:
   :members:
   :member-order: alphabetical

:mod:`taylorism.schedulers` --- Contains classes for Schedulers
===============================================================

.. automodule:: taylorism.schedulers
   :synopsis: Contains classes for Schedulers.
   
.. autoclass:: BaseScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical
.. autoclass:: LaxistScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical
.. autoclass:: MaxThreadsScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical
.. autoclass:: MaxMemoryScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical
.. autoclass:: SingleOpenFileScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical

:mod:`taylorism.examples` --- Examples using the taylorism package
==================================================================

Examples
--------

.. automodule:: taylorism.examples
   :synopsis: Basic, illustrative examples of use.

.. autoclass:: Sleeper
   :members:
   :private-members: _task
     
.. autofunction:: sleepers_example_program
