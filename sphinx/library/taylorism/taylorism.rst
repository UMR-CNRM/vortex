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

Abstract Scheduler Classes
--------------------------
 
.. autoclass:: BaseScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: NewLimitedScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical

   
Generic Scheduler Classes
-------------------------
   
.. autoclass:: NewLaxistScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: NewMaxThreadsScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: NewMaxMemoryScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: NewSingleOpenFileScheduler
   :show-inheritance:
   :members:
   :member-order: alphabetical


Backward-Compatibility Classes
------------------------------

.. autoclass:: _AbstractOldSchedulerProxy
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
     
.. autofunction:: sleepers_generic_program

.. autofunction:: sleepers_example_laxist

.. autofunction:: sleepers_example_threads

.. autofunction:: sleepers_example_bindedthreads

.. autofunction:: sleepers_example_memory

.. autofunction:: sleepers_example_bindedmemory
