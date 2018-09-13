:mod:`vortex.tools.delayedactions` --- Advanced tools that deals with delayed actions
=====================================================================================

.. automodule:: vortex.tools.delayedactions
   :synopsis: Advanced tools that deals with delayed actions

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 1.4.1

.. autodata:: __all__


Delayed action's hubs classes
-----------------------------

Actual classes
**************

.. autoclass:: PrivateDelayedActionsHub
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: DelayedActionsHub
   :show-inheritance:
   :members:
   :member-order: alphabetical

Access method
*************

.. autofunction:: get_hub


Delayed action's handlers
-------------------------

Abstract classes
****************

.. autoclass:: AbstractDelayedActionsHandler
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: AbstractFileBasedDelayedActionsHandler
   :show-inheritance:
   :members:
   :member-order: alphabetical

Actual handlers classes
***********************

.. autoclass:: RawFtpDelayedGetHandler
   :show-inheritance:
   :members:
   :member-order: alphabetical

Example code
************
.. autoclass:: DemoSleepDelayedActionHandler
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autofunction:: demo_sleeper_function


Delayed actions description
---------------------------

.. autoclass:: DelayedActionStatusTuple
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autodata:: d_action_status

.. autoclass:: DelayedAction
   :show-inheritance:
   :members:
   :member-order: alphabetical
