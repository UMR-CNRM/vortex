:mod:`footprints` --- Footprints mechanisms
===========================================

.. automodule:: footprints
   :synopsis: Generic footprint implementation

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.8.1


Modules
-------

* :mod:`footprints.access`
* :mod:`footprints.collectors` 
* :mod:`footprints.config`
* :mod:`footprints.dump`
* :mod:`footprints.observers`
* :mod:`footprints.priorities`
* :mod:`footprints.proxies`
* :mod:`footprints.reporting`
* :mod:`footprints.stdtypes`
* :mod:`footprints.util`

Package
-------

.. autodata:: __all__

.. autodata:: proxy

.. autodata:: setup


Interface functions
-------------------

.. autofunction:: pickup

.. autofunction:: load

.. autofunction:: default

.. autofunction:: collected_classes

.. autofunction:: collected_priorities

.. autofunction:: reset_package_priority


Exceptions
----------

.. autoclass:: FootprintException
   :show-inheritance:

.. autoclass:: FootprintMaxIter
   :show-inheritance:

.. autoclass:: FootprintUnreachableAttr
   :show-inheritance:

.. autoclass:: FootprintFatalError
   :show-inheritance:

.. autoclass:: FootprintInvalidDefinition
   :show-inheritance:

Footprint mechanism
-------------------


.. autoclass:: Footprint
   :show-inheritance:
   :members:
   :member-order: alphabetical


.. autoclass:: FootprintBaseMeta
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: FootprintBase
   :show-inheritance:
   :members:
   :member-order: alphabetical

