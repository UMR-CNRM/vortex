:mod:`vortex.toolbox` --- Top level interface to the :mod:`vortex` toolbox
==========================================================================

.. automodule:: vortex.toolbox
   :synopsis: Top level functions to basic vortex functionalities

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.1


Toolbox settings
----------------

These are switch that you can change at will. they will modify the overall
behaviour of the present toolbox module.

.. autodata:: active_now

.. autodata:: active_insitu

.. autodata:: active_verbose

.. autodata:: active_promise

.. autodata:: active_clear

.. autodata:: active_metadatacheck

.. autodata:: active_incache


Resource Loading
----------------

.. autoclass:: VortexToolboxDescError
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autofunction:: rload

.. autofunction:: rh


Standard Get and Put
--------------------

.. autofunction:: rget

.. autofunction:: rput


Sections handling
-----------------

.. autofunction:: input

.. autofunction:: executable

.. autofunction:: inputs

.. autofunction:: algo

.. autofunction:: output

.. autofunction:: outputs

.. autofunction:: add_section

.. autofunction:: diff


Promises
--------

.. autofunction:: promise

.. autofunction:: clear_promises


Informations
------------

.. autofunction:: show_inputs

.. autofunction:: show_outputs

.. autofunction:: show_toolbox_settings

.. autofunction:: namespaces

.. autofunction:: print_namespaces

.. autofunction:: quickview


Misc
----

.. autofunction:: rescue

.. autofunction:: magic


Internal methods (more or less)
-------------------------------

.. autofunction:: nicedump
