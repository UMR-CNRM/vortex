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
   :member-order: bysource

.. autoclass:: Store
   :show-inheritance:
   :members:
   :member-order: bysource

.. autoclass:: MultiStore
   :show-inheritance:
   :members:
   :member-order: bysource

.. autoclass:: Finder
   :show-inheritance:
   :members:
   :member-order: bysource
