:mod:`vortex.data.stores` --- Resources data stores
===================================================

.. automodule:: vortex.data.stores
   :synopsis: Resources stores

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.1

Package
-------

.. autodata:: __all__

Interface
---------

As a :mod:`vortex.utilities.catalogs` based module,
:mod:`vortex.data.stores` automaticaly defined the following functions:

.. autofunction:: catalog

.. autofunction:: pickup

.. autofunction:: load


Classes
-------

.. autoclass:: StoresCatalog
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Store
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: MultiStore
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Finder
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: VortexArchiveStore
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: VortexCacheStore
   :show-inheritance:
   :members:
   :member-order: alphabetical
