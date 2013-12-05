:mod:`footprints` --- Footprints mechanisms
===========================================

.. automodule:: footprints
   :synopsis: Generic footprint implementation

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.8.1


Modules
-------

* :mod:`footprints.dump`
* :mod:`footprints.observers`
* :mod:`footprints.priorities`
* :mod:`footprints.reporting`
* :mod:`footprints.util`

Package
-------

.. autodata:: __all__

.. autodata:: setup

Interface functions
-------------------

.. autofunction:: collectorsmap

.. autofunction:: collector

.. autofunction:: collected_footprints

.. autofunction:: pickup

.. autofunction:: load

.. autofunction:: default

Exceptions
----------

.. autoclass:: FootprintMaxIter
   :show-inheritance:

.. autoclass:: FootprintUnreachableAttr
   :show-inheritance:

Footprint mechanism
-------------------

.. autoclass:: FootprintSetup
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: FootprintProxy
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Collector
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Footprint
   :show-inheritance:
   :members:
   :member-order: alphabetical


.. autoclass:: FootprintAttrAccess
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

